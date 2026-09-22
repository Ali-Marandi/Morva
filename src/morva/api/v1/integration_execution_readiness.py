from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.persistence.database import SessionLocal
from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.runtime.independent_persisted_integration_readiness_verifier_m4_23 import (
    IndependentPersistedIntegrationReadinessVerificationError,
    verify_persisted_integration_execution_readiness,
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


class IndependentIntegrationExecutionReadinessVerificationResponse(BaseModel):
    verification: dict[str, object]


def _normalize_candidate_sha(candidate_sha: str | None) -> str | None:
    if candidate_sha is None:
        return None
    candidate_sha = candidate_sha.strip().lower()
    if len(candidate_sha) != 40 or any(
        char not in "0123456789abcdef" for char in candidate_sha
    ):
        raise HTTPException(
            status_code=422,
            detail="candidate_sha must be a Git commit SHA-1",
        )
    return candidate_sha


@router.get(
    "/readiness",
    response_model=IntegrationExecutionReadinessVerificationResponse,
)
def get_integration_execution_readiness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None, pattern="^(staging|pilot)$"
    ),
    principal: Principal = Depends(get_current_principal),
) -> IntegrationExecutionReadinessVerificationResponse:
    authorize(principal, "evidence.read", Scope.MINISTRY)
    candidate_sha = _normalize_candidate_sha(candidate_sha)

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


@router.get(
    "/readiness/verify",
    response_model=IndependentIntegrationExecutionReadinessVerificationResponse,
)
def verify_persisted_integration_execution_readiness_api(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None, pattern="^(staging|pilot)$"
    ),
    principal: Principal = Depends(get_current_principal),
) -> IndependentIntegrationExecutionReadinessVerificationResponse:
    authorize(principal, "evidence.read", Scope.MINISTRY)
    candidate_sha = _normalize_candidate_sha(candidate_sha)

    with SessionLocal() as session:
        repository = IntegrationExecutionReadinessVerificationRepository(session)
        try:
            record = repository.latest_raw(
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
            raw_blockers = record.blockers
            if not isinstance(raw_blockers, list):
                raise IndependentPersistedIntegrationReadinessVerificationError(
                    "persisted blockers must be a JSON list"
                )
            verification = verify_persisted_integration_execution_readiness(
                repository=record.repository,
                candidate_sha=record.candidate_sha,
                target_environment=record.target_environment,
                assessment_version=record.assessment_version,
                assessment_checked_at=record.assessment_checked_at,
                verified_at=record.verified_at,
                created_at=record.created_at,
                evidence_readiness_fingerprint=record.evidence_readiness_fingerprint,
                binding_fingerprint=record.binding_fingerprint,
                binding_verification_fingerprint=record.binding_verification_fingerprint,
                state=record.state,
                blockers=tuple(raw_blockers),
                assessment_fingerprint=record.assessment_fingerprint,
                verification_fingerprint=record.verification_fingerprint,
            )
        except (
            AttributeError,
            TypeError,
            ValueError,
            IndependentPersistedIntegrationReadinessVerificationError,
        ) as exc:
            raise HTTPException(
                status_code=409,
                detail="persisted integration execution readiness failed independent verification",
            ) from exc

        return IndependentIntegrationExecutionReadinessVerificationResponse(
            verification=verification.to_payload()
        )
