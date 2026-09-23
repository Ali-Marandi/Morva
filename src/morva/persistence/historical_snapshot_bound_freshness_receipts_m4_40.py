from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotPersistenceError,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    HistoricalSnapshotBoundPolicyReadinessFreshness,
    HistoricalSnapshotBoundPolicyReadinessFreshnessError,
    build_historical_snapshot_bound_policy_readiness_freshness,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    PolicyBoundReadinessFreshness,
    PolicyBoundReadinessFreshnessError,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
    ReadinessConvergenceFreshnessError,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    ReadinessConvergenceFreshnessPolicy,
)
from .models import Base


class HistoricalSnapshotBoundFreshnessReceiptPersistenceError(ValueError):
    """Raised when a historical snapshot-bound freshness receipt is unsafe."""


class HistoricalSnapshotBoundPolicyReadinessFreshnessRecord(Base):
    """Append-only M4.40 receipt for an M4.39 historical evaluation."""

    __tablename__ = "historical_snapshot_bound_policy_readiness_freshness_receipts"
    __table_args__ = (
        Index(
            "ix_historical_snapshot_freshness_receipt_scope_created_at",
            "organization_scope",
            "organization_scope_id",
            "created_at",
        ),
        Index(
            "ix_historical_snapshot_freshness_receipt_binding_fp",
            "binding_fingerprint",
            unique=True,
        ),
        Index(
            "ix_historical_snapshot_freshness_receipt_snapshot_id",
            "snapshot_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    repository: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    candidate_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_environment: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    organization_scope: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    organization_scope_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("readiness_freshness_policy_registry_snapshots.id"),
        nullable=False,
    )
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    registry_integrity_version: Mapped[int] = mapped_column(nullable=False)
    registry_policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
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

    def to_freshness(self) -> HistoricalSnapshotBoundPolicyReadinessFreshness:
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
            return HistoricalSnapshotBoundPolicyReadinessFreshness(
                binding_version=1,
                snapshot_id=self.snapshot_id,
                snapshot_fingerprint=self.snapshot_fingerprint,
                registry_integrity_version=self.registry_integrity_version,
                registry_policy_count=self.registry_policy_count,
                registry_fingerprint=self.registry_fingerprint,
                policy_bound=policy_bound,
                fingerprint=self.binding_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            ReadinessConvergenceFreshnessError,
            PolicyBoundReadinessFreshnessError,
            HistoricalSnapshotBoundPolicyReadinessFreshnessError,
        ) as exc:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "persisted historical snapshot-bound freshness receipt is structurally invalid"
            ) from exc


