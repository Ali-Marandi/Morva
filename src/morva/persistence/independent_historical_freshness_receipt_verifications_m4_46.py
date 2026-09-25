from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptPersistenceError,
    HistoricalFreshnessChainVerificationReceiptRecord,
)
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
    HistoricalFreshnessChainVerificationError,
    verify_historical_freshness_chain,
)
from morva.runtime.independent_historical_freshness_chain_verification_receipt_verifier_m4_45 import (
    IndependentHistoricalFreshnessChainVerificationReceipt,
    IndependentHistoricalFreshnessChainVerificationReceiptError,
    verify_historical_freshness_chain_verification_receipt,
)
from .models import Base


class IndependentHistoricalFreshnessReceiptVerificationPersistenceError(ValueError):
    """Raised when an M4.46 independent verification receipt is invalid."""


class IndependentHistoricalFreshnessReceiptVerificationRecord(Base):
    """Write-once persisted result of independent M4.45 verification."""

    __tablename__ = "independent_historical_freshness_receipt_verifications_m4_46"
    __table_args__ = (
        Index("ix_m4_46_independent_verification_receipt_id", "receipt_id"),
        Index("ix_m4_46_independent_verification_lineage_id", "lineage_id"),
        Index("ix_m4_46_independent_verification_valid", "valid"),
        Index("ix_m4_46_independent_verification_created_at", "created_at"),
        Index(
            "ix_m4_46_independent_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_freshness_chain_verification_receipts_m4_44.id"),
        nullable=False,
    )
    lineage_id: Mapped[UUID] = mapped_column(nullable=False)
    persisted_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalFreshnessChainVerificationReceipt:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "persisted M4.46 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalFreshnessChainVerificationReceipt(
                receipt_id=self.receipt_id,
                lineage_id=self.lineage_id,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                chain_valid=self.chain_valid,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentHistoricalFreshnessChainVerificationReceiptError,
        ) as exc:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "persisted M4.46 independent verification receipt is structurally invalid"
            ) from exc


class IndependentHistoricalFreshnessReceiptVerificationRepository:
    """Append-only M4.46 persistence with independent re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        receipt_id: UUID,
        recorded_by: str,
    ) -> IndependentHistoricalFreshnessReceiptVerificationRecord:
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "recorded_by is required"
            )

        source_receipt = self._get_receipt(receipt_id)
        reconstructed = self._reconstruct(source_receipt)
        independent = verify_historical_freshness_chain_verification_receipt(
            receipt=source_receipt,
            reconstructed=reconstructed,
        )
        existing = self.session.scalar(
            select(IndependentHistoricalFreshnessReceiptVerificationRecord).where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalFreshnessReceiptVerificationRecord(
            receipt_id=independent.receipt_id,
            lineage_id=independent.lineage_id,
            persisted_fingerprint=independent.persisted_fingerprint,
            reconstructed_fingerprint=independent.reconstructed_fingerprint,
            chain_valid=independent.chain_valid,
            valid=independent.valid,
            blockers_json=json.dumps(
                list(independent.blockers),
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            verification_fingerprint=independent.verification_fingerprint,
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_verification()
        return record

    def list(
        self,
        *,
        receipt_id: UUID | None = None,
        valid: bool | None = None,
        chain_valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[
        list[IndependentHistoricalFreshnessReceiptVerificationRecord],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(IndependentHistoricalFreshnessReceiptVerificationRecord)
        if receipt_id is not None:
            query = query.where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.receipt_id
                == receipt_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.valid == valid
            )
        if chain_valid is not None:
            query = query.where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.chain_valid
                == chain_valid
            )

        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalFreshnessReceiptVerificationRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.desc(),
                    IndependentHistoricalFreshnessReceiptVerificationRecord.id.desc(),
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
        verification_receipt_id: UUID,
    ) -> IndependentHistoricalFreshnessReceiptVerificationRecord:
        record = self.session.get(
            IndependentHistoricalFreshnessReceiptVerificationRecord,
            verification_receipt_id,
        )
        if record is None:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "M4.46 independent verification receipt not found"
            )
        stored = record.to_verification()
        source_receipt = self._get_receipt(record.receipt_id)
        reconstructed = self._reconstruct(source_receipt)
        expected = verify_historical_freshness_chain_verification_receipt(
            receipt=source_receipt,
            reconstructed=reconstructed,
        )
        if stored != expected:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "M4.46 independent verification result differs from reconstruction"
            )
        if record.lineage_id != source_receipt.lineage_id:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "M4.46 lineage identity differs from source receipt"
            )
        return record

    def _get_receipt(
        self,
        receipt_id: UUID,
    ) -> HistoricalFreshnessChainVerificationReceiptRecord:
        record = self.session.get(
            HistoricalFreshnessChainVerificationReceiptRecord,
            receipt_id,
        )
        if record is None:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "M4.44 historical freshness chain verification receipt not found"
            )
        try:
            record.to_verification()
        except HistoricalFreshnessChainVerificationReceiptPersistenceError as exc:
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                "M4.44 source receipt is structurally invalid"
            ) from exc
        return record

    def _reconstruct(
        self,
        source_receipt: HistoricalFreshnessChainVerificationReceiptRecord,
    ):
        lineage_repository = HistoricalSnapshotFreshnessReceiptLineageRepository(self.session)
        freshness_repository = HistoricalSnapshotBoundFreshnessReceiptRepository(self.session)
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(self.session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(self.session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(self.session)
        try:
            lineage_record = lineage_repository.verify(source_receipt.lineage_id)
            lineage = lineage_record.to_lineage()
            freshness_record = freshness_repository.verify(lineage.freshness_receipt_id)
            freshness = freshness_record.to_freshness()
            binding_record = binding_repository.verify(lineage.historical_binding_id)
            binding = binding_record.to_binding()
            snapshot_record = snapshot_repository.reconstruct(
                lineage.snapshot_id,
                policy_repository,
            )
            return verify_historical_freshness_chain(
                freshness_receipt_id=freshness_record.id,
                freshness=freshness,
                historical_binding_id=binding_record.id,
                historical_binding=binding,
                snapshot_id=snapshot_record.id,
                snapshot=snapshot_record.to_snapshot(),
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
            raise IndependentHistoricalFreshnessReceiptVerificationPersistenceError(
                f"M4.45 independent reconstruction failed: {exc}"
            ) from exc
