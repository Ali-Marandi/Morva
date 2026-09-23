from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.persistence.database import SessionLocal
from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize

router = APIRouter(
    prefix="/integration-execution",
    tags=["integration-readiness"],
)

CANONICAL_REPOSITORY = "Ali-Marandi/Morva"


class IntegrationExecutionReadinessVerificationResponse(BaseModel):
    assessment: dict[str, object]
    verification_fingerprint: str
    verified_at: datetime
    created_at: datetime


@router.get(
    "/readiness",
    response_model=IntegrationExecutionReadinessVerificationResponse,
)
def get_integration_execution_readiness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(default=None, pattern="^(staging|pilot)$"),
    principal: Principal = Depends(get_current_principal),
) -> IntegrationExecutionReadinessVerificationResponse:
    authorize(principal, "evidence.read", Scope.MINISTRY)
    if candidate_sha is not None:
        candidate_sha = candidate_sha.strip().lower()
        if len(candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in candidate_sha
        ):
            raise HTTPException(status_code=422, detail="candidate_sha must be a Git commit SHA-1")

    with SessionLocal() as session:
        repository = IntegrationExecutionReadinessVerificationRepository(session)
        try:
            record = repository.latest(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
            )
        except IntegrationExecutionReadinessPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="no persisted integration execution readiness verification found",
            )
        try:
            verification = record.to_verification()
        except IntegrationExecutionReadinessPersistenceError as exc:
            raise HTTPException(
                status_code=409,
                detail="persisted integration execution readiness verification is invalid",
            ) from exc

        assessment = verification.assessment.to_payload()
        return IntegrationExecutionReadinessVerificationResponse(
            assessment=assessment,
            verification_fingerprint=verification.fingerprint,
            verified_at=verification.verified_at,
            created_at=record.created_at,
        )


class IntegrationExecutionReadinessVerificationHistoryResponse(BaseModel):
    items: list[IntegrationExecutionReadinessVerificationResponse]
    has_more: bool
    next_before_verified_at: datetime | None = None
    next_before_id: UUID | None = None


def _normalize_candidate_sha_for_history(candidate_sha: str | None) -> str | None:
    if candidate_sha is None:
        return None
    normalized = candidate_sha.strip().lower()
    if len(normalized) != 40 or any(
        char not in "0123456789abcdef" for char in normalized
    ):
        raise HTTPException(
            status_code=422,
            detail="candidate_sha must be a Git commit SHA-1",
        )
    return normalized


def _normalize_history_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="verified_before must be timezone-aware",
        )
    return value.astimezone()


@router.get(
    "/readiness/history",
    response_model=IntegrationExecutionReadinessVerificationHistoryResponse,
)
def get_integration_execution_readiness_history(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    verified_before: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IntegrationExecutionReadinessVerificationHistoryResponse:
    authorize(principal, "evidence.read", Scope.MINISTRY)

    if (verified_before is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="verified_before and before_id must be supplied together",
        )

    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
    verified_before = _normalize_history_timestamp(verified_before)

    with SessionLocal() as session:
        repository = IntegrationExecutionReadinessVerificationRepository(session)
        try:
            records = repository.list_verified(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                verified_before=verified_before,
                before_id=before_id,
                limit=limit + 1,
            )
        except IntegrationExecutionReadinessPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        has_more = len(records) > limit
        page = records[:limit]
        items: list[IntegrationExecutionReadinessVerificationResponse] = []
        try:
            for record in page:
                verification = record.to_verification()
                items.append(
                    IntegrationExecutionReadinessVerificationResponse(
                        assessment=verification.assessment.to_payload(),
                        verification_fingerprint=verification.fingerprint,
                        verified_at=verification.verified_at,
                        created_at=record.created_at,
                    )
                )
        except IntegrationExecutionReadinessPersistenceError as exc:
            raise HTTPException(
                status_code=409,
                detail="persisted integration execution readiness verification is invalid",
            ) from exc

        next_verified_at = page[-1].verified_at if has_more and page else None
        next_id = page[-1].id if has_more and page else None
        return IntegrationExecutionReadinessVerificationHistoryResponse(
            items=items,
            has_more=has_more,
            next_before_verified_at=next_verified_at,
            next_before_id=next_id,
        )