class HistoricalSnapshotBoundFreshnessReceiptRepository:
    """Append-only M4.40 receipt persistence and independent verification."""

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
        freshness: HistoricalSnapshotBoundPolicyReadinessFreshness,
        recorded_by: str,
    ) -> HistoricalSnapshotBoundPolicyReadinessFreshnessRecord:
        actor = recorded_by.strip()
        if not actor:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "recorded_by is required"
            )
        candidate_sha = candidate_sha.strip().lower()
        organization_scope = organization_scope.strip().lower()
        organization_scope_id = organization_scope_id.strip()
        if len(candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in candidate_sha
        ):
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "candidate_sha must be canonical SHA-1"
            )
        if not organization_scope or not organization_scope_id:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "organization scope and scope id are required"
            )

        try:
            normalized = HistoricalSnapshotBoundPolicyReadinessFreshness(
                binding_version=freshness.binding_version,
                snapshot_id=freshness.snapshot_id,
                snapshot_fingerprint=freshness.snapshot_fingerprint,
                registry_integrity_version=freshness.registry_integrity_version,
                registry_policy_count=freshness.registry_policy_count,
                registry_fingerprint=freshness.registry_fingerprint,
                policy_bound=freshness.policy_bound,
                fingerprint=freshness.fingerprint,
            )
        except HistoricalSnapshotBoundPolicyReadinessFreshnessError as exc:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                str(exc)
            ) from exc

        existing = self.session.scalar(
            select(HistoricalSnapshotBoundPolicyReadinessFreshnessRecord).where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.binding_fingerprint
                == normalized.fingerprint.lower()
            )
        )
        if existing is not None:
            _normalize_loaded_record(self.session, existing)
            existing.to_freshness()
            if existing.recorded_by != actor:
                raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                    "binding fingerprint is already recorded by a different actor"
                )
            return existing

        assessment = normalized.policy_bound.assessment
        policy = normalized.policy_bound.policy
        record = HistoricalSnapshotBoundPolicyReadinessFreshnessRecord(
            repository=repository.strip(),
            candidate_sha=candidate_sha,
            target_environment=target_environment,
            organization_scope=organization_scope,
            organization_scope_id=organization_scope_id,
            snapshot_id=normalized.snapshot_id,
            snapshot_fingerprint=normalized.snapshot_fingerprint.lower(),
            registry_integrity_version=normalized.registry_integrity_version,
            registry_policy_count=normalized.registry_policy_count,
            registry_fingerprint=normalized.registry_fingerprint.lower(),
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint.lower(),
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

    def verify(
        self,
        receipt_id: UUID,
        *,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository | None = None,
        snapshot_repository: FreshnessPolicyRegistrySnapshotRepository | None = None,
    ) -> HistoricalSnapshotBoundPolicyReadinessFreshnessRecord:
        record = self.session.get(
            HistoricalSnapshotBoundPolicyReadinessFreshnessRecord,
            receipt_id,
        )
        if record is None:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "historical snapshot-bound freshness receipt not found"
            )
        _normalize_loaded_record(self.session, record)
        stored = record.to_freshness()

        policy_repository = policy_repository or ReadinessConvergenceFreshnessPolicyRepository(
            self.session
        )
        snapshot_repository = snapshot_repository or FreshnessPolicyRegistrySnapshotRepository(
            self.session
        )
        try:
            snapshot_record = snapshot_repository.reconstruct(
                record.snapshot_id,
                policy_repository,
            )
            snapshot = snapshot_record.to_snapshot()
            policy_record = snapshot_repository.resolve_policy(
                record.snapshot_id,
                policy_repository,
                policy_id=record.policy_id,
                policy_version=record.policy_version,
            )
            policy = policy_record.to_policy()
        except (
            FreshnessPolicyRegistrySnapshotPersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
        ) as exc:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                str(exc)
            ) from exc

        if snapshot.fingerprint != record.snapshot_fingerprint:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt snapshot fingerprint differs from reconstructed snapshot"
            )
        if snapshot.integrity_version != record.registry_integrity_version:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt registry integrity version differs from snapshot"
            )
        if snapshot.policy_count != record.registry_policy_count:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt registry policy count differs from snapshot"
            )
        if snapshot.registry_fingerprint != record.registry_fingerprint:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt registry fingerprint differs from snapshot"
            )
        if policy.fingerprint != record.policy_fingerprint:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt policy fingerprint differs from persisted policy"
            )

        rebuilt = build_historical_snapshot_bound_policy_readiness_freshness(
            stored.policy_bound,
            snapshot_id=snapshot_record.id,
            snapshot_fingerprint=snapshot.fingerprint,
            registry_integrity_version=snapshot.integrity_version,
            registry_policy_count=snapshot.policy_count,
            registry_fingerprint=snapshot.registry_fingerprint,
        )
        if rebuilt.fingerprint != record.binding_fingerprint:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "receipt fingerprint differs from reconstructed evaluation"
            )
        return record

    def list(
        self,
        *,
        repository: str = "Ali-Marandi/Morva",
        candidate_sha: str | None = None,
        target_environment: str | None = None,
        organization_scope: str | None = None,
        organization_scope_id: str | None = None,
        snapshot_id: UUID | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[list[HistoricalSnapshotBoundPolicyReadinessFreshnessRecord], bool]:
        if limit < 1 or limit > 100:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if (organization_scope is None) != (organization_scope_id is None):
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "organization_scope and organization_scope_id must be supplied together"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalSnapshotBoundFreshnessReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(HistoricalSnapshotBoundPolicyReadinessFreshnessRecord).where(
            HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.repository == repository
        )
        if candidate_sha is not None:
            query = query.where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.candidate_sha
                == candidate_sha.strip().lower()
            )
        if target_environment is not None:
            query = query.where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.target_environment
                == target_environment
            )
        if organization_scope is not None and organization_scope_id is not None:
            query = query.where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.organization_scope
                == organization_scope.strip().lower(),
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.organization_scope_id
                == organization_scope_id.strip(),
            )
        if snapshot_id is not None:
            query = query.where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.snapshot_id
                == snapshot_id
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.created_at.desc(),
                    HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.id.desc(),
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
    record: HistoricalSnapshotBoundPolicyReadinessFreshnessRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        for field_name in ("checked_at", "observed_at", "created_at"):
            value = getattr(record, field_name)
            if value.tzinfo is None:
                setattr(record, field_name, value.replace(tzinfo=timezone.utc))


def _ensure_timezone(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
