from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergence,
    ScopeBoundReadinessConvergenceError,
)

from .models import Base


class ScopeBoundReadinessConvergencePersistenceError(ValueError):
    """Raised when an M4.26 convergence receipt cannot be persisted safely."""


class ScopeBoundReadinessConvergenceRecord(Base):
    """Append-only persisted receipt for an M4.26 scope-bound convergence observation."""

    __tablename__ = "scope_bound_readiness_convergences"
    __table_args__ = (
        Index(
            "ix_scope_bound_readiness_convergence_verification_fp",
            "persisted_verification_fingerprint",
        ),
        Index(
            "ix_scope_bound_readiness_convergence_scope_checked_at",
            "organization_scope",
            "organization_scope_id",
            "checked_at",
        ),
        Index(
            "ix_scope_bound_readiness_convergence_state",
            "state",
        ),
        Index(
            "ix_scope_bound_readiness_convergence_fingerprint",
            "convergence_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    repository: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    candidate_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    organization_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    organization_scope_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    persisted_verification_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    persisted_evidence_readiness_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    current_evidence_readiness_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    blockers: Mapped[list] = mapped_column(JSON, nullable=False)
    convergence_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    recorded_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_convergence(self) -> ScopeBoundReadinessConvergence:
        try:
            convergence = ScopeBoundReadinessConvergence(
                convergence_version=1,
                repository=self.repository,
                candidate_sha=self.candidate_sha,
                target_environment=self.target_environment,
                organization_scope=self.organization_scope,
                organization_scope_id=self.organization_scope_id,
                checked_at=_ensure_timezone(self.checked_at, "checked_at"),
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
                fingerprint=self.convergence_fingerprint,
            )
        except (TypeError, ValueError, ScopeBoundReadinessConvergenceError) as exc:
            raise ScopeBoundReadinessConvergencePersistenceError(
                "persisted scope-bound readiness convergence is structurally invalid"
            ) from exc
        return convergence


class ScopeBoundReadinessConvergenceRepository:
    """Append-only persistence boundary for M4.26 convergence receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        convergence: ScopeBoundReadinessConvergence,
        *,
        recorded_by: str,
    ) -> ScopeBoundReadinessConvergenceRecord:
        actor = recorded_by.strip()
        if not actor:
            raise ScopeBoundReadinessConvergencePersistenceError(
                "recorded_by is required"
            )

        try:
            convergence = ScopeBoundReadinessConvergence(
                convergence_version=convergence.convergence_version,
                repository=convergence.repository,
                candidate_sha=convergence.candidate_sha,
                target_environment=convergence.target_environment,
                organization_scope=convergence.organization_scope,
                organization_scope_id=convergence.organization_scope_id,
                checked_at=_ensure_timezone(convergence.checked_at, "checked_at"),
                persisted_verification_fingerprint=(
                    convergence.persisted_verification_fingerprint
                ),
                persisted_evidence_readiness_fingerprint=(
                    convergence.persisted_evidence_readiness_fingerprint
                ),
                current_evidence_readiness_fingerprint=(
                    convergence.current_evidence_readiness_fingerprint
                ),
                state=convergence.state,
                blockers=convergence.blockers,
                fingerprint=convergence.fingerprint,
            )
        except ScopeBoundReadinessConvergenceError as exc:
            raise ScopeBoundReadinessConvergencePersistenceError(
                str(exc)
            ) from exc

        existing = self.session.scalar(
            select(ScopeBoundReadinessConvergenceRecord).where(
                ScopeBoundReadinessConvergenceRecord.convergence_fingerprint
                == convergence.fingerprint.lower()
            )
        )
        if existing is not None:
            existing.to_convergence()
            if existing.recorded_by != actor:
                raise ScopeBoundReadinessConvergencePersistenceError(
                    "convergence fingerprint is already recorded by a different actor"
                )
            return existing

        record = ScopeBoundReadinessConvergenceRecord(
            repository=convergence.repository,
            candidate_sha=convergence.candidate_sha.lower(),
            target_environment=convergence.target_environment,
            organization_scope=convergence.organization_scope,
            organization_scope_id=convergence.organization_scope_id,
            checked_at=_ensure_timezone(convergence.checked_at, "checked_at"),
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
            convergence_fingerprint=convergence.fingerprint.lower(),
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_verified(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
        checked_before: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScopeBoundReadinessConvergenceRecord]:
        if limit < 1 or limit > 101:
            raise ScopeBoundReadinessConvergencePersistenceError(
                "convergence history query limit must be between 1 and 101"
            )
        if (organization_scope is None) != (organization_scope_id is None):
            raise ScopeBoundReadinessConvergencePersistenceError(
                "organization_scope and organization_scope_id must be supplied together"
            )
        if (checked_before is None) != (before_id is None):
            raise ScopeBoundReadinessConvergencePersistenceError(
                "checked_before and before_id must be supplied together"
            )
        if organization_scope is not None:
            organization_scope = organization_scope.strip().lower()
            organization_scope_id = organization_scope_id.strip()
            if not organization_scope or not organization_scope_id:
                raise ScopeBoundReadinessConvergencePersistenceError(
                    "organization scope and scope id are required"
                )
        if checked_before is not None:
            checked_before = _ensure_timezone(
                checked_before,
                "checked_before",
            )

        query = select(ScopeBoundReadinessConvergenceRecord).where(
            ScopeBoundReadinessConvergenceRecord.repository == repository
        )
        if candidate_sha is not None:
            query = query.where(
                ScopeBoundReadinessConvergenceRecord.candidate_sha
                == candidate_sha.strip().lower()
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
        if checked_before is not None and before_id is not None:
            query = query.where(
                (
                    ScopeBoundReadinessConvergenceRecord.checked_at
                    < checked_before
                )
                | (
                    (
                        ScopeBoundReadinessConvergenceRecord.checked_at
                        == checked_before
                    )
                    & (
                        ScopeBoundReadinessConvergenceRecord.id
                        < before_id
                    )
                )
            )

        records = self.session.scalars(
            query.order_by(
                ScopeBoundReadinessConvergenceRecord.checked_at.desc(),
                ScopeBoundReadinessConvergenceRecord.id.desc(),
            ).limit(limit)
        ).all()

        bind = self.session.get_bind()
        for record in records:
            if bind is not None and bind.dialect.name == "sqlite":
                for field_name in ("checked_at", "created_at"):
                    value = getattr(record, field_name)
                    if value.tzinfo is None:
                        setattr(
                            record,
                            field_name,
                            value.replace(tzinfo=timezone.utc),
                        )
            record.checked_at = _ensure_timezone(record.checked_at, "checked_at")
            record.created_at = _ensure_timezone(record.created_at, "created_at")
            record.to_convergence()

        return records


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise ScopeBoundReadinessConvergencePersistenceError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)
