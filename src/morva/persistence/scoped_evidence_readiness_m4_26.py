from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.evidence_lifecycle_records import EvidenceLifecycleRepository
from morva.persistence.evidence_role_binding_records import (
    EvidenceRoleBindingError,
    EvidenceRoleBindingRepository,
)
from morva.persistence.evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from morva.runtime.evidence_lifecycle import EvidenceLifecycleError, build_lifecycle_assessment
from morva.runtime.evidence_readiness import (
    EvidenceReadinessAssessment,
    EvidenceReadinessError,
    build_readiness_assessment,
)
from morva.runtime.evidence_registry_bridge import (
    EvidenceRegistryBridgeError,
    build_registry_projection,
)
from morva.security.policy import Scope


class ScopedEvidenceReadinessPersistenceError(ValueError):
    """Raised when current scoped evidence readiness cannot be rebuilt safely."""


def build_current_scoped_evidence_readiness(
    session: Session,
    *,
    organization_scope: str,
    organization_scope_id: str,
    checked_at: datetime,
) -> EvidenceReadinessAssessment:
    try:
        normalized_scope, scope_id = normalize_readiness_scope(
            organization_scope,
            organization_scope_id,
        )
    except ReadinessScopeBindingError as exc:
        raise ScopedEvidenceReadinessPersistenceError(str(exc)) from exc
    scope = Scope(normalized_scope)

    accepted_query = select(AuthoritativeEvidenceSubmissionRecord).where(
        AuthoritativeEvidenceSubmissionRecord.status == "accepted",
        AuthoritativeEvidenceSubmissionRecord.submission_scope == scope.value,
        AuthoritativeEvidenceSubmissionRecord.submission_scope_id == scope_id,
    )
    accepted_records = session.scalars(
        accepted_query.order_by(
            AuthoritativeEvidenceSubmissionRecord.evidence_id.asc()
        )
    ).all()
    try:
        accepted_records = _normalize_loaded_submissions(session, accepted_records)
        registry, _ = build_registry_projection(
            accepted_records,
            projected_at=checked_at,
        )
        binding_repository = EvidenceRoleBindingRepository(session)
        bindings, convergence = binding_repository.list_current(
            principal_scope=scope,
            principal_scope_id=scope_id,
            checked_at=checked_at,
            exact_scope=True,
        )
        lifecycle_repository = EvidenceLifecycleRepository(session)
        lifecycle_records = lifecycle_repository.list_for_scope(
            scope=scope,
            scope_id=scope_id,
        )
        lifecycle = build_lifecycle_assessment(
            registry,
            repository="Ali-Marandi/Morva",
            checked_at=checked_at,
            links=tuple(
                record.to_link()
                for record in lifecycle_records
            ),
        )
        return build_readiness_assessment(
            registry,
            convergence,
            repository="Ali-Marandi/Morva",
            checked_at=checked_at,
            receipts=tuple(
                record.to_receipt()
                for record in bindings
            ),
            lifecycle=lifecycle,
        )
    except (
        EvidenceRegistryBridgeError,
        EvidenceRoleBindingError,
        EvidenceLifecycleError,
        EvidenceReadinessError,
        ValueError,
    ) as exc:
        raise ScopedEvidenceReadinessPersistenceError(
            f"current scoped evidence readiness rebuild failed: {exc}"
        ) from exc



def _normalize_loaded_submissions(
    session: Session,
    records: list[AuthoritativeEvidenceSubmissionRecord],
) -> list[AuthoritativeEvidenceSubmissionRecord]:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        for record in records:
            for field_name in (
                "effective_from",
                "effective_to",
                "expires_at",
                "submitted_at",
                "decided_at",
            ):
                value = getattr(record, field_name)
                if value is not None and value.tzinfo is None:
                    setattr(record, field_name, value.replace(tzinfo=timezone.utc))
    return records
