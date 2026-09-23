from __future__ import annotations

from datetime import datetime, timezone

from morva.audit.persistence import append_audit_event
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.persistence.database import SessionLocal
from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.persistence.scope_bound_readiness_convergence_records_m4_27 import (
    ScopeBoundReadinessConvergencePersistenceError,
    ScopeBoundReadinessConvergenceRepository,
)
from morva.persistence.scoped_evidence_readiness_m4_26 import (
    ScopedEvidenceReadinessPersistenceError,
    build_current_scoped_evidence_readiness,
)
from morva.runtime.persist_scope_bound_readiness_convergence_m4_27 import (
    PersistScopeBoundReadinessConvergenceError,
    persist_latest_scope_bound_readiness_convergence,
)
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize
from morva.runtime.readiness_scope_binding_m4_25 import (
    ReadinessScopeBindingError,
    normalize_readiness_scope,
)
from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergenceError,
    build_scope_bound_readiness_convergence,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessError,
    assess_readiness_convergence_freshness,
)
from morva.persistence.scope_bound_readiness_convergence_records_m4_27 import (
    ScopeBoundReadinessConvergencePersistenceError,
    ScopeBoundReadinessConvergenceRepository,
)

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
    organization_scope: str
    organization_scope_id: str
    scope_binding_fingerprint: str


@router.get(
    "/readiness",
    response_model=IntegrationExecutionReadinessVerificationResponse,
)
def get_integration_execution_readiness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(default=None, pattern="^(staging|pilot)$"),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> IntegrationExecutionReadinessVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    if candidate_sha is not None:
        candidate_sha = candidate_sha.strip().lower()
        if len(candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in candidate_sha
        ):
            raise HTTPException(status_code=422, detail="candidate_sha must be a Git commit SHA-1")

    with SessionLocal() as session:
        repository = IntegrationExecutionReadinessVerificationRepository(session)
        try:
            scope_filter, scope_id_filter = _resolve_scope_filter(
                principal,
                organization_scope,
                organization_scope_id,
            )
            record = repository.latest(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
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
            organization_scope=record.organization_scope,
            organization_scope_id=record.organization_scope_id,
            scope_binding_fingerprint=record.scope_binding_fingerprint,
        )




def _resolve_scope_filter(
    principal: Principal,
    organization_scope: str | None,
    organization_scope_id: str | None,
) -> tuple[str | None, str | None]:
    if principal.scope is not Scope.MINISTRY:
        if organization_scope is not None and organization_scope != principal.scope.value:
            raise HTTPException(status_code=403, detail="organization scope violation")
        if organization_scope_id is not None and organization_scope_id != principal.scope_id:
            raise HTTPException(status_code=403, detail="organization scope violation")
        return principal.scope.value, principal.scope_id

    if (organization_scope is None) != (organization_scope_id is None):
        raise HTTPException(
            status_code=422,
            detail="organization_scope and organization_scope_id must be supplied together",
        )
    if organization_scope is None:
        return None, None
    try:
        return normalize_readiness_scope(organization_scope, organization_scope_id or "")
    except ReadinessScopeBindingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc





class ScopeBoundReadinessConvergenceResponse(BaseModel):
    convergence: dict[str, object]


class ReadinessConvergenceFreshnessResponse(BaseModel):
    freshness: dict[str, object]


class ScopeBoundReadinessConvergenceReceiptResponse(BaseModel):
    id: UUID
    convergence: dict[str, object]
    recorded_by: str
    created_at: datetime


class ScopeBoundReadinessConvergenceReceiptHistoryResponse(BaseModel):
    items: list[ScopeBoundReadinessConvergenceReceiptResponse]
    has_more: bool
    next_before_checked_at: datetime | None = None
    next_before_id: UUID | None = None


@router.get(
    "/readiness/convergence/freshness",
    response_model=ReadinessConvergenceFreshnessResponse,
)
def get_readiness_convergence_freshness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    max_age_seconds: int = Query(..., ge=1),
    principal: Principal = Depends(get_current_principal),
) -> ReadinessConvergenceFreshnessResponse:
    authorize(principal, "evidence.read", principal.scope)
    scope_filter, scope_id_filter = _resolve_scope_filter(
        principal,
        organization_scope,
        organization_scope_id,
    )
    if scope_filter is None or scope_id_filter is None:
        raise HTTPException(
            status_code=422,
            detail="organization_scope and organization_scope_id are required",
        )
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
    observed_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        repository = ScopeBoundReadinessConvergenceRepository(session)
        try:
            records = repository.list_verified(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                limit=1,
            )
            if not records:
                raise HTTPException(
                    status_code=404,
                    detail="no persisted scope-bound readiness convergence found",
                )
            freshness = assess_readiness_convergence_freshness(
                records[0].to_convergence(),
                observed_at=observed_at,
                max_age_seconds=max_age_seconds,
            )
        except HTTPException:
            raise
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ReadinessConvergenceFreshnessResponse(
        freshness=freshness.to_payload(),
    )


