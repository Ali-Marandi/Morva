from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

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
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotPersistenceError,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    HistoricalFreshnessChainVerification,
    HistoricalFreshnessChainVerificationError,
    verify_historical_freshness_chain,
)
from .models import Base


class HistoricalFreshnessChainVerificationReceiptPersistenceError(ValueError):
    """Raised when an M4.44 verification receipt is invalid or tampered."""


class HistoricalFreshnessChainVerificationReceiptRecord(Base):
    """Immutable persistence record for deterministic M4.43 verification results."""

    __tablename__ = "historical_freshness_chain_verification_receipts_m4_44"
    __table_args__ = (
        Index("ix_m4_44_verification_lineage_id", "lineage_id"),
        Index("ix_m4_44_verification_state", "state"),
        Index("ix_m4_44_verification_created_at", "created_at"),
        Index("ix_m4_44_verification_fingerprint", "fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lineage_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_snapshot_freshness_receipt_lineages_m4_41.id"),
        nullable=False,
    )
    freshness_receipt_id: Mapped[UUID] = mapped_column(nullable=False)
    historical_binding_id: Mapped[UUID] = mapped_column(nullable=False)
    snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    lineage_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    freshness_receipt_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    historical_binding_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[int] = mapped_column(nullable=False)
    policy_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    registry_integrity_version: Mapped[int] = mapped_column(nullable=False)
    registry_policy_count: Mapped[int] = mapped_column(nullable=False)
    registry_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> HistoricalFreshnessChainVerification:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "persisted M4.44 blockers payload is invalid"
            ) from exc
        try:
            return HistoricalFreshnessChainVerification(
                verification_version=1,
                freshness_receipt_id=self.freshness_receipt_id,
                historical_binding_id=self.historical_binding_id,
                snapshot_id=self.snapshot_id,
                lineage_fingerprint=self.lineage_fingerprint,
                freshness_receipt_fingerprint=self.freshness_receipt_fingerprint,
                historical_binding_fingerprint=self.historical_binding_fingerprint,
                snapshot_fingerprint=self.snapshot_fingerprint,
                policy_id=self.policy_id,
                policy_version=self.policy_version,
                policy_fingerprint=self.policy_fingerprint,
                registry_integrity_version=self.registry_integrity_version,
                registry_policy_count=self.registry_policy_count,
                registry_fingerprint=self.registry_fingerprint,
                state=self.state,
                blockers=blockers,
                fingerprint=self.fingerprint,
            )
        except (TypeError, ValueError, HistoricalFreshnessChainVerificationError) as exc:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "persisted M4.44 verification receipt is structurally invalid"
            ) from exc


class HistoricalFreshnessChainVerificationReceiptRepository:
    """Append-only M4.44 receipt persistence with independent re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        lineage_id: UUID,
        recorded_by: str,
    ) -> HistoricalFreshnessChainVerificationReceiptRecord:
        actor = recorded_by.strip()
        if not actor:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "recorded_by is required"
            )

        verification = self._reconstruct(lineage_id)
        existing = self.session.scalar(
            select(HistoricalFreshnessChainVerificationReceiptRecord).where(
                HistoricalFreshnessChainVerificationReceiptRecord.fingerprint
                == verification.fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalFreshnessChainVerificationReceiptRecord(
            lineage_id=lineage_id,
            freshness_receipt_id=verification.freshness_receipt_id,
            historical_binding_id=verification.historical_binding_id,
            snapshot_id=verification.snapshot_id,
            lineage_fingerprint=verification.lineage_fingerprint,
            freshness_receipt_fingerprint=verification.freshness_receipt_fingerprint,
            historical_binding_fingerprint=verification.historical_binding_fingerprint,
            snapshot_fingerprint=verification.snapshot_fingerprint,
            policy_id=verification.policy_id,
            policy_version=verification.policy_version,
            policy_fingerprint=verification.policy_fingerprint,
            registry_integrity_version=verification.registry_integrity_version,
            registry_policy_count=verification.registry_policy_count,
            registry_fingerprint=verification.registry_fingerprint,
            state=verification.state,
            blockers_json=json.dumps(
                list(verification.blockers),
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            fingerprint=verification.fingerprint,
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_verification()
        return record

    def list(
        self,
        *,
        lineage_id: UUID | None = None,
        state: str | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[
        list[HistoricalFreshnessChainVerificationReceiptRecord],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )
        normalized_state = state.strip() if state is not None else None
        if normalized_state is not None and normalized_state not in {"verified", "blocked"}:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "state must be verified or blocked"
            )

        query = select(HistoricalFreshnessChainVerificationReceiptRecord)
        if lineage_id is not None:
            query = query.where(
                HistoricalFreshnessChainVerificationReceiptRecord.lineage_id == lineage_id
            )
        if normalized_state is not None:
            query = query.where(
                HistoricalFreshnessChainVerificationReceiptRecord.state == normalized_state
            )

        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalFreshnessChainVerificationReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalFreshnessChainVerificationReceiptRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        HistoricalFreshnessChainVerificationReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalFreshnessChainVerificationReceiptRecord.id < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalFreshnessChainVerificationReceiptRecord.created_at.desc(),
                    HistoricalFreshnessChainVerificationReceiptRecord.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(
        self,
        receipt_id: UUID,
    ) -> HistoricalFreshnessChainVerificationReceiptRecord:
        record = self.session.get(
            HistoricalFreshnessChainVerificationReceiptRecord,
            receipt_id,
        )
        if record is None:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "historical freshness chain verification receipt not found"
            )
        stored = record.to_verification()
        reconstructed = self._reconstruct(record.lineage_id)
        if stored.fingerprint != reconstructed.fingerprint:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "M4.44 verification fingerprint differs from reconstructed chain"
            )
        if (
            stored.state != reconstructed.state
            or stored.blockers != reconstructed.blockers
        ):
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "M4.44 verification result differs from reconstructed chain"
            )
        if stored.lineage_fingerprint != record.lineage_fingerprint:
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                "M4.44 lineage fingerprint differs from persisted identity"
            )
        return record

    def _reconstruct(self, lineage_id: UUID) -> HistoricalFreshnessChainVerification:
        lineage_repository = HistoricalSnapshotFreshnessReceiptLineageRepository(self.session)
        freshness_repository = HistoricalSnapshotBoundFreshnessReceiptRepository(self.session)
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(
            self.session
        )
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(self.session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(self.session)
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
            return verify_historical_freshness_chain(
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
            raise HistoricalFreshnessChainVerificationReceiptPersistenceError(
                f"M4.43 chain reconstruction failed: {exc}"
            ) from exc
