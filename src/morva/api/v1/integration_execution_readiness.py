from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.persistence.database import SessionLocal
from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.runtime.independent_persisted_integration_execution_readiness_verifier_m4_23 import (
    PersistedIntegrationExecutionReadinessVerificationError,
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


class IndependentPersistedIntegrationExecutionReadinessResponse(BaseModel):
    assessment: dict[str, object]
    verification: dict[str, object]


def _validate_candidate_sha(candidate_sha: str | None) -> str | None:
    if candidate_sha is None:
        return None
    value = candidate_sha.strip().lower()
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value):
        raise HTTPException(
            status_code=422,
            detail="candidate_sha must be a Git commit SHA-1",
        )
    return value


def _load_latest_record(
    *,
    candidate_sha: str | None,
    target_environment: str | None,
):
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
        return record


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
    candidate_sha = _validate_candidate_sha(candidate_sha)

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

        return IntegrationExecutionReadinessVerificationResponse(
            assessment=verification.assessment.to_payload(),
            verification_fingerprint=verification.fingerprint,
            verified_at=verification.verified_at,
            created_at=record.created_at,
        )


@router.get(
    "/readiness/verify",
    response_model=IndependentPersistedIntegrationExecutionReadinessResponse,
    responses={
        404: {"description": "No persisted readiness verification found"},
        409: {"description": "Persisted readiness failed independent verification"},
    },
)
def verify_persisted_readiness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(default=None, pattern="^(staging|pilot)$"),
    principal: Principal = Depends(get_current_principal),
) -> IndependentPersistedIntegrationExecutionReadinessResponse:
    authorize(principal, "evidence.read", Scope.MINISTRY)
    candidate_sha = _validate_candidate_sha(candidate_sha)
    record = _load_latest_record(
        candidate_sha=candidate_sha,
        target_environment=target_environment,
    )

    try:
        verification = verify_persisted_integration_execution_readiness(
            record,
            repository=CANONICAL_REPOSITORY,
            candidate_sha=candidate_sha,
            target_environment=target_environment,
        )
    except PersistedIntegrationExecutionReadinessVerificationError as exc:
        raise HTTPException(
            status_code=409,
            detail="persisted integration execution readiness failed independent verification",
        ) from exc

    assessment = {
        "assessment_version": 1,
        "repository": verification.repository,
        "candidate_sha": verification.candidate_sha,
        "target_environment": verification.target_environment,
        "checked_at": verification.assessment_checked_at.isoformat(),
        "evidence_readiness_fingerprint": record.evidence_readiness_fingerprint,
        "binding_fingerprint": record.binding_fingerprint,
        "binding_verification_fingerprint": record.binding_verification_fingerprint,
        "state": verification.state,
        "blockers": list(verification.blockers),
        "ready": verification.state == "ready",
        "fingerprint": verification.assessment_fingerprint,
    }
    return IndependentPersistedIntegrationExecutionReadinessResponse(
        assessment=assessment,
        verification=verification.to_payload(),
    )
