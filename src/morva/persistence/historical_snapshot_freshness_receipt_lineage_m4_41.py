from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_registry_bound_freshness_receipt_bindings_m4_37 import (
    HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError,
    HistoricalRegistryBoundFreshnessReceiptBindingRecord,
    HistoricalRegistryBoundFreshnessReceiptBindingRepository,
)
from morva.persistence.historical_snapshot_bound_freshness_receipts_m4_40 import (
    HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
    HistoricalSnapshotBoundFreshnessReceiptRepository,
)
from morva.runtime.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineage,
    HistoricalSnapshotFreshnessReceiptLineageError,
    build_historical_snapshot_freshness_receipt_lineage,
)
from .models import Base


class HistoricalSnapshotFreshnessReceiptLineagePersistenceError(ValueError):
    """Raised when M4.40 cannot be linked safely to M4.37 lineage."""


class HistoricalSnapshotFreshnessReceiptLineageRecord(Base):
    """Append-only lineage binding between M4.40 and M4.37."""

    __tablename__ = "historical_snapshot_freshness_receipt_lineages_m4_41"
    __table_args__ = (
        Index(
            "ix_m4_41_lineage_fingerprint",
            "fingerprint",
            unique=True,
        ),
        Index(
            "ix_m4_41_lineage_freshness_receipt_id",
            "freshness_receipt_id",
            unique=True,
        ),
        Index(
            "ix_m4_41_lineage_historical_binding_id",
            "historical_binding_id",
        ),
        Index(
            "ix_m4_41_lineage_snapshot_id",
            "snapshot_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    freshness_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "historical_snapshot_bound_policy_readiness_freshness_receipts.id"
        ),
        nullable=False,
    )
    historical_binding_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_registry_bound_freshness_receipt_bindings.id"),
        nullable=False,
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("readiness_freshness_policy_registry_snapshots.id"),
        nullable=False,
    )
    freshness_receipt_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    historical_binding_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    snapshot_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    registry_integrity_version: Mapped[int] = mapped_column(nullable=False)
    registry_policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bound_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_lineage(self) -> HistoricalSnapshotFreshnessReceiptLineage:
        try:
            return HistoricalSnapshotFreshnessReceiptLineage(
                lineage_version=1,
                freshness_receipt_id=self.freshness_receipt_id,
                historical_binding_id=self.historical_binding_id,
                snapshot_id=self.snapshot_id,
                freshness_receipt_fingerprint=self.freshness_receipt_fingerprint,
                historical_binding_fingerprint=self.historical_binding_fingerprint,
                snapshot_fingerprint=self.snapshot_fingerprint,
                registry_integrity_version=self.registry_integrity_version,
                registry_policy_count=self.registry_policy_count,
                registry_fingerprint=self.registry_fingerprint,
                policy_id=self.policy_id,
                policy_version=self.policy_version,
                policy_fingerprint=self.policy_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (TypeError, ValueError, HistoricalSnapshotFreshnessReceiptLineageError) as exc:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "persisted historical freshness receipt lineage is structurally invalid"
            ) from exc


