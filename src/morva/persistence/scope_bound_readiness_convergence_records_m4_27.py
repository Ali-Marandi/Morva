from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.readiness_scope_binding_m4_25 import (
    ReadinessScopeBindingError,
    normalize_readiness_scope,
)
from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergence,
    ScopeBoundReadinessConvergenceError,
)

from .models import Base


class ScopeBoundReadinessConvergencePersistenceError(ValueError):
    """Raised when an M4.26 convergence receipt cannot be persisted safely."""


class ScopeBoundReadinessConvergenceRecord(Base):
    """Append-only persisted M4.26 scope-bound convergence receipt."""

    __tablename__ = "scope_bound_readiness_convergences"
    __table_args__ = (
        UniqueConstraint(
            "fingerprint",
            name="uq_scope_bound_readiness_convergence_fingerprint",
        ),
        Index(
            "ix_scope_bound_readiness_convergence_scope_binding",
            "organization_scope",
            "organization_scope_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    convergence_version: Mapped[int] = mapped_column()
    repository: Mapped[str] = mapped_column(String(200), index=True)
    candidate_sha: Mapped[str] = mapped_column(String(40), index=True)
    target_environment: Mapped[str] = mapped_column(String(20), index=True)
    organization_scope: Mapped[str] = mapped_column(String(20), index=True)
    organization_scope_id: Mapped[str] = mapped_column(String(100), index=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    persisted_verification_fingerprint: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    persisted_evidence_readiness_fingerprint: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    current_evidence_readiness_fingerprint: Mapped[str] = mapped_column(
        String(64),
        index=True,
    )
    state: Mapped[str] = mapped_column(String(20), index=True)
    blockers: Mapped[list] = mapped_column(JSON, default=list)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_convergence(self) -> ScopeBoundReadinessConvergence:
        try:
            checked_at = _ensure_timezone(self.checked_at, "checked_at")
            normalize_readiness_scope(
                self.organization_scope,
                self.organization_scope_id,
            )
            convergence = ScopeBoundReadinessConvergence(
                convergence_version=self.convergence_version,
                repository=self.repository,
                candidate_sha=self.candidate_sha,
                target_environment=self.target_environment,
                organization_scope=self.organization_scope,
                organization_scope_id=self.organization_scope_id,
                checked_at=checked_at,
                persisted_verification_fingerprint=(
                    self.persisted_verification_fingerprint
                ),
                persisted_evidence_readiness_fingerprint=(
                    self.persisted_evidence_readiness_fingerprint
                ),
                current_evidence_readiness_fingerprint=(
                    self.current_evidence_readiness_fingerprint
                ),
                state=self.state,
                blockers=tuple(self.blockers),
                fingerprint=self.fingerprint,
            )
            return convergence
        except ScopeBoundReadinessConvergencePersistenceError:
            raise
        except (TypeError, ValueError, ScopeBoundReadinessError) as exc:
            raise ScopeBoundReadinessConvergencePersistenceError(
                "persisted scope-bound readiness convergence is structurally invalid"
            ) from exc


class ScopeBoundReadinessConvergenceRepository:
    """Append-only persistence boundary for M4.26 convergence receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        convergence: ScopeBoundReadinessConvergence,
    ) -> ScopeBoundReadinessConvergenceRecord:
        if convergence.repository != "Ali-Marandi/Morva":
            raise ScopeBoundReadinessConvergencePersistenceError(
                "convergence persistence requires the canonical repository"
            )
        try:
            scope, scope_id = normalize_readiness_scope(
                convergence.organization_scope,
                convergence.organization_scope_id,
            )
            checked_at = _ensure_timezone(convergence.checked_at, "checked_at")
            fingerprint = convergence.fingerprint.lower()
        except (ReadinessScopeBindingError, ValueError) as exc:
            raise ScopeBoundReadinessConvergencePersistenceError(str(exc)) from exc

        existing = self.session.scalar(
            select(ScopeBoundReadinessConvergenceRecord).where(
                ScopeBoundReadinessConvergenceRecord.fingerprint == fingerprint
            )
        )
        if existing is not None:
            self._normalize_loaded_record(existing)
            try:
                existing_convergence = existing.to_convergence()
                if (
                    existing_convergence.organization_scope != scope
                    or existing_convergence.organization_scope_id != scope_id
                ):
                    raise ScopeBoundReadinessConvergencePersistenceError(
                        "convergence is already bound to a different organization scope"
                    )
            except ScopeBoundReadinessConvergencePersistenceError:
                raise
            return existing

        record = ScopeBoundReadinessConvergenceRecord(
            convergence_version=convergence.convergence_version,
            repository=convergence.repository,
            candidate_sha=convergence.candidate_sha.lower(),
            target_environment=convergence.target_environment,
            organization_scope=scope,
            organization_scope_id=scope_id,
            checked_at=checked_at,
            persisted_verification_fingerprint=(
                convergence.persisted_verification_fingerprint.lower()
            ),
            persisted_evidence_readiness_fingerprint=(
                convergence.persisted_evidence_readiness_fingerprint.lower()
            ),
            current_evidence_readiness_fingerprint=(
                convergence.current_evidence_readiness_fingerprint.lower()
            ),
            state=convergence.state,
            blockers=list(convergence.blockers),
            fingerprint=fingerprint,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def latest(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
    ) -> ScopeBoundReadinessConvergenceRecord | None:
        if (organization_scope is None) != (organization_scope_id is None):
            raise ScopeBoundReadinessConvergencePersistenceError(
                "organization_scope and organization_scope_id must be supplied together"
            )
        if organization_scope is not None and organization_scope_id is not None:
            try:
                organization_scope, organization_scope_id = normalize_readiness_scope(
                    organization_scope,
                    organization_scope_id,
                )
            except ReadinessScopeBindingError as exc:
                raise ScopeBoundReadinessConvergencePersistenceError(
                    str(exc)
                ) from exc

        query = select(ScopeBoundReadinessConvergenceRecord).where(
            ScopeBoundReadinessConvergenceRecord.repository == repository
        )
        if candidate_sha is not None:
            query = query.where(
                ScopeBoundReadinessConvergenceRecord.candidate_sha
                == candidate_sha.lower()
            )
        if target_environment is not None:
            query = query.where(
                ScopeBoundReadinessConvergenceRecord.target_environment
                == target_environment
            )
        if organization_scope is not None and organization_scope_id is not None:
            query = query.where(
                ScopeBoundReadinessConvergenceRecord.organization_scope
                == organization_scope,
                ScopeBoundReadinessConvergenceRecord.organization_scope_id
                == organization_scope_id,
            )

        record = self.session.scalar(
            query.order_by(
                ScopeBoundReadinessConvergenceRecord.checked_at.desc(),
                ScopeBoundReadinessConvergenceRecord.id.desc(),
            ).limit(1)
        )
        if record is not None:
            self._normalize_loaded_record(record)
            record.to_convergence()
        return record

    def _normalize_loaded_record(
        self,
        record: ScopeBoundReadinessConvergenceRecord,
    ) -> ScopeBoundReadinessConvergenceRecord:
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "sqlite":
            for field_name in ("checked_at", "created_at"):
                value = getattr(record, field_name)
                if value is not None and value.tzinfo is None:
                    setattr(record, field_name, value.replace(tzinfo=timezone.utc))
        return record


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ScopeBoundReadinessConvergencePersistenceError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)
