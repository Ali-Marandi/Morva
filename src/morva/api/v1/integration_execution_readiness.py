from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from morva.audit.persistence import append_audit_event

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

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
from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRecord,
    HistoricalFreshnessChainVerificationReceiptPersistenceError,
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
    IndependentHistoricalFreshnessReceiptVerificationRepository,
    IndependentHistoricalFreshnessReceiptVerificationRecord,
)
from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
    HistoricalFreshnessVerificationHistoryIntegrityRepository,
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
)
from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM452VerificationReceiptHistoryIntegrityRecord,
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.historical_m4_60_receipt_history_integrity_m4_61 import (
    HistoricalM460ReceiptHistoryIntegrityPersistenceError,
    HistoricalM460ReceiptHistoryIntegrityRecord,
    HistoricalM460ReceiptHistoryIntegrityRepository,
)
from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityPersistenceError,
    HistoricalM463ReceiptHistoryIntegrityRecord,
    HistoricalM463ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_61_receipt_history_verifier_m4_62 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_61_receipt_history_integrity,
)
from morva.runtime.independent_historical_m4_53_receipt_history_verifier_m4_54 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_53_receipt_history_integrity,
)
from morva.runtime.independent_historical_m4_64_receipt_history_verifier_m4_65 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_64_receipt_history_integrity,
)
from morva.runtime.independent_historical_m4_55_receipt_verifier_m4_56 import (
    IndependentHistoricalM455ReceiptVerificationError,
    independently_verify_historical_m4_55_receipt as reconstruct_m4_55_receipt_verification,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationPersistenceError,
    IndependentHistoricalM455ReceiptVerificationRecord,
    IndependentHistoricalM455ReceiptVerificationRepository,
)
from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM457VerificationReceiptHistoryIntegrityRecord,
    HistoricalM457VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_58_receipt_history_verifier_m4_59 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_58_receipt_history_integrity,
)
from morva.persistence.scoped_evidence_readiness_m4_26 import (
    ScopedEvidenceReadinessPersistenceError,
)
from morva.runtime.persist_scope_bound_readiness_convergence_m4_27 import (
    PersistScopeBoundReadinessConvergenceError,
    persist_latest_scope_bound_readiness_convergence,
)
from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergenceError,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    HistoricalFreshnessChainVerificationError,
    verify_historical_freshness_chain,
)
from morva.runtime.independent_historical_freshness_chain_verification_receipt_verifier_m4_45 import (
    IndependentHistoricalFreshnessChainVerificationReceiptError,
    verify_historical_freshness_chain_verification_receipt as _verify_m4_44_receipt_independent,
)
from morva.runtime.independent_historical_freshness_verification_history_integrity_verifier_m4_48 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
    independently_verify_historical_freshness_verification_history_integrity,
)
from morva.runtime.independent_historical_verification_receipt_history_integrity_verifier_m4_51 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityError,
    independently_verify_historical_independent_verification_receipt_history_integrity,
)
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize
from morva.runtime.readiness_scope_binding_m4_25 import (
    ReadinessScopeBindingError,
    normalize_readiness_scope,
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


class IntegrationExecutionReadinessVerificationHistoryResponse(BaseModel):
    items: list[IntegrationExecutionReadinessVerificationResponse]
    has_more: bool
    next_verified_before: datetime | None = None
    next_before_id: UUID | None = None


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


def _normalize_history_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=422,
            detail="before_created_at must be timezone-aware",
        )
    return value.astimezone(timezone.utc)