@router.post(
    "/readiness/convergence/receipts",
    response_model=ScopeBoundReadinessConvergenceReceiptResponse,
)
def persist_scope_bound_readiness_convergence_receipt(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> ScopeBoundReadinessConvergenceReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    scope_filter, scope_id_filter = _resolve_scope_filter(
        principal,
        organization_scope,
        organization_scope_id,
    )
    if scope_filter is None or scope_id_filter is None:
        raise HTTPException(
            status_code=422,
            detail="organization_scope and organization_scope_id are required",
        )
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
    checked_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        try:
            record = persist_latest_scope_bound_readiness_convergence(
                session,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                checked_at=checked_at,
                recorded_by=principal.user_id,
            )
            session.commit()
        except HTTPException:
            raise
        except (
            PersistScopeBoundReadinessConvergenceError,
            IntegrationExecutionReadinessPersistenceError,
            ScopedEvidenceReadinessPersistenceError,
            ScopeBoundReadinessConvergencePersistenceError,
        ) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type="integration.readiness.convergence.recorded",
            entity_type="scope_bound_readiness_convergence",
            entity_id=str(record.id),
            actor_id=principal.user_id,
            payload={
                "convergence_fingerprint": record.convergence_fingerprint,
                "state": record.state,
                "organization_scope": record.organization_scope,
                "organization_scope_id": record.organization_scope_id,
            },
            reason="scope-bound readiness convergence observation persisted",
            session=session,
        )
        session.commit()
        return ScopeBoundReadinessConvergenceReceiptResponse(
            id=record.id,
            convergence=record.to_convergence().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )


@router.get(
    "/readiness/convergence",
    response_model=ScopeBoundReadinessConvergenceResponse,
)
def get_scope_bound_readiness_convergence(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> ScopeBoundReadinessConvergenceResponse:
    authorize(principal, "evidence.read", principal.scope)

    if (
        principal.scope is not Scope.MINISTRY
        and organization_scope is None
        and organization_scope_id is None
    ):
        organization_scope = principal.scope.value
        organization_scope_id = principal.scope_id

    scope_filter, scope_id_filter = _resolve_scope_filter(
        principal,
        organization_scope,
        organization_scope_id,
    )
    if scope_filter is None or scope_id_filter is None:
        raise HTTPException(
            status_code=422,
            detail="organization_scope and organization_scope_id are required",
        )

    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)

    checked_at = datetime.now(timezone.utc)
    with SessionLocal() as session:
        repository = IntegrationExecutionReadinessVerificationRepository(session)
        try:
            record = repository.latest(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
            )
            if record is None:
                raise HTTPException(
                    status_code=404,
                    detail="no persisted integration execution readiness verification found",
                )
            verification = record.to_verification()
            current_evidence_readiness = build_current_scoped_evidence_readiness(
                session,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                checked_at=checked_at,
            )
            convergence = build_scope_bound_readiness_convergence(
                verification,
                current_evidence_readiness,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                checked_at=checked_at,
            )
        except HTTPException:
            raise
        except (
            IntegrationExecutionReadinessPersistenceError,
            ScopedEvidenceReadinessPersistenceError,
            ScopeBoundReadinessConvergenceError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ScopeBoundReadinessConvergenceResponse(
        convergence=convergence.to_payload()
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


def _normalize_history_timestamp(
    value: datetime | None,
    *,
    name: str = "verified_before",
) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must be timezone-aware",
        )
    return value.astimezone(timezone.utc)


@router.get(
    "/readiness/convergence/history",
    response_model=ScopeBoundReadinessConvergenceReceiptHistoryResponse,
)
def get_scope_bound_readiness_convergence_history(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    checked_before: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> ScopeBoundReadinessConvergenceReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    scope_filter, scope_id_filter = _resolve_scope_filter(
        principal,
        organization_scope,
        organization_scope_id,
    )
    if (checked_before is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="checked_before and before_id must be supplied together",
        )
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
    checked_before = _normalize_history_timestamp(
        checked_before,
        name="checked_before",
    )
    with SessionLocal() as session:
        repository = ScopeBoundReadinessConvergenceRepository(session)
        try:
            records = repository.list_verified(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                checked_before=checked_before,
                before_id=before_id,
                limit=limit + 1,
            )
        except ScopeBoundReadinessConvergencePersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        has_more = len(records) > limit
        page = records[:limit]
        items = [
            ScopeBoundReadinessConvergenceReceiptResponse(
                id=record.id,
                convergence=record.to_convergence().to_payload(),
                recorded_by=record.recorded_by,
                created_at=record.created_at,
            )
            for record in page
        ]
        return ScopeBoundReadinessConvergenceReceiptHistoryResponse(
            items=items,
            has_more=has_more,
            next_before_checked_at=(
                page[-1].checked_at if has_more and page else None
            ),
            next_before_id=page[-1].id if has_more and page else None,
        )


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
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    verified_before: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IntegrationExecutionReadinessVerificationHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)

    scope_filter, scope_id_filter = _resolve_scope_filter(
        principal,
        organization_scope,
        organization_scope_id,
    )

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
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
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
                        organization_scope=record.organization_scope,
                        organization_scope_id=record.organization_scope_id,
                        scope_binding_fingerprint=record.scope_binding_fingerprint,
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
