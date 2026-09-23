from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from morva.audit.persistence import append_audit_event

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
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.registry_bound_policy_readiness_freshness_records_m4_35 import (
    RegistryBoundPolicyReadinessFreshnessPersistenceError,
    RegistryBoundPolicyReadinessFreshnessRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotPersistenceError,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.persistence.historical_registry_bound_freshness_receipt_bindings_m4_37 import (
    HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError,
    HistoricalRegistryBoundFreshnessReceiptBindingRepository,
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
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshnessError,
    build_policy_bound_freshness,
)
from morva.runtime.registry_bound_policy_readiness_freshness_m4_34 import (
    RegistryBoundPolicyReadinessFreshnessError,
    build_registry_bound_policy_readiness_freshness,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicyError,
    build_freshness_policy,
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


class PolicyBoundReadinessFreshnessResponse(BaseModel):
    freshness: dict[str, object]


class FreshnessPolicyCreate(BaseModel):
    policy_id: str
    policy_version: int = 1
    max_age_seconds: int


class FreshnessPolicyResponse(BaseModel):
    policy: dict[str, object]


class FreshnessPolicyRegistryHistoryResponse(BaseModel):
    items: list[FreshnessPolicyResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class FreshnessPolicyRegistryIntegrityResponse(BaseModel):
    integrity_version: int
    policy_count: int
    fingerprint: str
    generated_at: datetime


class FreshnessPolicyRegistrySnapshotResponse(BaseModel):
    id: UUID
    snapshot: dict[str, object]
    captured_by: str
    created_at: datetime


class FreshnessPolicyRegistrySnapshotVerificationResponse(BaseModel):
    valid: bool
    snapshot: dict[str, object]


class HistoricalRegistryBoundFreshnessReceiptBindingCreate(BaseModel):
    receipt_id: UUID
    snapshot_id: UUID


class HistoricalRegistryBoundFreshnessReceiptBindingResponse(BaseModel):
    id: UUID
    binding: dict[str, object]
    bound_by: str
    created_at: datetime


class HistoricalRegistryBoundFreshnessReceiptBindingVerificationResponse(BaseModel):
    valid: bool
    binding: dict[str, object]


class RegistryBoundPolicyReadinessFreshnessResponse(BaseModel):
    freshness: dict[str, object]

class RegistryBoundPolicyReadinessFreshnessReceiptResponse(BaseModel):
    id: UUID
    freshness: dict[str, object]
    repository: str
    candidate_sha: str
    target_environment: str
    organization_scope: str
    organization_scope_id: str
    recorded_by: str
    created_at: datetime


class RegistryBoundPolicyReadinessFreshnessReceiptHistoryResponse(BaseModel):
    items: list[RegistryBoundPolicyReadinessFreshnessReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


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
    "/readiness/convergence/freshness/policies",
    response_model=FreshnessPolicyResponse,
)
def create_readiness_freshness_policy(
    payload: FreshnessPolicyCreate,
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="freshness policy registry is ministry-managed",
        )
    try:
        policy = build_freshness_policy(
            policy_id=payload.policy_id,
            max_age_seconds=payload.max_age_seconds,
            policy_version=payload.policy_version,
        )
    except ReadinessConvergenceFreshnessPolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    with SessionLocal() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            record = repository.record(
                policy,
                recorded_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.freshness_policy.recorded",
                entity_type="readiness_convergence_freshness_policy",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "policy_id": record.policy_id,
                    "policy_version": record.policy_version,
                    "fingerprint": record.fingerprint,
                    "max_age_seconds": record.max_age_seconds,
                },
                reason="versioned readiness freshness policy persisted",
                session=session,
            )
            session.commit()
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreshnessPolicyResponse(policy=record.to_policy().to_payload())




@router.get(
    "/readiness/convergence/freshness/policies",
    response_model=FreshnessPolicyRegistryHistoryResponse,
)
def list_readiness_freshness_policies(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyRegistryHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if before_created_at is not None and before_created_at.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="before_created_at must be timezone-aware",
        )
    if (
        principal.scope is not Scope.MINISTRY
        and before_id is not None
    ):
        # Cursor values are opaque; non-ministry callers must still be scoped
        # by their own authority, while the policy registry itself is ministry-managed.
        raise HTTPException(status_code=403, detail="freshness policy registry is ministry-managed")
    with SessionLocal() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        FreshnessPolicyResponse(policy=record.to_policy().to_payload())
        for record in records
    ]
    next_created_at = records[-1].created_at if has_more else None
    next_id = records[-1].id if has_more else None
    return FreshnessPolicyRegistryHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=next_created_at,
        next_before_id=next_id,
    )




