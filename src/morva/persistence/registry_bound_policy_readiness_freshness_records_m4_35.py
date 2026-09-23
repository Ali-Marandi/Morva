from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshness,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicy,
)
from morva.runtime.registry_bound_policy_readiness_freshness_m4_34 import (
    RegistryBoundPolicyReadinessFreshness,
    RegistryBoundPolicyReadinessFreshnessError,
)
from .models import Base


class RegistryBoundPolicyReadinessFreshnessPersistenceError(ValueError):
    """Raised when a registry-bound freshness receipt cannot be persisted safely."""


class RegistryBoundPolicyReadinessFreshnessRecord(Base):
    """Append-only persisted receipt for an M4.34 registry-bound freshness evaluation."""

    __tablename__ = "registry_bound_policy_readiness_freshness_receipts"
    __table_args__ = (
        Index(
            "ix_registry_bound_freshness_receipt_scope_created_at",
            "organization_scope",
            "organization_scope_id",
            "created_at",
        ),
        Index(
            "ix_registry_bound_freshness_receipt_binding_fp",
            "binding_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    repository: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    candidate_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    organization_scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    organization_scope_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    registry_integrity_version: Mapped[int] = mapped_column(nullable=False)
    registry_policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    convergence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    max_age_seconds: Mapped[int] = mapped_column(nullable=False)
    age_seconds: Mapped[int] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    blockers: Mapped[list] = mapped_column(JSON, nullable=False)
    freshness_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    binding_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_freshness(self) -> RegistryBoundPolicyReadinessFreshness:
        try:
            policy = ReadinessConvergenceFreshnessPolicy(
                policy_version=self.policy_version,
                policy_id=self.policy_id,
                max_age_seconds=self.max_age_seconds,
                fingerprint=self.policy_fingerprint,
            )
            assessment = ReadinessConvergenceFreshnessAssessment(
                freshness_version=1,
                convergence_fingerprint=self.convergence_fingerprint,
                checked_at=_ensure_timezone(self.checked_at, "checked_at"),
                observed_at=_ensure_timezone(self.observed_at, "observed_at"),
                max_age_seconds=self.max_age_seconds,
                age_seconds=self.age_seconds,
                state=self.state,
                blockers=tuple(self.blockers),
                fingerprint=self.freshness_fingerprint,
            )
            policy_bound = PolicyBoundReadinessFreshness(
                binding_version=1,
                policy=policy,
                assessment=assessment,
            )
            return RegistryBoundPolicyReadinessFreshness(
                binding_version=1,
                registry_integrity_version=self.registry_integrity_version,
                registry_policy_count=self.registry_policy_count,
                registry_fingerprint=self.registry_fingerprint,
                policy_bound=policy_bound,
                fingerprint=self.binding_fingerprint,
            )
        except (TypeError, ValueError, RegistryBoundPolicyReadinessFreshnessError) as exc:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "persisted registry-bound freshness receipt is structurally invalid"
            ) from exc


class RegistryBoundPolicyReadinessFreshnessRepository:
    """Append-only repository for registry-bound freshness evaluation receipts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        repository: str,
        candidate_sha: str,
        target_environment: str,
        organization_scope: str,
        organization_scope_id: str,
        freshness: RegistryBoundPolicyReadinessFreshness,
        recorded_by: str,
    ) -> RegistryBoundPolicyReadinessFreshnessRecord:
        actor = recorded_by.strip()
        if not actor:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "recorded_by is required"
            )
        candidate_sha = candidate_sha.strip().lower()
        organization_scope = organization_scope.strip().lower()
        organization_scope_id = organization_scope_id.strip()
        if len(candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in candidate_sha
        ):
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "candidate_sha must be canonical SHA-1"
            )
        if not organization_scope or not organization_scope_id:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "organization scope and scope id are required"
            )

        try:
            normalized = RegistryBoundPolicyReadinessFreshness(
                binding_version=freshness.binding_version,
                registry_integrity_version=freshness.registry_integrity_version,
                registry_policy_count=freshness.registry_policy_count,
                registry_fingerprint=freshness.registry_fingerprint,
                policy_bound=freshness.policy_bound,
                fingerprint=freshness.fingerprint,
            )
        except RegistryBoundPolicyReadinessFreshnessError as exc:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                str(exc)
            ) from exc

        existing = self.session.scalar(
            select(RegistryBoundPolicyReadinessFreshnessRecord).where(
                RegistryBoundPolicyReadinessFreshnessRecord.binding_fingerprint
                == normalized.fingerprint.lower()
            )
        )
        if existing is not None:
            _normalize_loaded_record(self.session, existing)
            existing.to_freshness()
            if existing.recorded_by != actor:
                raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                    "binding fingerprint is already recorded by a different actor"
                )
            return existing

        assessment = normalized.policy_bound.assessment
        policy = normalized.policy_bound.policy
        record = RegistryBoundPolicyReadinessFreshnessRecord(
            repository=repository.strip(),
            candidate_sha=candidate_sha,
            target_environment=target_environment,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint.lower(),
            registry_integrity_version=normalized.registry_integrity_version,
            registry_policy_count=normalized.registry_policy_count,
            registry_fingerprint=normalized.registry_fingerprint.lower(),
            convergence_fingerprint=assessment.convergence_fingerprint.lower(),
            checked_at=_ensure_timezone(assessment.checked_at, "checked_at"),
            observed_at=_ensure_timezone(assessment.observed_at, "observed_at"),
            max_age_seconds=assessment.max_age_seconds,
            age_seconds=assessment.age_seconds,
            state=assessment.state,
            blockers=list(assessment.blockers),
            freshness_fingerprint=assessment.fingerprint.lower(),
            binding_fingerprint=normalized.fingerprint.lower(),
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        _normalize_loaded_record(self.session, record)
        record.to_freshness()
        return record

    def list(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[list[RegistryBoundPolicyReadinessFreshnessRecord], bool]:
        if limit < 1 or limit > 100:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "limit must be between 1 and 100"
            )
        if (organization_scope is None) != (organization_scope_id is None):
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "organization_scope and organization_scope_id must be supplied together"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(RegistryBoundPolicyReadinessFreshnessRecord).where(
            RegistryBoundPolicyReadinessFreshnessRecord.repository == repository
        )
        if candidate_sha is not None:
            query = query.where(
                RegistryBoundPolicyReadinessFreshnessRecord.candidate_sha
                == candidate_sha.strip().lower()
            )
        if target_environment is not None:
            query = query.where(
                RegistryBoundPolicyReadinessFreshnessRecord.target_environment
                == target_environment
            )
        if organization_scope is not None and organization_scope_id is not None:
            query = query.where(
                RegistryBoundPolicyReadinessFreshnessRecord.organization_scope
                == organization_scope.strip().lower(),
                RegistryBoundPolicyReadinessFreshnessRecord.organization_scope_id
                == organization_scope_id.strip(),
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                RegistryBoundPolicyReadinessFreshnessRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    RegistryBoundPolicyReadinessFreshnessRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        RegistryBoundPolicyReadinessFreshnessRecord.created_at
                        == before_created_at
                    )
                    & (
                        RegistryBoundPolicyReadinessFreshnessRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    RegistryBoundPolicyReadinessFreshnessRecord.created_at.desc(),
                    RegistryBoundPolicyReadinessFreshnessRecord.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            _normalize_loaded_record(self.session, record)
            record.to_freshness()
        return records, has_more


def _normalize_loaded_record(
    session: Session,
    record: RegistryBoundPolicyReadinessFreshnessRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        for field_name in ("checked_at", "observed_at", "created_at"):
            value = getattr(record, field_name)
            if value.tzinfo is None:
                setattr(record, field_name, value.replace(tzinfo=timezone.utc))


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise RegistryBoundPolicyReadinessFreshnessPersistenceError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)
