from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.persistence.scope_bound_readiness_convergence_records_m4_27 import (
    ScopeBoundReadinessConvergencePersistenceError,
    ScopeBoundReadinessConvergenceRecord,
    ScopeBoundReadinessConvergenceRepository,
)
from morva.persistence.scoped_evidence_readiness_m4_26 import (
    ScopedEvidenceReadinessPersistenceError,
    build_current_scoped_evidence_readiness,
)
from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergenceError,
    build_scope_bound_readiness_convergence,
)


class PersistScopeBoundReadinessConvergenceError(ValueError):
    """Raised when an M4.26 convergence observation cannot be persisted safely."""


def persist_latest_scope_bound_readiness_convergence(
    session: Session,
    *,
    candidate_sha: str | None,
    target_environment: str | None,
    organization_scope: str,
    organization_scope_id: str,
    checked_at: datetime,
    recorded_by: str,
) -> ScopeBoundReadinessConvergenceRecord:
    if not recorded_by.strip():
        raise PersistScopeBoundReadinessConvergenceError(
            "recorded_by is required"
        )

    verification_repository = IntegrationExecutionReadinessVerificationRepository(
        session
    )
    try:
        verification_record = verification_repository.latest(
            repository="Ali-Marandi/Morva",
            candidate_sha=candidate_sha,
            target_environment=target_environment,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
        )
        if verification_record is None:
            raise PersistScopeBoundReadinessConvergenceError(
                "no persisted integration execution readiness verification found"
            )
        verification = verification_record.to_verification()
        current_readiness = build_current_scoped_evidence_readiness(
            session,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            checked_at=checked_at,
        )
        convergence = build_scope_bound_readiness_convergence(
            verification,
            current_readiness,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            checked_at=checked_at,
        )
        return ScopeBoundReadinessConvergenceRepository(session).record(
            convergence,
            recorded_by=recorded_by,
        )
    except (
        IntegrationExecutionReadinessPersistenceError,
        ScopedEvidenceReadinessPersistenceError,
        ScopeBoundReadinessConvergenceError,
        ScopeBoundReadinessConvergencePersistenceError,
        PersistScopeBoundReadinessConvergenceError,
    ):
        raise
    except ValueError as exc:
        raise PersistScopeBoundReadinessConvergenceError(str(exc)) from exc