@router.get(
    "/readiness/convergence/freshness/policies/integrity",
    response_model=FreshnessPolicyRegistryIntegrityResponse,
)
def get_readiness_freshness_policy_registry_integrity(
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyRegistryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            policy_count, fingerprint = repository.integrity_snapshot()
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreshnessPolicyRegistryIntegrityResponse(
        integrity_version=1,
        policy_count=policy_count,
        fingerprint=fingerprint,
        generated_at=datetime.now(timezone.utc),
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-bound",
    response_model=PolicyBoundReadinessFreshnessResponse,
)
def get_policy_registry_bound_readiness_convergence_freshness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    policy_id: str = Query(..., min_length=1, max_length=100),
    policy_version: int = Query(default=1, ge=1),
    principal: Principal = Depends(get_current_principal),
) -> PolicyBoundReadinessFreshnessResponse:
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
        convergence_repository = ScopeBoundReadinessConvergenceRepository(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            records = convergence_repository.list_verified(
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
            policy_record = policy_repository.get(
                policy_id=policy_id,
                policy_version=policy_version,
            )
            if policy_record is None:
                raise HTTPException(
                    status_code=404,
                    detail="freshness policy not found",
                )
            freshness = build_policy_bound_freshness(
                policy_record.to_policy(),
                records[0].to_convergence(),
                observed_at=observed_at,
            )
        except HTTPException:
            raise
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            PolicyBoundReadinessFreshnessError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PolicyBoundReadinessFreshnessResponse(
        freshness=freshness.to_payload(),
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-bound-integrity",
    response_model=RegistryBoundPolicyReadinessFreshnessResponse,
)
def get_registry_integrity_bound_readiness_convergence_freshness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    policy_id: str = Query(..., min_length=1, max_length=100),
    policy_version: int = Query(default=1, ge=1),
    principal: Principal = Depends(get_current_principal),
) -> RegistryBoundPolicyReadinessFreshnessResponse:
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
    with SessionLocal() as session:
        try:
            freshness, _ = _build_registry_integrity_bound_freshness(
                session,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                policy_id=policy_id,
                policy_version=policy_version,
                observed_at=datetime.now(timezone.utc),
            )
        except HTTPException:
            raise
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            PolicyBoundReadinessFreshnessError,
            RegistryBoundPolicyReadinessFreshnessError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RegistryBoundPolicyReadinessFreshnessResponse(
        freshness=freshness.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-bound-integrity/receipts",
    response_model=RegistryBoundPolicyReadinessFreshnessReceiptResponse,
)
def persist_registry_integrity_bound_readiness_convergence_freshness_receipt(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    policy_id: str = Query(..., min_length=1, max_length=100),
    policy_version: int = Query(default=1, ge=1),
    principal: Principal = Depends(get_current_principal),
) -> RegistryBoundPolicyReadinessFreshnessReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="registry-bound freshness receipts are ministry-managed",
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
    with SessionLocal() as session:
        try:
            freshness, convergence = _build_registry_integrity_bound_freshness(
                session,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                policy_id=policy_id,
                policy_version=policy_version,
                observed_at=datetime.now(timezone.utc),
            )
            repository = RegistryBoundPolicyReadinessFreshnessRepository(session)
            record = repository.record(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=convergence.candidate_sha,
                target_environment=convergence.target_environment,
                organization_scope=convergence.organization_scope,
                organization_scope_id=convergence.organization_scope_id,
                freshness=freshness,
                recorded_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.registry_bound_freshness_receipt.recorded",
                entity_type="registry_bound_policy_readiness_freshness_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "binding_fingerprint": record.binding_fingerprint,
                    "registry_fingerprint": record.registry_fingerprint,
                    "policy_id": record.policy_id,
                    "policy_version": record.policy_version,
                    "candidate_sha": record.candidate_sha,
                },
                reason="registry-bound freshness evaluation receipt persisted",
                session=session,
            )
            session.commit()
        except HTTPException:
            raise
        except RegistryBoundPolicyReadinessFreshnessPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            PolicyBoundReadinessFreshnessError,
            RegistryBoundPolicyReadinessFreshnessError,
        ) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RegistryBoundPolicyReadinessFreshnessReceiptResponse(
        id=record.id,
        freshness=record.to_freshness().to_payload(),
        repository=record.repository,
        candidate_sha=record.candidate_sha,
        target_environment=record.target_environment,
        organization_scope=record.organization_scope,
        organization_scope_id=record.organization_scope_id,
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-bound-integrity/receipts",
    response_model=RegistryBoundPolicyReadinessFreshnessReceiptHistoryResponse,
)
def list_registry_integrity_bound_readiness_convergence_freshness_receipts(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> RegistryBoundPolicyReadinessFreshnessReceiptHistoryResponse:
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
    if before_created_at is not None and before_created_at.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="before_created_at must be timezone-aware",
        )
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
    with SessionLocal() as session:
        repository = RegistryBoundPolicyReadinessFreshnessRepository(session)
        try:
            records, has_more = repository.list(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except RegistryBoundPolicyReadinessFreshnessPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        RegistryBoundPolicyReadinessFreshnessReceiptResponse(
            id=record.id,
            freshness=record.to_freshness().to_payload(),
            repository=record.repository,
            candidate_sha=record.candidate_sha,
            target_environment=record.target_environment,
            organization_scope=record.organization_scope,
            organization_scope_id=record.organization_scope_id,
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    next_created_at = records[-1].created_at if has_more else None
    next_id = records[-1].id if has_more else None
    return RegistryBoundPolicyReadinessFreshnessReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=next_created_at,
        next_before_id=next_id,
    )


def _build_registry_integrity_bound_freshness(
    session,
    *,
    candidate_sha: str | None,
    target_environment: str | None,
    organization_scope: str,
    organization_scope_id: str,
    policy_id: str,
    policy_version: int,
    observed_at: datetime,
):
    convergence_repository = ScopeBoundReadinessConvergenceRepository(session)
    policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    records = convergence_repository.list_verified(
        repository=CANONICAL_REPOSITORY,
        candidate_sha=candidate_sha,
        target_environment=target_environment,
        organization_scope=organization_scope,
        organization_scope_id=organization_scope_id,
        limit=1,
    )
    if not records:
        raise HTTPException(
            status_code=404,
            detail="no persisted scope-bound readiness convergence found",
        )
    convergence = records[0].to_convergence()
    policy_record = policy_repository.get(
        policy_id=policy_id,
        policy_version=policy_version,
    )
    if policy_record is None:
        raise HTTPException(status_code=404, detail="freshness policy not found")
    policy_bound = build_policy_bound_freshness(
        policy_record.to_policy(),
        convergence,
        observed_at=observed_at,
    )
    policy_count, registry_fingerprint = policy_repository.integrity_snapshot()
    freshness = build_registry_bound_policy_readiness_freshness(
        policy_bound,
        registry_integrity_version=1,
        registry_policy_count=policy_count,
        registry_fingerprint=registry_fingerprint,
    )
    return freshness, convergence


@router.post(
    "/readiness/convergence/freshness/policies/snapshots",
    response_model=FreshnessPolicyRegistrySnapshotResponse,
)
def capture_readiness_freshness_policy_registry_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyRegistrySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="freshness registry snapshots are ministry-managed",
        )
    with SessionLocal() as session:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        try:
            record = snapshot_repository.capture(
                policy_repository,
                captured_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.freshness_policy_registry_snapshot.captured",
                entity_type="readiness_freshness_policy_registry_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_fingerprint": record.fingerprint,
                    "registry_fingerprint": record.registry_fingerprint,
                    "policy_count": record.policy_count,
                },
                reason="historical freshness policy registry snapshot captured",
                session=session,
            )
            session.commit()
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreshnessPolicyRegistrySnapshotResponse(
        id=record.id,
        snapshot=record.to_snapshot().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policies/snapshots/{snapshot_id}/verify",
    response_model=FreshnessPolicyRegistrySnapshotVerificationResponse,
)
def verify_readiness_freshness_policy_registry_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyRegistrySnapshotVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        try:
            record = snapshot_repository.reconstruct(
                snapshot_id,
                policy_repository,
            )
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            if "not found" in str(exc):
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreshnessPolicyRegistrySnapshotVerificationResponse(
        valid=True,
        snapshot=record.to_snapshot().to_payload(),
    )