class HistoricalSnapshotFreshnessReceiptLineageRepository:
    """Append-only M4.41 lineage binding and independent verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def bind(
        self,
        *,
        freshness_receipt_id: UUID,
        historical_binding_id: UUID,
        bound_by: str,
    ) -> HistoricalSnapshotFreshnessReceiptLineageRecord:
        actor = bound_by.strip()
        if not actor:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "bound_by is required"
            )

        receipt_repository = HistoricalSnapshotBoundFreshnessReceiptRepository(self.session)
        try:
            receipt_record = receipt_repository.verify(freshness_receipt_id)
        except HistoricalSnapshotBoundFreshnessReceiptPersistenceError as exc:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                f"freshness receipt verification failed: {exc}"
            ) from exc

        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(
            self.session
        )
        try:
            binding_record = binding_repository.verify(historical_binding_id)
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                f"historical receipt binding verification failed: {exc}"
            ) from exc

        freshness = receipt_record.to_freshness()
        binding = binding_record.to_binding()

        if freshness.snapshot_id != binding.snapshot_id:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "freshness receipt snapshot differs from historical binding"
            )
        if freshness.snapshot_fingerprint != binding.snapshot_fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "freshness receipt snapshot fingerprint differs from historical binding"
            )
        policy = freshness.policy_bound.policy
        if binding.policy_id != policy.policy_id:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "historical binding policy id differs from freshness receipt"
            )
        if binding.policy_version != policy.policy_version:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "historical binding policy version differs from freshness receipt"
            )
        if binding.policy_fingerprint != policy.fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "historical binding policy fingerprint differs from freshness receipt"
            )
        if freshness.registry_integrity_version != binding.registry_integrity_version:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "freshness receipt registry integrity version differs from historical binding"
            )
        if freshness.registry_policy_count != binding.registry_policy_count:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "freshness receipt registry policy count differs from historical binding"
            )
        if freshness.registry_fingerprint != binding.registry_fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "freshness receipt registry fingerprint differs from historical binding"
            )

        lineage = build_historical_snapshot_freshness_receipt_lineage(
            freshness_receipt_id=receipt_record.id,
            historical_binding_id=binding_record.id,
            snapshot_id=freshness.snapshot_id,
            freshness_receipt_fingerprint=freshness.fingerprint,
            historical_binding_fingerprint=binding.fingerprint,
            snapshot_fingerprint=freshness.snapshot_fingerprint,
            registry_integrity_version=freshness.registry_integrity_version,
            registry_policy_count=freshness.registry_policy_count,
            registry_fingerprint=freshness.registry_fingerprint,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint,
        )

        existing = self.session.scalar(
            select(HistoricalSnapshotFreshnessReceiptLineageRecord).where(
                HistoricalSnapshotFreshnessReceiptLineageRecord.freshness_receipt_id
                == receipt_record.id
            )
        )
        if existing is not None:
            _normalize_loaded_record(self.session, existing)
            existing.to_lineage()
            if existing.fingerprint != lineage.fingerprint:
                raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                    "freshness receipt is already linked to different historical lineage"
                )
            if existing.bound_by != actor:
                raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                    "freshness receipt lineage is already recorded by a different actor"
                )
            return existing

        existing_fingerprint = self.session.scalar(
            select(HistoricalSnapshotFreshnessReceiptLineageRecord).where(
                HistoricalSnapshotFreshnessReceiptLineageRecord.fingerprint
                == lineage.fingerprint
            )
        )
        if existing_fingerprint is not None:
            _normalize_loaded_record(self.session, existing_fingerprint)
            existing_fingerprint.to_lineage()
            if existing_fingerprint.bound_by != actor:
                raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                    "lineage fingerprint is already recorded by a different actor"
                )
            return existing_fingerprint

        record = HistoricalSnapshotFreshnessReceiptLineageRecord(
            freshness_receipt_id=receipt_record.id,
            historical_binding_id=binding_record.id,
            snapshot_id=freshness.snapshot_id,
            freshness_receipt_fingerprint=freshness.fingerprint.lower(),
            historical_binding_fingerprint=binding.fingerprint.lower(),
            snapshot_fingerprint=freshness.snapshot_fingerprint.lower(),
            registry_integrity_version=freshness.registry_integrity_version,
            registry_policy_count=freshness.registry_policy_count,
            registry_fingerprint=freshness.registry_fingerprint.lower(),
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_fingerprint=policy.fingerprint.lower(),
            fingerprint=lineage.fingerprint.lower(),
            bound_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        _normalize_loaded_record(self.session, record)
        record.to_lineage()
        return record

    def verify(
        self,
        lineage_id: UUID,
    ) -> HistoricalSnapshotFreshnessReceiptLineageRecord:
        record = self.session.get(
            HistoricalSnapshotFreshnessReceiptLineageRecord,
            lineage_id,
        )
        if record is None:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "historical freshness receipt lineage not found"
            )
        _normalize_loaded_record(self.session, record)

        try:
            freshness_record = HistoricalSnapshotBoundFreshnessReceiptRepository(
                self.session
            ).verify(record.freshness_receipt_id)
        except HistoricalSnapshotBoundFreshnessReceiptPersistenceError as exc:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                f"freshness receipt verification failed: {exc}"
            ) from exc
        try:
            binding_record = HistoricalRegistryBoundFreshnessReceiptBindingRepository(
                self.session
            ).verify(record.historical_binding_id)
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                f"historical receipt binding verification failed: {exc}"
            ) from exc

        freshness = freshness_record.to_freshness()
        binding = binding_record.to_binding()
        if freshness.snapshot_id != record.snapshot_id or binding.snapshot_id != record.snapshot_id:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage snapshot identity differs from source records"
            )
        if freshness.snapshot_fingerprint != record.snapshot_fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage snapshot fingerprint differs from freshness receipt"
            )
        if binding.snapshot_fingerprint != record.snapshot_fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage snapshot fingerprint differs from historical binding"
            )
        policy = freshness.policy_bound.policy
        if (
            record.policy_id != policy.policy_id
            or record.policy_version != policy.policy_version
            or record.policy_fingerprint != policy.fingerprint
        ):
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage policy identity differs from freshness receipt"
            )
        if (
            record.registry_integrity_version != binding.registry_integrity_version
            or record.registry_policy_count != binding.registry_policy_count
            or record.registry_fingerprint != binding.registry_fingerprint
            or record.registry_integrity_version != freshness.registry_integrity_version
            or record.registry_policy_count != freshness.registry_policy_count
            or record.registry_fingerprint != freshness.registry_fingerprint
        ):
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage registry identity differs from source records"
            )
        lineage = build_historical_snapshot_freshness_receipt_lineage(
            freshness_receipt_id=freshness_record.id,
            historical_binding_id=binding_record.id,
            snapshot_id=record.snapshot_id,
            freshness_receipt_fingerprint=freshness.fingerprint,
            historical_binding_fingerprint=binding.fingerprint,
            snapshot_fingerprint=record.snapshot_fingerprint,
            registry_integrity_version=record.registry_integrity_version,
            registry_policy_count=record.registry_policy_count,
            registry_fingerprint=record.registry_fingerprint,
            policy_id=record.policy_id,
            policy_version=record.policy_version,
            policy_fingerprint=record.policy_fingerprint,
        )
        if lineage.fingerprint != record.fingerprint:
            raise HistoricalSnapshotFreshnessReceiptLineagePersistenceError(
                "lineage fingerprint differs from reconstructed lineage"
            )
        return record


def _normalize_loaded_record(
    session: Session,
    record: HistoricalSnapshotFreshnessReceiptLineageRecord,
) -> None:
    bind = session.get_bind()
    if bind is not None and bind.dialect.name == "sqlite":
        value = record.created_at
        if value.tzinfo is None:
            record.created_at = value.replace(tzinfo=timezone.utc)