@router.get(
    "/readiness/history",
    response_model=IntegrationExecutionReadinessVerificationHistoryResponse,
)
def list_integration_execution_readiness_history(
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
    if verified_before is not None:
        verified_before = _normalize_history_timestamp(verified_before)
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)

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
    records = records[:limit]
    items = [
        IntegrationExecutionReadinessVerificationResponse(
            assessment=record.to_verification().assessment.to_payload(),
            verification_fingerprint=record.verification_fingerprint,
            verified_at=record.verified_at,
            created_at=record.created_at,
            organization_scope=record.organization_scope,
            organization_scope_id=record.organization_scope_id,
            scope_binding_fingerprint=record.scope_binding_fingerprint,
        )
        for record in records
    ]
    return IntegrationExecutionReadinessVerificationHistoryResponse(
        items=items,
        has_more=has_more,
        next_verified_before=records[-1].verified_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
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

class HistoricalFreshnessChainVerificationResponse(BaseModel):
    valid: bool
    verification: dict[str, object]


class HistoricalFreshnessChainVerificationReceiptResponse(BaseModel):
    id: UUID
    lineage_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class HistoricalFreshnessChainVerificationReceiptHistoryResponse(BaseModel):
    items: list[HistoricalFreshnessChainVerificationReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalFreshnessChainVerificationReceiptResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalFreshnessReceiptVerificationResponse(BaseModel):
    id: UUID
    receipt_id: UUID
    lineage_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalFreshnessReceiptVerificationHistoryResponse(BaseModel):
    items: list[IndependentHistoricalFreshnessReceiptVerificationResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalSnapshotFreshnessReceiptLineageHistoryResponse(BaseModel):
    items: list[HistoricalSnapshotFreshnessReceiptLineageResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


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
        except ScopeBoundReadinessConvergencePersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not records:
        raise HTTPException(
            status_code=404,
            detail="no persisted scope-bound readiness convergence found",
        )
    return ScopeBoundReadinessConvergenceResponse(
        convergence=records[0].to_convergence().to_payload(),
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
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="readiness convergence receipts are ministry-managed",
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
            append_audit_event(
                event_type="integration.readiness.scope_bound_convergence.recorded",
                entity_type="scope_bound_readiness_convergence",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "candidate_sha": record.candidate_sha,
                    "target_environment": record.target_environment,
                    "organization_scope": record.organization_scope,
                    "organization_scope_id": record.organization_scope_id,
                    "convergence_fingerprint": record.convergence_fingerprint,
                },
                reason="scope-bound readiness convergence receipt persisted",
                session=session,
            )
            session.commit()
        except HTTPException:
            raise
        except (
            PersistScopeBoundReadinessConvergenceError,
            IntegrationExecutionReadinessPersistenceError,
            ScopedEvidenceReadinessPersistenceError,
            ScopeBoundReadinessConvergenceError,
            ScopeBoundReadinessConvergencePersistenceError,
        ) as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ScopeBoundReadinessConvergenceReceiptResponse(
        id=record.id,
        convergence=record.to_convergence().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/history",
    response_model=ScopeBoundReadinessConvergenceReceiptHistoryResponse,
)
def list_scope_bound_readiness_convergence_history(
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
    if scope_filter is None or scope_id_filter is None:
        raise HTTPException(
            status_code=422,
            detail="organization_scope and organization_scope_id are required",
        )
    if (checked_before is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="checked_before and before_id must be supplied together",
        )
    if checked_before is not None:
        checked_before = _normalize_history_timestamp(checked_before)
    candidate_sha = _normalize_candidate_sha_for_history(candidate_sha)
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
    records = records[:limit]
    items = [
        ScopeBoundReadinessConvergenceReceiptResponse(
            id=record.id,
            convergence=record.to_convergence().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return ScopeBoundReadinessConvergenceReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_checked_at=records[-1].checked_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
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



@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound",
    response_model=HistoricalSnapshotBoundPolicyReadinessFreshnessResponse,
)
def get_historical_snapshot_bound_readiness_convergence_freshness(
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
) -> HistoricalSnapshotBoundPolicyReadinessFreshnessResponse:
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
        convergence_repository = ScopeBoundReadinessConvergenceRepository(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
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
            policy_bound = build_policy_bound_freshness(
                policy_record.to_policy(),
                records[0].to_convergence(),
                observed_at=datetime.now(timezone.utc),
            )
            snapshot = snapshot_record.to_snapshot()
            freshness = build_historical_snapshot_bound_policy_readiness_freshness(
                policy_bound,
                snapshot_id=snapshot_record.id,
                snapshot_fingerprint=snapshot.fingerprint,
                registry_integrity_version=snapshot.integrity_version,
                registry_policy_count=snapshot.policy_count,
                registry_fingerprint=snapshot.registry_fingerprint,
            )
        except HTTPException:
            raise
        except (
            ScopeBoundReadinessConvergencePersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            FreshnessPolicyRegistrySnapshotPersistenceError,
            PolicyBoundReadinessFreshnessError,
            HistoricalSnapshotBoundPolicyReadinessFreshnessError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalSnapshotBoundPolicyReadinessFreshnessResponse(
        freshness=freshness.to_payload(),
    )


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
                snapshot_id=snapshot.id,
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
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts/{receipt_id}/verify",
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
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/history",
    response_model=HistoricalSnapshotFreshnessReceiptLineageHistoryResponse,
)
def list_historical_snapshot_freshness_receipt_lineage(
    freshness_receipt_id: UUID | None = Query(default=None),
    historical_binding_id: UUID | None = Query(default=None),
    snapshot_id: UUID | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalSnapshotFreshnessReceiptLineageHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness receipt lineage history is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        try:
            records, has_more = repository.list(
                freshness_receipt_id=freshness_receipt_id,
                historical_binding_id=historical_binding_id,
                snapshot_id=snapshot_id,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalSnapshotFreshnessReceiptLineagePersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        HistoricalSnapshotFreshnessReceiptLineageResponse(
            id=record.id,
            lineage=record.to_lineage().to_payload(),
            bound_by=record.bound_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    next_before_created_at = records[-1].created_at if has_more and records else None
    next_before_id = records[-1].id if has_more and records else None
    return HistoricalSnapshotFreshnessReceiptLineageHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=next_before_created_at,
        next_before_id=next_before_id,
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
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/{lineage_id}/verify-chain",
    response_model=HistoricalFreshnessChainVerificationResponse,
)
def verify_historical_freshness_receipt_chain(
    lineage_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessChainVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        lineage_repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        freshness_repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            lineage_record = lineage_repository.verify(lineage_id)
            lineage = lineage_record.to_lineage()
            freshness_record = freshness_repository.verify(lineage.freshness_receipt_id)
            freshness = freshness_record.to_freshness()
            binding_record = binding_repository.verify(lineage.historical_binding_id)
            binding = binding_record.to_binding()
            snapshot_record = snapshot_repository.reconstruct(
                lineage.snapshot_id,
                policy_repository,
            )
            snapshot = snapshot_record.to_snapshot()
            verification = verify_historical_freshness_chain(
                freshness_receipt_id=freshness_record.id,
                freshness=freshness,
                historical_binding_id=binding_record.id,
                historical_binding=binding,
                snapshot_id=snapshot_record.id,
                snapshot=snapshot,
                lineage=lineage,
            )
        except (
            HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
            HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
            HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError,
            FreshnessPolicyRegistrySnapshotPersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            HistoricalFreshnessChainVerificationError,
        ) as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return HistoricalFreshnessChainVerificationResponse(
        valid=verification.valid,
        verification=verification.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/{lineage_id}/verification-receipts",
    response_model=HistoricalFreshnessChainVerificationReceiptResponse,
)
def persist_historical_freshness_chain_verification_receipt(
    lineage_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessChainVerificationReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness chain verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        try:
            record = repository.record(
                lineage_id=lineage_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type="integration.readiness.historical_freshness_chain_verification.recorded",
                entity_type="historical_freshness_chain_verification_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "lineage_id": str(record.lineage_id),
                    "state": record.state,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.43 historical freshness chain verification receipt persisted",
                session=session,
            )
            session.commit()
        except HistoricalFreshnessChainVerificationReceiptPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return HistoricalFreshnessChainVerificationReceiptResponse(
        id=record.id,
        lineage_id=record.lineage_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/verification-history",
    response_model=HistoricalFreshnessChainVerificationReceiptHistoryResponse,
)
def list_historical_freshness_chain_verification_history(
    lineage_id: UUID | None = Query(default=None),
    state: str | None = Query(default=None, pattern="^(verified|blocked)$"),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessChainVerificationReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness chain verification history is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        try:
            records, has_more = repository.list(
                lineage_id=lineage_id,
                state=state,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalFreshnessChainVerificationReceiptPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        HistoricalFreshnessChainVerificationReceiptResponse(
            id=record.id,
            lineage_id=record.lineage_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    next_before_created_at = records[-1].created_at if has_more and records else None
    next_before_id = records[-1].id if has_more and records else None
    return HistoricalFreshnessChainVerificationReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=next_before_created_at,
        next_before_id=next_before_id,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/verification-receipts/{receipt_id}/verify",
    response_model=HistoricalFreshnessChainVerificationReceiptResponse,
)
def verify_historical_freshness_chain_verification_receipt(
    receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessChainVerificationReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        try:
            record = repository.verify(receipt_id)
        except HistoricalFreshnessChainVerificationReceiptPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalFreshnessChainVerificationReceiptResponse(
        id=record.id,
        lineage_id=record.lineage_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/verification-receipts/{receipt_id}/verify-independent",
    response_model=IndependentHistoricalFreshnessChainVerificationReceiptResponse,
)
def independently_verify_historical_freshness_chain_verification_receipt(
    receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessChainVerificationReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        receipt_record = session.get(
            HistoricalFreshnessChainVerificationReceiptRecord,
            receipt_id,
        )
        if receipt_record is None:
            raise HTTPException(
                status_code=404,
                detail="historical freshness chain verification receipt not found",
            )
        lineage_repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        freshness_repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        try:
            lineage_record = lineage_repository.verify(receipt_record.lineage_id)
            lineage = lineage_record.to_lineage()
            freshness_record = freshness_repository.verify(lineage.freshness_receipt_id)
            freshness = freshness_record.to_freshness()
            binding_record = binding_repository.verify(lineage.historical_binding_id)
            binding = binding_record.to_binding()
            snapshot_record = snapshot_repository.reconstruct(
                lineage.snapshot_id,
                policy_repository,
            )
            reconstructed = verify_historical_freshness_chain(
                freshness_receipt_id=freshness_record.id,
                freshness=freshness,
                historical_binding_id=binding_record.id,
                historical_binding=binding,
                snapshot_id=snapshot_record.id,
                snapshot=snapshot_record.to_snapshot(),
                lineage=lineage,
            )
            independent = _verify_m4_44_receipt_independent(
                receipt=receipt_record,
                reconstructed=reconstructed,
            )
        except (
            HistoricalFreshnessChainVerificationReceiptPersistenceError,
            HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
            HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
            HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError,
            FreshnessPolicyRegistrySnapshotPersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            HistoricalFreshnessChainVerificationError,
            IndependentHistoricalFreshnessChainVerificationReceiptError,
        ) as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return IndependentHistoricalFreshnessChainVerificationReceiptResponse(
        verification=independent.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/verification-receipts/{receipt_id}/independent-verification-receipts",
    response_model=IndependentHistoricalFreshnessReceiptVerificationResponse,
)
def persist_independent_historical_freshness_receipt_verification(
    receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessReceiptVerificationResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="independent historical freshness receipt verifications are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        try:
            record = repository.record(
                receipt_id=receipt_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type="integration.readiness.independent_historical_freshness_receipt_verification.recorded",
                entity_type="independent_historical_freshness_receipt_verification",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "receipt_id": str(record.receipt_id),
                    "lineage_id": str(record.lineage_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.45 independent historical freshness receipt verification persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalFreshnessReceiptVerificationPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalFreshnessReceiptVerificationResponse(
        id=record.id,
        receipt_id=record.receipt_id,
        lineage_id=record.lineage_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history",
    response_model=IndependentHistoricalFreshnessReceiptVerificationHistoryResponse,
)
def list_independent_historical_freshness_receipt_verifications(
    receipt_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    chain_valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessReceiptVerificationHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="independent historical freshness receipt verification history is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        try:
            records, has_more = repository.list(
                receipt_id=receipt_id,
                valid=valid,
                chain_valid=chain_valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalFreshnessReceiptVerificationPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        IndependentHistoricalFreshnessReceiptVerificationResponse(
            id=record.id,
            receipt_id=record.receipt_id,
            lineage_id=record.lineage_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalFreshnessReceiptVerificationHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-receipts/{verification_receipt_id}/verify",
    response_model=IndependentHistoricalFreshnessReceiptVerificationResponse,
)
def verify_independent_historical_freshness_receipt_verification(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessReceiptVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        try:
            record = repository.verify(verification_receipt_id)
        except IndependentHistoricalFreshnessReceiptVerificationPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalFreshnessReceiptVerificationResponse(
        id=record.id,
        receipt_id=record.receipt_id,
        lineage_id=record.lineage_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
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


class HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime



class IndependentHistoricalFreshnessVerificationHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class HistoricalFreshnessVerificationHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime


class HistoricalIndependentVerificationReceiptHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalVerificationReceiptHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime


class HistoricalM452VerificationReceiptHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalM460ReceiptHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime


class HistoricalM460ReceiptHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalM460ReceiptHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class HistoricalM463ReceiptHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime


class HistoricalM463ReceiptHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalM463ReceiptHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalM464ReceiptHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalM461ReceiptHistoryIntegrityReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalM461ReceiptHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalM453ReceiptHistoryIntegrityReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalM455ReceiptVerificationResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalM455ReceiptVerificationReceiptResponse(BaseModel):
    id: UUID
    receipt_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalM455ReceiptVerificationReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalM455ReceiptVerificationReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalM453ReceiptHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse(BaseModel):
    id: UUID
    integrity: dict[str, object]
    captured_by: str
    created_at: datetime


class HistoricalM457VerificationReceiptHistoryIntegrityHistoryResponse(BaseModel):
    items: list[HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


class IndependentHistoricalM458ReceiptHistoryIntegrityResponse(BaseModel):
    verification: dict[str, object]


class IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalM458ReceiptHistoryIntegrityReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/snapshots",
    response_model=HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse,
)
def capture_historical_freshness_verification_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness verification history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_freshness_verification_history_integrity.snapshot.recorded"
                ),
                entity_type="historical_freshness_verification_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "chain_valid_count": record.chain_valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.47 historical freshness verification history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalFreshnessVerificationHistoryIntegrityPersistenceError as exc:
            session.rollback()
            status = 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/snapshots",
    response_model=HistoricalFreshnessVerificationHistoryIntegrityHistoryResponse,
)
def list_historical_freshness_verification_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessVerificationHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="historical freshness verification history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalFreshnessVerificationHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalFreshnessVerificationHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/snapshots/{snapshot_id}/verify",
    response_model=HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse,
)
def verify_historical_freshness_verification_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        try:
            record = repository.verify(snapshot_id)
        except HistoricalFreshnessVerificationHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalFreshnessVerificationHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/snapshots/{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalFreshnessVerificationHistoryIntegrityResponse,
)
def independently_verify_historical_freshness_verification_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(
            HistoricalFreshnessVerificationHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.47 history integrity snapshot not found",
            )
        source_repository = IndependentHistoricalFreshnessReceiptVerificationRepository(
            session
        )
        source_query = (
            select(IndependentHistoricalFreshnessReceiptVerificationRecord)
            .where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.asc(),
                IndependentHistoricalFreshnessReceiptVerificationRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = (
                independently_verify_historical_freshness_verification_history_integrity(
                    snapshot=record,
                    source_records=source_records,
                )
            )
        except IndependentHistoricalFreshnessVerificationHistoryIntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalFreshnessVerificationHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "snapshots/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse,
)
def persist_independent_historical_freshness_verification_history_integrity_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="independent history-integrity verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_historical_freshness_verification_history_integrity."
                    "receipt.recorded"
                ),
                entity_type="independent_historical_freshness_verification_history_integrity_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.49 independent M4.48 verification receipt persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/verification-history",
    response_model=IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptHistoryResponse,
)
def list_independent_historical_freshness_verification_history_integrity_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="independent history-integrity verification history is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipts/{verification_receipt_id}/verify",
    response_model=IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse,
)
def verify_independent_historical_freshness_verification_history_integrity_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.verify(verification_receipt_id)
        except IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-snapshots",
    response_model=HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse,
)
def capture_historical_independent_verification_receipt_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.50 receipt-history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_independent_verification_receipt_history_integrity."
                    "snapshot.recorded"
                ),
                entity_type="historical_independent_verification_receipt_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.50 historical M4.49 receipt-history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-snapshots",
    response_model=HistoricalIndependentVerificationReceiptHistoryIntegrityHistoryResponse,
)
def list_historical_independent_verification_receipt_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalIndependentVerificationReceiptHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.50 receipt-history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalIndependentVerificationReceiptHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-snapshots/{snapshot_id}/verify",
    response_model=HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse,
)
def verify_historical_independent_verification_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            record = repository.verify(snapshot_id)
        except HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalIndependentVerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )



@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-snapshots/{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalVerificationReceiptHistoryIntegrityResponse,
)
def independently_verify_historical_independent_verification_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalVerificationReceiptHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(
            HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.50 receipt-history integrity snapshot not found",
            )
        source_repository = (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
                session
            )
        )
        source_query = (
            select(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = (
                independently_verify_historical_independent_verification_receipt_history_integrity(
                    snapshot=record,
                    source_records=source_records,
                )
            )
        except (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalVerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalVerificationReceiptHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )




@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-integrity/snapshots/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse,
)
def persist_independent_historical_verification_receipt_history_integrity_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.52 verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_historical_verification_receipt_history_integrity."
                    "receipt.recorded"
                ),
                entity_type="independent_historical_verification_receipt_history_integrity_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.52 independent M4.51 verification receipt persisted",
                session=session,
            )
            session.commit()
        except (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-integrity/verification-history",
    response_model=IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptHistoryResponse,
)
def list_independent_historical_verification_receipt_history_integrity_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.52 verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return (
        IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptHistoryResponse(
            items=items,
            has_more=has_more,
            next_before_created_at=records[-1].created_at
            if has_more and records
            else None,
            next_before_id=records[-1].id if has_more and records else None,
        )
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "verification-receipt-history-integrity/verification-receipts/"
    "{verification_receipt_id}/verify",
    response_model=IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse,
)
def verify_independent_historical_verification_receipt_history_integrity_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        try:
            record = repository.verify(verification_receipt_id)
        except (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )



@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-52-history-integrity-snapshots",
    response_model=HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse,
)
def capture_historical_m4_52_verification_receipt_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.53 history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalM452VerificationReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_m4_52_verification_receipt_history_integrity."
                    "snapshot.recorded"
                ),
                entity_type="historical_m4_52_verification_receipt_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.53 point-in-time M4.52 receipt-history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-52-history-integrity-snapshots",
    response_model=HistoricalM452VerificationReceiptHistoryIntegrityHistoryResponse,
)
def list_historical_m4_52_verification_receipt_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM452VerificationReceiptHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.53 history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = HistoricalM452VerificationReceiptHistoryIntegrityRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalM452VerificationReceiptHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-52-history-integrity-snapshots/{snapshot_id}/verify",
    response_model=HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse,
)
def verify_historical_m4_52_verification_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalM452VerificationReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.verify(snapshot_id)
        except HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalM452VerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )



@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-52-history-integrity-snapshots/{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalM453ReceiptHistoryIntegrityResponse,
)
def independently_verify_historical_m4_53_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM453ReceiptHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(
            HistoricalM452VerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.53 receipt-history integrity snapshot not found",
            )
        source_repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        source_query = (
            select(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = (
                independently_verify_historical_m4_53_receipt_history_integrity(
                    snapshot=record,
                    source_records=source_records,
                )
            )
        except (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalM453ReceiptHistoryIntegrityError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalM453ReceiptHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )

@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-53-history-integrity-snapshots/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse,
)
def persist_independent_historical_m4_53_receipt_history_integrity_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.55 verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_historical_m4_53_receipt_history_verification."
                    "receipt.recorded"
                ),
                entity_type="independent_historical_m4_53_receipt_history_verification_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.55 independent M4.54 verification receipt persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipt-history",
    response_model=IndependentHistoricalM453ReceiptHistoryIntegrityReceiptHistoryResponse,
)
def list_independent_historical_m4_53_receipt_history_integrity_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM453ReceiptHistoryIntegrityReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.55 verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalM453ReceiptHistoryIntegrityReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipts/{verification_receipt_id}/verify",
    response_model=IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse,
)
def verify_independent_historical_m4_53_receipt_history_integrity_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.verify(verification_receipt_id)
        except IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM453ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )





@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipts/{verification_receipt_id}/verify-independent",
    response_model=IndependentHistoricalM455ReceiptVerificationResponse,
)
def independently_verify_historical_m4_55_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM455ReceiptVerificationResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        receipt = session.get(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if receipt is None:
            raise HTTPException(
                status_code=404,
                detail="M4.55 verification receipt not found",
            )
        snapshot = session.get(
            HistoricalM452VerificationReceiptHistoryIntegrityRecord,
            receipt.snapshot_id,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="M4.53 history integrity snapshot not found",
            )
        source_repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        source_query = (
            select(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            HistoricalM452VerificationReceiptHistoryIntegrityRepository(session).verify(
                snapshot.id
            )
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = reconstruct_m4_55_receipt_verification(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
            )
        except (
            HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError,
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalM455ReceiptVerificationError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalM455ReceiptVerificationResponse(
        verification=verification.to_payload(),
    )



@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-58-verification-receipts/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse,
)
def persist_independent_historical_m4_58_verification_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.60 verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_m4_58_receipt_history_verification."
                    "receipt.recorded"
                ),
                entity_type="independent_m4_58_verification_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.60 independent M4.59 verification result persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-58-verification-receipts/verification-history",
    response_model=IndependentHistoricalM458ReceiptHistoryIntegrityReceiptHistoryResponse,
)
def list_independent_historical_m4_58_verification_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM458ReceiptHistoryIntegrityReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.60 verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalM458ReceiptHistoryIntegrityReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-58-verification-receipts/verification-receipts/"
    "{verification_receipt_id}/verify",
    response_model=IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse,
)
def verify_independent_historical_m4_58_verification_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        try:
            record = repository.verify(verification_receipt_id)
        except IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM458ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-57-verification-history-integrity-snapshots/"
    "{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalM458ReceiptHistoryIntegrityResponse,
)
def independently_verify_historical_m4_58_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM458ReceiptHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(
            HistoricalM457VerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.58 receipt-history integrity snapshot not found",
            )
        source_repository = IndependentHistoricalM455ReceiptVerificationRepository(
            session
        )
        source_query = (
            select(IndependentHistoricalM455ReceiptVerificationRecord)
            .where(
                IndependentHistoricalM455ReceiptVerificationRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalM455ReceiptVerificationRecord.created_at.asc(),
                IndependentHistoricalM455ReceiptVerificationRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = (
                independently_verify_historical_m4_58_receipt_history_integrity(
                    snapshot=record,
                    source_records=source_records,
                )
            )
        except (
            IndependentHistoricalM455ReceiptVerificationPersistenceError,
            IndependentHistoricalM458ReceiptHistoryIntegrityError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalM458ReceiptHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-57-verification-history-integrity-snapshots",
    response_model=HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse,
)
def capture_historical_m4_57_verification_receipt_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.58 history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_m4_57_verification_receipt_history_integrity."
                    "snapshot.recorded"
                ),
                entity_type="historical_m4_57_verification_receipt_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.58 point-in-time M4.57 receipt-history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-57-verification-history-integrity-snapshots",
    response_model=HistoricalM457VerificationReceiptHistoryIntegrityHistoryResponse,
)
def list_historical_m4_57_verification_receipt_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM457VerificationReceiptHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.58 history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalM457VerificationReceiptHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-57-verification-history-integrity-snapshots/{snapshot_id}/verify",
    response_model=HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse,
)
def verify_historical_m4_57_verification_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.verify(snapshot_id)
        except HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalM457VerificationReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipts/{verification_receipt_id}/independent-verification-receipts",
    response_model=IndependentHistoricalM455ReceiptVerificationReceiptResponse,
)
def persist_independent_historical_m4_55_receipt_verification(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM455ReceiptVerificationReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.57 verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        try:
            record = repository.record(
                receipt_id=verification_receipt_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_m4_55_receipt_verification."
                    "receipt.recorded"
                ),
                entity_type="independent_m4_54_receipt_verification_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "receipt_id": str(record.receipt_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.57 independent M4.56 verification result persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalM455ReceiptVerificationPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM455ReceiptVerificationReceiptResponse(
        id=record.id,
        receipt_id=record.receipt_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipts/independent-verification-history",
    response_model=IndependentHistoricalM455ReceiptVerificationReceiptHistoryResponse,
)
def list_independent_historical_m4_55_receipt_verifications(
    receipt_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM455ReceiptVerificationReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.57 verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        try:
            records, has_more = repository.list(
                receipt_id=receipt_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalM455ReceiptVerificationPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        IndependentHistoricalM455ReceiptVerificationReceiptResponse(
            id=record.id,
            receipt_id=record.receipt_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalM455ReceiptVerificationReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-54-verification-receipts/independent-verification-receipts/{verification_id}/verify",
    response_model=IndependentHistoricalM455ReceiptVerificationReceiptResponse,
)
def verify_persisted_independent_historical_m4_55_receipt_verification(
    verification_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM455ReceiptVerificationReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        try:
            record = repository.verify(verification_id)
        except IndependentHistoricalM455ReceiptVerificationPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM455ReceiptVerificationReceiptResponse(
        id=record.id,
        receipt_id=record.receipt_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots",
    response_model=HistoricalM460ReceiptHistoryIntegritySnapshotResponse,
)
def capture_historical_m4_60_receipt_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM460ReceiptHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.61 history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_m4_60_receipt_history_integrity."
                    "snapshot.recorded"
                ),
                entity_type="historical_m4_60_receipt_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.61 point-in-time M4.60 receipt-history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalM460ReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalM460ReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots",
    response_model=HistoricalM460ReceiptHistoryIntegrityHistoryResponse,
)
def list_historical_m4_60_receipt_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM460ReceiptHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.61 history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalM460ReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalM460ReceiptHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalM460ReceiptHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots/{snapshot_id}/verify",
    response_model=HistoricalM460ReceiptHistoryIntegritySnapshotResponse,
)
def verify_historical_m4_60_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM460ReceiptHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.verify(snapshot_id)
        except HistoricalM460ReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalM460ReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots/{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalM461ReceiptHistoryIntegrityResponse,
)
def independently_verify_historical_m4_61_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM461ReceiptHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(HistoricalM460ReceiptHistoryIntegrityRecord, snapshot_id)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.61 receipt-history integrity snapshot not found",
            )
        source_repository = (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(session)
        )
        source_query = (
            select(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = independently_verify_historical_m4_61_receipt_history_integrity(
                snapshot=record,
                source_records=source_records,
            )
        except (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalM461ReceiptHistoryIntegrityError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalM461ReceiptHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )


@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse,
)
def persist_independent_historical_m4_62_verification_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.63 verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(session)
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "independent_historical_m4_61_receipt_history_integrity."
                    "receipt.recorded"
                ),
                entity_type="independent_m4_61_verification_receipt",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.63 independent M4.62 verification receipt persisted",
                session=session,
            )
            session.commit()
        except (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots/verification-history",
    response_model=IndependentHistoricalM461ReceiptHistoryIntegrityReceiptHistoryResponse,
)
def list_independent_historical_m4_62_verification_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM461ReceiptHistoryIntegrityReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.63 verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(session)
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalM461ReceiptHistoryIntegrityReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-60-receipt-history-integrity-snapshots/verification-receipts/"
    "{verification_receipt_id}/verify",
    response_model=IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse,
)
def verify_independent_historical_m4_62_verification_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(session)
        )
        try:
            record = repository.verify(verification_receipt_id)
        except (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError
        ) as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return IndependentHistoricalM461ReceiptHistoryIntegrityReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )



@router.post(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-63-receipt-history-integrity-snapshots",
    response_model=HistoricalM463ReceiptHistoryIntegritySnapshotResponse,
)
def capture_historical_m4_63_receipt_history_integrity_snapshot(
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM463ReceiptHistoryIntegritySnapshotResponse:
    authorize(
        principal,
        "evidence.binding.write",
        principal.scope,
        privileged=True,
    )
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.64 history integrity is ministry-managed",
        )
    with SessionLocal() as session:
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.capture(captured_by=principal.user_id)
            integrity = record.to_integrity()
            append_audit_event(
                event_type=(
                    "integration.readiness."
                    "historical_m4_63_receipt_history_integrity."
                    "snapshot.recorded"
                ),
                entity_type="historical_m4_63_receipt_history_integrity_snapshot",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "record_count": record.record_count,
                    "valid_count": record.valid_count,
                    "history_fingerprint": record.history_fingerprint,
                    "fingerprint": record.fingerprint,
                },
                reason="M4.64 point-in-time M4.63 receipt-history integrity snapshot persisted",
                session=session,
            )
            session.commit()
        except HistoricalM463ReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HistoricalM463ReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=integrity.to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-63-receipt-history-integrity-snapshots",
    response_model=HistoricalM463ReceiptHistoryIntegrityHistoryResponse,
)
def list_historical_m4_63_receipt_history_integrity_snapshots(
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM463ReceiptHistoryIntegrityHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.64 history integrity is ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        try:
            records, has_more = repository.list(
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except HistoricalM463ReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    items = [
        HistoricalM463ReceiptHistoryIntegritySnapshotResponse(
            id=record.id,
            integrity=record.to_integrity().to_payload(),
            captured_by=record.captured_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return HistoricalM463ReceiptHistoryIntegrityHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-63-receipt-history-integrity-snapshots/{snapshot_id}/verify",
    response_model=HistoricalM463ReceiptHistoryIntegritySnapshotResponse,
)
def verify_historical_m4_63_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> HistoricalM463ReceiptHistoryIntegritySnapshotResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        try:
            record = repository.verify(snapshot_id)
        except HistoricalM463ReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc
    return HistoricalM463ReceiptHistoryIntegritySnapshotResponse(
        id=record.id,
        integrity=record.to_integrity().to_payload(),
        captured_by=record.captured_by,
        created_at=record.created_at,
    )



@router.get(
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-63-receipt-history-integrity-snapshots/{snapshot_id}/verify-independent",
    response_model=IndependentHistoricalM464ReceiptHistoryIntegrityResponse,
)
def independently_verify_historical_m4_64_receipt_history_integrity_snapshot(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM464ReceiptHistoryIntegrityResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.get(
            HistoricalM463ReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HTTPException(
                status_code=404,
                detail="M4.64 receipt-history integrity snapshot not found",
            )
        source_repository = (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        source_query = (
            select(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            verification = (
                independently_verify_historical_m4_64_receipt_history_integrity(
                    snapshot=record,
                    source_records=source_records,
                )
            )
        except (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalM464ReceiptHistoryIntegrityError,
        ) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return IndependentHistoricalM464ReceiptHistoryIntegrityResponse(
        verification=verification.to_payload(),
    )
