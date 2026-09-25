from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
    IndependentHistoricalFreshnessReceiptVerificationRecord,
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from morva.runtime.independent_historical_freshness_verification_history_integrity_verifier_m4_48 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrity,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
    independently_verify_historical_freshness_verification_history_integrity,
)
from .models import Base


class IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
    ValueError
):
    """Raised when an M4.49 verification receipt is invalid or tampered."""


class IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord(Base):
    """Append-only persisted result of independent M4.48 verification."""

    __tablename__ = (
        "independent_historical_freshness_verification_history_integrity_receipts_m4_49"
    )
    __table_args__ = (
        Index("ix_m4_49_verification_snapshot_id", "snapshot_id"),
        Index("ix_m4_49_verification_valid", "valid"),
        Index("ix_m4_49_verification_created_at", "created_at"),
        Index("ix_m4_49_verification_fingerprint", "verification_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_freshness_verification_history_integrity_m4_47.id"),
        nullable=False,
    )
    persisted_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    persisted_history_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_history_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    persisted_record_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_record_count: Mapped[int] = mapped_column(nullable=False)
    persisted_valid_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_valid_count: Mapped[int] = mapped_column(nullable=False)
    persisted_chain_valid_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_chain_valid_count: Mapped[int] = mapped_column(nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalFreshnessVerificationHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "persisted M4.49 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalFreshnessVerificationHistoryIntegrity(
                snapshot_id=self.snapshot_id,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                persisted_history_fingerprint=self.persisted_history_fingerprint,
                reconstructed_history_fingerprint=self.reconstructed_history_fingerprint,
                persisted_record_count=self.persisted_record_count,
                reconstructed_record_count=self.reconstructed_record_count,
                persisted_valid_count=self.persisted_valid_count,
                reconstructed_valid_count=self.reconstructed_valid_count,
                persisted_chain_valid_count=self.persisted_chain_valid_count,
                reconstructed_chain_valid_count=self.reconstructed_chain_valid_count,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "persisted M4.49 independent verification receipt is structurally invalid"
            ) from exc


class IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository:
    """Append-only M4.49 persistence with independent point-in-time re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, snapshot_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "recorded_by is required"
            )
        snapshot = self._get_snapshot(snapshot_id)
        independent = self._reconstruct(snapshot)
        existing = self.session.scalar(
            select(IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord).where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord(
            snapshot_id=independent.snapshot_id,
            persisted_fingerprint=independent.persisted_fingerprint,
            reconstructed_fingerprint=independent.reconstructed_fingerprint,
            persisted_history_fingerprint=independent.persisted_history_fingerprint,
            reconstructed_history_fingerprint=independent.reconstructed_history_fingerprint,
            persisted_record_count=independent.persisted_record_count,
            reconstructed_record_count=independent.reconstructed_record_count,
            persisted_valid_count=independent.persisted_valid_count,
            reconstructed_valid_count=independent.reconstructed_valid_count,
            persisted_chain_valid_count=independent.persisted_chain_valid_count,
            reconstructed_chain_valid_count=independent.reconstructed_chain_valid_count,
            valid=independent.valid,
            blockers_json=json.dumps(list(independent.blockers), ensure_ascii=True, separators=(",", ":")),
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
        snapshot_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord)
        if snapshot_id is not None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.snapshot_id
                == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at.desc(),
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_receipt_id: UUID):
        record = self.session.get(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if record is None:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "M4.49 independent verification receipt not found"
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        expected = self._reconstruct(snapshot)
        if stored != expected:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "M4.49 independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(
            HistoricalFreshnessVerificationHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "M4.47 history integrity snapshot not found"
            )
        try:
            snapshot.to_integrity()
        except HistoricalFreshnessVerificationHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                "M4.47 source snapshot is structurally invalid"
            ) from exc
        return snapshot

    def _reconstruct(self, snapshot):
        source_query = (
            select(IndependentHistoricalFreshnessReceiptVerificationRecord)
            .where(
                IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.asc(),
                IndependentHistoricalFreshnessReceiptVerificationRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = IndependentHistoricalFreshnessReceiptVerificationRepository(self.session)
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            return independently_verify_historical_freshness_verification_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        except (
            IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
            IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError(
                f"M4.48 independent reconstruction failed: {exc}"
            ) from exc