@router.post(
    "/readiness/convergence/freshness/policy-registry-bound-integrity/receipt-snapshot-bindings",
    response_model=HistoricalRegistryBoundFreshnessReceiptBindingResponse,
)
def bind_registry_integrity_receipt_to_historical_snapshot(
    payload: HistoricalRegistryBoundFreshnessReceiptBindingCreate,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalRegistryBoundFreshnessReceiptBindingResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical receipt bindings are ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        try:
            record = repository.bind(
                receipt_id=payload.receipt_id,
                snapshot_id=payload.snapshot_id,
                bound_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.historical_receipt_snapshot_binding.recorded",
                entity_type="historical_registry_bound_freshness_receipt_binding",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "receipt_id": str(record.receipt_id),
                    "snapshot_id": str(record.snapshot_id),
                    "fingerprint": record.fingerprint,
                    "registry_fingerprint": record.registry_fingerprint,
                },
                reason="registry-bound freshness receipt anchored to historical registry snapshot",
                session=session,
            )
            session.commit()
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalRegistryBoundFreshnessReceiptBindingResponse(
        id=record.id,
        binding=record.to_binding().to_payload(),
        bound_by=record.bound_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-bound-integrity/"
    "receipt-snapshot-bindings/{binding_id}/verify",
    response_model=HistoricalRegistryBoundFreshnessReceiptBindingVerificationResponse,
)
def verify_registry_integrity_receipt_historical_snapshot_binding(
    binding_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalRegistryBoundFreshnessReceiptBindingVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        try:
            record = repository.verify(binding_id)
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalRegistryBoundFreshnessReceiptBindingVerificationResponse(
        valid=True,
        binding=record.to_binding().to_payload(),
    )


@router.get(
    "/readiness/convergence/freshness/policies/snapshots/{snapshot_id}/policies/{policy_id}",
    response_model=FreshnessPolicyResponse,
)
def get_historical_snapshot_freshness_policy(
    snapshot_id: UUID,
    policy_id: str,
    policy_version: int = Query(default=1, ge=1),
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            record = snapshot_repository.resolve_policy(
                snapshot_id,
                policy_repository,
                policy_id=policy_id,
                policy_version=policy_version,
            )
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return FreshnessPolicyResponse(policy=record.to_policy().to_payload())


@router.get(
    "/readiness/convergence/freshness/policies/{policy_id}",
    response_model=FreshnessPolicyResponse,
)
def get_readiness_freshness_policy(
    policy_id: str,
    policy_version: int = Query(default=1, ge=1),
    principal: Principal = Depends(get_current_principal),
) -> FreshnessPolicyResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            record = repository.get(
                policy_id=policy_id,
                policy_version=policy_version,
            )
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if record is None:
            raise HTTPException(status_code=404, detail="freshness policy not found")
        return FreshnessPolicyResponse(policy=record.to_policy().to_payload())


@router.get(
    "/readiness/convergence/freshness/policy-bound",
    response_model=PolicyBoundReadinessFreshnessResponse,
)
def get_policy_bound_readiness_convergence_freshness(
    candidate_sha: str | None = Query(default=None, min_length=40, max_length=40),
    target_environment: str | None = Query(
        default=None,
        pattern="^(staging|pilot)$",
    ),
    organization_scope: str | None = Query(default=None),
    organization_scope_id: str | None = Query(default=None),
    policy_id: str = Query(..., min_length=1, max_length=100),
    policy_version: int = Query(default=1, ge=1),
    max_age_seconds: int = Query(..., ge=1),
    principal: Principal = Depends(get_current_principal),
) -> PolicyBoundReadinessFreshnessResponse:
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
            policy = build_freshness_policy(
                policy_id=policy_id,
                max_age_seconds=max_age_seconds,
                policy_version=policy_version,
            )
            freshness = build_policy_bound_freshness(
                policy,
                records[0].to_convergence(),
                observed_at=observed_at,
            )
        except HTTPException:
            raise
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyError,
            PolicyBoundReadinessFreshnessError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PolicyBoundReadinessFreshnessResponse(
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
