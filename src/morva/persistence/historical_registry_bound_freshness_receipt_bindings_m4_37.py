from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotPersistenceError,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.persistence.registry_bound_policy_readiness_freshness_records_m4_35 import (
    RegistryBoundPolicyReadinessFreshnessPersistenceError,
    RegistryBoundPolicyReadinessFreshnessRecord,
)
from morva.runtime.historical_registry_bound_freshness_receipt_m4_37 import (
    HistoricalRegistryBoundFreshnessReceipt,
    HistoricalRegistryBoundFreshnessReceiptError,
    build_historical_registry_bound_freshness_receipt,
)

from .models import Base


class HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(ValueError):
    """Raised when an M4.35 receipt cannot be bound safely to M4.36."""


class HistoricalRegistryBoundFreshnessReceiptBindingRecord(Base):
    """Append-only link between an M4.35 receipt and exact M4.36 snapshot."""

    __tablename__ = "historical_registry_bound_freshness_receipt_bindings"
    __table_args__ = (
        Index(
            "ix_historical_receipt_binding_fingerprint",
            "fingerprint",
            unique=True,
        ),
        Index(
            "ix_historical_receipt_binding_receipt_id",
            "receipt_id",
            unique=True,
        ),
        Index(
            "ix_historical_receipt_binding_snapshot_id",
            "snapshot_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("registry_bound_policy_readiness_freshness_receipts.id"),
        nullable=False,
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("readiness_freshness_policy_registry_snapshots.id"),
        nullable=False,
    )
    receipt_binding_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    snapshot_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    registry_integrity_version: Mapped[int] = mapped_column(nullable=False)
    registry_policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bound_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_binding(self) -> HistoricalRegistryBoundFreshnessReceipt:
        try:
            return HistoricalRegistryBoundFreshnessReceipt(
                binding_version=1,
                receipt_id=self.receipt_id,
                snapshot_id=self.snapshot_id,
                receipt_binding_fingerprint=self.receipt_binding_fingerprint,
                snapshot_fingerprint=self.snapshot_fingerprint,
                registry_integrity_version=self.registry_integrity_version,
                registry_policy_count=self.registry_policy_count,
                registry_fingerprint=self.registry_fingerprint,
                policy_id=self.policy_id,
                policy_version=self.policy_version,
                policy_fingerprint=self.policy_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (TypeError, ValueError, HistoricalRegistryBoundFreshnessReceiptError) as exc:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "persisted historical receipt binding is structurally invalid"
            ) from exc


class HistoricalRegistryBoundFreshnessReceiptBindingRepository:
    """Append-only M4.37 binding and independent re-verification boundary."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def bind(
        self,
        *,
        receipt_id: UUID,
        snapshot_id: UUID,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository | None = None,
        snapshot_repository: FreshnessPolicyRegistrySnapshotRepository | None = None,
        bound_by: str,
    ) -> HistoricalRegistryBoundFreshnessReceiptBindingRecord:
        actor = bound_by.strip()
        if not actor:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound_by is required"
            )

        receipt_record = self.session.get(
            RegistryBoundPolicyReadinessFreshnessRecord, receipt_id
        )
        if receipt_record is None:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "registry-bound freshness receipt not found"
            )
        try:
            receipt = receipt_record.to_freshness()
        except RegistryBoundPolicyReadinessFreshnessPersistenceError as exc:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                f"receipt reconstruction failed: {exc}"
            ) from exc

        policy_repository = policy_repository or ReadinessConvergenceFreshnessPolicyRepository(
            self.session
        )
        snapshot_repository = snapshot_repository or FreshnessPolicyRegistrySnapshotRepository(
            self.session
        )
        try:
            snapshot_record = snapshot_repository.reconstruct(snapshot_id, policy_repository)
            snapshot = snapshot_record.to_snapshot()
            policy_record = policy_repository.get(
                policy_id=receipt.policy_bound.policy.policy_id,
                policy_version=receipt.policy_bound.policy.policy_version,
            )
        except (
            FreshnessPolicyRegistrySnapshotPersistenceError,
            ReadinessConvergenceFreshnessPolicyPersistenceError,
        ) as exc:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                str(exc)
            ) from exc
        if policy_record is None:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt policy is missing from the current registry"
            )
        try:
            policy = policy_record.to_policy()
        except ReadinessConvergenceFreshnessPolicyPersistenceError as exc:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                f"receipt policy reconstruction failed: {exc}"
            ) from exc
        if policy.fingerprint != receipt.policy_bound.policy.fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt policy fingerprint differs from the persisted policy"
            )
        if policy_record.id not in snapshot.member_record_ids:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt policy is not a member of the historical registry snapshot"
            )
        if receipt.registry_integrity_version != snapshot.integrity_version:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt registry integrity version differs from snapshot"
            )
        if receipt.registry_policy_count != snapshot.policy_count:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt registry policy count differs from snapshot"
            )
        if receipt.registry_fingerprint != snapshot.registry_fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt registry fingerprint differs from snapshot"
            )

        binding = build_historical_registry_bound_freshness_receipt(
            receipt_id=receipt_record.id,
            snapshot_id=snapshot_record.id,
            receipt_binding_fingerprint=receipt.fingerprint,
            snapshot_fingerprint=snapshot.fingerprint,
            registry_integrity_version=snapshot.integrity_version,
            registry_policy_count=snapshot.policy_count,
            registry_fingerprint=snapshot.registry_fingerprint,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint,
        )

        existing = self.session.scalar(
            select(HistoricalRegistryBoundFreshnessReceiptBindingRecord).where(
                HistoricalRegistryBoundFreshnessReceiptBindingRecord.receipt_id
                == receipt_record.id
            )
        )
        if existing is not None:
            _normalize_loaded_record(self.session, existing)
            existing.to_binding()
            if existing.fingerprint != binding.fingerprint:
                raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                    "receipt is already bound to a different historical snapshot"
                )
            if existing.bound_by != actor:
                raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                    "receipt binding is already recorded by a different actor"
                )
            return existing

        existing_fingerprint = self.session.scalar(
            select(HistoricalRegistryBoundFreshnessReceiptBindingRecord).where(
                HistoricalRegistryBoundFreshnessReceiptBindingRecord.fingerprint
                == binding.fingerprint
            )
        )
        if existing_fingerprint is not None:
            _normalize_loaded_record(self.session, existing_fingerprint)
            existing_fingerprint.to_binding()
            if existing_fingerprint.bound_by != actor:
                raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                    "binding fingerprint is already recorded by a different actor"
                )
            return existing_fingerprint

        record = HistoricalRegistryBoundFreshnessReceiptBindingRecord(
            receipt_id=receipt_record.id,
            snapshot_id=snapshot_record.id,
            receipt_binding_fingerprint=receipt.fingerprint.lower(),
            snapshot_fingerprint=snapshot.fingerprint.lower(),
            registry_integrity_version=snapshot.integrity_version,
            registry_policy_count=snapshot.policy_count,
            registry_fingerprint=snapshot.registry_fingerprint.lower(),
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint.lower(),
            fingerprint=binding.fingerprint.lower(),
            bound_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        _normalize_loaded_record(self.session, record)
        record.to_binding()
        return record

    def verify(
        self,
        binding_id: UUID,
        *,
        policy_repository: ReadinessConvergenceFreshnessPolicyRepository | None = None,
        snapshot_repository: FreshnessPolicyRegistrySnapshotRepository | None = None,
    ) -> HistoricalRegistryBoundFreshnessReceiptBindingRecord:
        record = self.session.get(
            HistoricalRegistryBoundFreshnessReceiptBindingRecord, binding_id
        )
        if record is None:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "historical receipt binding not found"
            )
        _normalize_loaded_record(self.session, record)
        binding = record.to_binding()
        receipt_record = self.session.get(
            RegistryBoundPolicyReadinessFreshnessRecord, record.receipt_id
        )
        if receipt_record is None:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound receipt is missing"
            )
        receipt = receipt_record.to_freshness()
        if receipt.fingerprint != binding.receipt_binding_fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound receipt fingerprint changed"
            )
        policy_repository = policy_repository or ReadinessConvergenceFreshnessPolicyRepository(
            self.session
        )
        snapshot_repository = snapshot_repository or FreshnessPolicyRegistrySnapshotRepository(
            self.session
        )
        snapshot_record = snapshot_repository.reconstruct(
            record.snapshot_id,
            policy_repository,
        )
        snapshot = snapshot_record.to_snapshot()
        if snapshot.fingerprint != binding.snapshot_fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "historical registry snapshot fingerprint changed"
            )
        if receipt.registry_fingerprint != snapshot.registry_fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt and historical snapshot registry fingerprints differ"
            )
        if receipt.registry_policy_count != snapshot.policy_count:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "receipt and historical snapshot policy counts differ"
            )
        if binding.policy_id != receipt.policy_bound.policy.policy_id:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound policy id differs from receipt"
            )
        if binding.policy_version != receipt.policy_bound.policy.policy_version:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound policy version differs from receipt"
            )
        if binding.policy_fingerprint != receipt.policy_bound.policy.fingerprint:
            raise HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError(
                "bound policy fingerprint differs from receipt"
            )
        return record


def _normalize_loaded_record(
    session: Session,
    record: HistoricalRegistryBoundFreshnessReceiptBindingRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        value = record.created_at
        if value.tzinfo is None:
            record.created_at = value.replace(tzinfo=timezone.utc)
