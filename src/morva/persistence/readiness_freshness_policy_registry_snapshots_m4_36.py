from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.runtime.readiness_freshness_policy_registry_snapshot_m4_36 import (
    FreshnessPolicyRegistrySnapshot,
    FreshnessPolicyRegistrySnapshotError,
    build_freshness_policy_registry_snapshot,
)

from .models import Base
from .readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRepository,
)


class FreshnessPolicyRegistrySnapshotPersistenceError(ValueError):
    """Raised when a historical registry snapshot cannot be persisted safely."""


class FreshnessPolicyRegistrySnapshotRecord(Base):
    """Append-only historical anchor for an exact freshness-policy registry membership."""

    __tablename__ = "readiness_freshness_policy_registry_snapshots"
    __table_args__ = (
        Index(
            "ix_readiness_freshness_registry_snapshot_fingerprint",
            "fingerprint",
            unique=True,
        ),
        Index(
            "ix_readiness_freshness_registry_snapshot_registry_fingerprint",
            "registry_fingerprint",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_version: Mapped[int] = mapped_column(nullable=False)
    integrity_version: Mapped[int] = mapped_column(nullable=False)
    policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    member_record_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    membership_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    captured_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_snapshot(self) -> FreshnessPolicyRegistrySnapshot:
        try:
            member_ids = tuple(UUID(value) for value in self.member_record_ids)
            return FreshnessPolicyRegistrySnapshot(
                snapshot_version=self.snapshot_version,
                integrity_version=self.integrity_version,
                policy_count=self.policy_count,
                registry_fingerprint=self.registry_fingerprint,
                member_record_ids=member_ids,
                membership_fingerprint=self.membership_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (TypeError, ValueError, FreshnessPolicyRegistrySnapshotError) as exc:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "persisted registry snapshot is structurally invalid"
            ) from exc


class FreshnessPolicyRegistrySnapshotRepository:
    """Append-only persistence and independent reconstruction boundary for M4.36."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository,
        *,
        captured_by: str,
    ) -> FreshnessPolicyRegistrySnapshotRecord:
        actor = captured_by.strip()
        if not actor:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "captured_by is required"
            )

        try:
            policy_count, registry_fingerprint, member_record_ids = (
                policy_repository.integrity_snapshot_manifest()
            )
            snapshot = build_freshness_policy_registry_snapshot(
                integrity_version=1,
                policy_count=policy_count,
                registry_fingerprint=registry_fingerprint,
                member_record_ids=member_record_ids,
            )
        except (
            ReadinessConvergenceFreshnessPolicyPersistenceError,
            FreshnessPolicyRegistrySnapshotError,
        ) as exc:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(str(exc)) from exc

        existing = self.session.scalar(
            select(FreshnessPolicyRegistrySnapshotRecord).where(
                FreshnessPolicyRegistrySnapshotRecord.fingerprint
                == snapshot.fingerprint.lower()
            )
        )
        if existing is not None:
            _normalize_loaded_record(self.session, existing)
            existing.to_snapshot()
            return existing

        record = FreshnessPolicyRegistrySnapshotRecord(
            snapshot_version=snapshot.snapshot_version,
            integrity_version=snapshot.integrity_version,
            policy_count=snapshot.policy_count,
            registry_fingerprint=snapshot.registry_fingerprint.lower(),
            member_record_ids=[str(value) for value in snapshot.member_record_ids],
            membership_fingerprint=snapshot.membership_fingerprint.lower(),
            fingerprint=snapshot.fingerprint.lower(),
            captured_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        _normalize_loaded_record(self.session, record)
        record.to_snapshot()
        return record

    def get(
        self,
        snapshot_id: UUID,
    ) -> FreshnessPolicyRegistrySnapshotRecord | None:
        record = self.session.get(FreshnessPolicyRegistrySnapshotRecord, snapshot_id)
        if record is None:
            return None
        _normalize_loaded_record(self.session, record)
        record.to_snapshot()
        return record

    def resolve_policy(
        self,
        snapshot_id: UUID,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository,
        *,
        policy_id: str,
        policy_version: int = 1,
    ):
        record = self.reconstruct(snapshot_id, policy_repository)
        snapshot = record.to_snapshot()
        policy_record = policy_repository.get(
            policy_id=policy_id,
            policy_version=policy_version,
        )
        if policy_record is None:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "historical snapshot policy not found"
            )
        if policy_record.id not in snapshot.member_record_ids:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "policy is not a member of the historical registry snapshot"
            )
        try:
            policy_record.to_policy()
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                f"historical snapshot policy reconstruction failed: {exc}"
            ) from exc
        return policy_record

    def reconstruct(
        self,
        snapshot_id: UUID,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository,
    ) -> FreshnessPolicyRegistrySnapshotRecord:
        record = self.get(snapshot_id)
        if record is None:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "registry snapshot not found"
            )
        snapshot = record.to_snapshot()
        try:
            count, fingerprint = policy_repository.integrity_snapshot_for_record_ids(
                snapshot.member_record_ids
            )
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                f"registry snapshot reconstruction failed: {exc}"
            ) from exc
        if count != snapshot.policy_count:
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "registry snapshot policy count changed"
            )
        if fingerprint.lower() != snapshot.registry_fingerprint.lower():
            raise FreshnessPolicyRegistrySnapshotPersistenceError(
                "registry snapshot registry fingerprint changed"
            )
        return record


def _normalize_loaded_record(
    session: Session,
    record: FreshnessPolicyRegistrySnapshotRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        value = record.created_at
        if value.tzinfo is None:
            record.created_at = value.replace(tzinfo=timezone.utc)
