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
from morva.persistence.historical_snapshot_bound_freshness_receipts_m4_40 import (
    HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
    HistoricalSnapshotBoundFreshnessReceiptRepository,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
    HistoricalSnapshotFreshnessReceiptLineageRepository,
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
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    HistoricalSnapshotBoundPolicyReadinessFreshnessError,
    build_historical_snapshot_bound_policy_readiness_freshness,
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


class HistoricalSnapshotBoundPolicyReadinessFreshnessResponse(BaseModel):
    freshness: dict[str, object]



class HistoricalSnapshotBoundFreshnessReceiptResponse(BaseModel):
    id: UUID
    freshness: dict[str, object]
    repository: str
    candidate_sha: str
    target_environment: str
    organization_scope: str
    organization_scope_id: str
    recorded_by: str
    created_at: datetime


class HistoricalSnapshotBoundFreshnessReceiptHistoryResponse(BaseModel):
    items: list[HistoricalSnapshotBoundFreshnessReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalSnapshotBoundFreshnessReceiptVerificationResponse(BaseModel):
    valid: bool
    freshness: dict[str, object]

class HistoricalSnapshotFreshnessReceiptLineageCreate(BaseModel):
    freshness_receipt_id: UUID
    historical_binding_id: UUID


class HistoricalSnapshotFreshnessReceiptLineageResponse(BaseModel):
    id: UUID
    lineage: dict[str, object]
    bound_by: str
    created_at: datetime


class HistoricalSnapshotFreshnessReceiptLineageVerificationResponse(BaseModel):
    valid: bool
    lineage: dict[str, object]


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


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts",
    response_model=HistoricalSnapshotBoundFreshnessReceiptResponse,
)
def persist_historical_snapshot_bound_freshness_receipt(
    snapshot_id: UUID,
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
) -> HistoricalSnapshotBoundFreshnessReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical snapshot-bound freshness receipts are ministry-managed",
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
            convergence_repository = ScopeBoundReadinessConvergenceRepository(session)
            policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
            snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
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
            snapshot_record = snapshot_repository.reconstruct(
                snapshot_id,
                policy_repository,
            )
            policy_record = snapshot_repository.resolve_policy(
                snapshot_id,
                policy_repository,
                policy_id=policy_id,
                policy_version=policy_version,
            )
            snapshot = snapshot_record.to_snapshot()
            policy_bound = build_policy_bound_freshness(
                policy_record.to_policy(),
                records[0].to_convergence(),
                observed_at=datetime.now(timezone.utc),
            )
            freshness = build_historical_snapshot_bound_policy_readiness_freshness(
                policy_bound,
                snapshot_id=snapshot_record.id,
                snapshot_fingerprint=snapshot.fingerprint,
                registry_integrity_version=snapshot.integrity_version,
                registry_policy_count=snapshot.policy_count,
                registry_fingerprint=snapshot.registry_fingerprint,
            )
            repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
            record = repository.record(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=records[0].candidate_sha,
                target_environment=records[0].target_environment,
                organization_scope=records[0].organization_scope,
                organization_scope_id=records[0].organization_scope_id,
                freshness=freshness,
                recorded_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.historical_snapshot_bound_freshness_receipt.recorded",
                entity_type="historical_snapshot_bound_policy_readiness_freshness_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "binding_fingerprint": record.binding_fingerprint,
                    "snapshot_id": str(record.snapshot_id),
                    "snapshot_fingerprint": record.snapshot_fingerprint,
                    "policy_id": record.policy_id,
                    "policy_version": record.policy_version,
                    "candidate_sha": record.candidate_sha,
                },
                reason="historical snapshot-bound freshness evaluation receipt persisted",
                session=session,
            )
            session.commit()
        except HTTPException:
            raise
        except HistoricalSnapshotBoundFreshnessReceiptPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            FreshnessPolicyRegistrySnapshotPersistenceError,
            PolicyBoundReadinessFreshnessError,
            HistoricalSnapshotBoundPolicyReadinessFreshnessError,
        ) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalSnapshotBoundFreshnessReceiptResponse(
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
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts",
    response_model=HistoricalSnapshotBoundFreshnessReceiptHistoryResponse,
)
def list_historical_snapshot_bound_freshness_receipts(
    snapshot_id: UUID | None = Query(default=None),
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
) -> HistoricalSnapshotBoundFreshnessReceiptHistoryResponse:
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
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        try:
            records, has_more = repository.list(
                repository=CANONICAL_REPOSITORY,
                candidate_sha=candidate_sha,
                target_environment=target_environment,
                organization_scope=scope_filter,
                organization_scope_id=scope_id_filter,
                snapshot_id=snapshot_id,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalSnapshotBoundFreshnessReceiptPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalSnapshotBoundFreshnessReceiptResponse(
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
    return HistoricalSnapshotBoundFreshnessReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more else None,
        next_before_id=records[-1].id if has_more else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipts/{receipt_id}/verify",
    response_model=HistoricalSnapshotBoundFreshnessReceiptVerificationResponse,
)
def verify_historical_snapshot_bound_freshness_receipt(
    receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalSnapshotBoundFreshnessReceiptVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        try:
            record = repository.verify(receipt_id)
        except HistoricalSnapshotBoundFreshnessReceiptPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalSnapshotBoundFreshnessReceiptVerificationResponse(
        valid=True,
        freshness=record.to_freshness().to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage",
    response_model=HistoricalSnapshotFreshnessReceiptLineageResponse,
)
def bind_historical_snapshot_freshness_receipt_lineage(
    payload: HistoricalSnapshotFreshnessReceiptLineageCreate,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalSnapshotFreshnessReceiptLineageResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness receipt lineage is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        try:
            record = repository.bind(
                freshness_receipt_id=payload.freshness_receipt_id,
                historical_binding_id=payload.historical_binding_id,
                bound_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.historical_snapshot_freshness_receipt_lineage.recorded",
                entity_type="historical_snapshot_freshness_receipt_lineage",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "freshness_receipt_id": str(record.freshness_receipt_id),
                    "historical_binding_id": str(record.historical_binding_id),
                    "snapshot_id": str(record.snapshot_id),
                    "fingerprint": record.fingerprint,
                },
                reason="historical freshness receipt lineage anchored to M4.37 snapshot binding",
                session=session,
            )
            session.commit()
        except HistoricalSnapshotFreshnessReceiptLineagePersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalSnapshotFreshnessReceiptLineageResponse(
        id=record.id,
        lineage=record.to_lineage().to_payload(),
        bound_by=record.bound_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/{lineage_id}/verify",
    response_model=HistoricalSnapshotFreshnessReceiptLineageVerificationResponse,
)
def verify_historical_snapshot_freshness_receipt_lineage(
    lineage_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalSnapshotFreshnessReceiptLineageVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        try:
            record = repository.verify(lineage_id)
        except HistoricalSnapshotFreshnessReceiptLineagePersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalSnapshotFreshnessReceiptLineageVerificationResponse(
        valid=True,
        lineage=record.to_lineage().to_payload(),
    )


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