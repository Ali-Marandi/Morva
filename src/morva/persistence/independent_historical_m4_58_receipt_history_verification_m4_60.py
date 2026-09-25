from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM457VerificationReceiptHistoryIntegrityRecord,
    HistoricalM457VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationPersistenceError,
    IndependentHistoricalM455ReceiptVerificationRecord,
    IndependentHistoricalM455ReceiptVerificationRepository,
)
from morva.runtime.independent_historical_m4_58_receipt_history_verifier_m4_59 import (
    IndependentHistoricalM458ReceiptHistoryIntegrity,
    IndependentHistoricalM458ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_58_receipt_history_integrity,
)
from .models import Base


class IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(ValueError):
    """Raised when an M4.60 persisted M4.59 result is invalid or tampered."""


class IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord(Base):
    """Append-only persisted result of independent M4.59 verification."""

    __tablename__ = "independent_m4_58_verification_receipts_m4_60"
    __table_args__ = (
        Index("ix_m4_60_snapshot_id", "snapshot_id"),
        Index("ix_m4_60_valid", "valid"),
        Index("ix_m4_60_created_at", "created_at"),
        Index("ix_m4_60_verification_fingerprint", "verification_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_m4_57_verification_receipt_history_integrity_m4_58.id"),
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
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalM458ReceiptHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.60 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM458ReceiptHistoryIntegrity(
                snapshot_id=self.snapshot_id,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                persisted_history_fingerprint=self.persisted_history_fingerprint,
                reconstructed_history_fingerprint=self.reconstructed_history_fingerprint,
                persisted_record_count=self.persisted_record_count,
                reconstructed_record_count=self.reconstructed_record_count,
                persisted_valid_count=self.persisted_valid_count,
                reconstructed_valid_count=self.reconstructed_valid_count,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentHistoricalM458ReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.60 independent verification result is structurally invalid"
            ) from exc


class IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository:
    """Append-only M4.60 persistence with independent M4.59/source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, snapshot_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "recorded_by is required"
            )
        snapshot = self._get_snapshot(snapshot_id)
        source_records = self._source_records(snapshot)
        verification = independently_verify_historical_m4_58_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        existing = self.session.scalar(
            select(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord).where(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.verification_fingerprint
                == verification.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing
        record = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord(
            snapshot_id=verification.snapshot_id,
            persisted_fingerprint=verification.persisted_fingerprint,
            reconstructed_fingerprint=verification.reconstructed_fingerprint,
            persisted_history_fingerprint=verification.persisted_history_fingerprint,
            reconstructed_history_fingerprint=verification.reconstructed_history_fingerprint,
            persisted_record_count=verification.persisted_record_count,
            reconstructed_record_count=verification.reconstructed_record_count,
            persisted_valid_count=verification.persisted_valid_count,
            reconstructed_valid_count=verification.reconstructed_valid_count,
            valid=verification.valid,
            blockers_json=json.dumps(list(verification.blockers), ensure_ascii=True, separators=(",", ":")),
            verification_fingerprint=verification.verification_fingerprint,
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_verification()
        return record

    def list(self, *, snapshot_id: UUID | None = None, valid: bool | None = None, before_created_at: datetime | None = None, before_id: UUID | None = None, limit: int = 50):
        if limit < 1 or limit > 100:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord)
        if snapshot_id is not None:
            query = query.where(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.snapshot_id == snapshot_id)
        if valid is not None:
            query = query.where(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.valid == valid)
        if before_created_at is not None and before_id is None:
            query = query.where(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at < before_created_at)
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at < before_created_at)
                | ((IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at == before_created_at)
                   & (IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.id < before_id))
            )
        records = list(self.session.scalars(
            query.order_by(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at.desc(),
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.id.desc(),
            ).limit(limit + 1)
        ).all())
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_id: UUID):
        record = self.session.get(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord, verification_id)
        if record is None:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.60 independent verification receipt not found"
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        source_records = self._source_records(snapshot)
        reconstructed = independently_verify_historical_m4_58_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        if stored != reconstructed:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.60 persisted independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(HistoricalM457VerificationReceiptHistoryIntegrityRecord, snapshot_id)
        if snapshot is None:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.58 history integrity snapshot not found"
            )
        try:
            HistoricalM457VerificationReceiptHistoryIntegrityRepository(self.session).verify(snapshot.id)
        except HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.58 source snapshot failed verification"
            ) from exc
        return snapshot

    def _source_records(self, snapshot):
        source_records = list(self.session.scalars(
            select(IndependentHistoricalM455ReceiptVerificationRecord)
            .where(IndependentHistoricalM455ReceiptVerificationRecord.created_at < snapshot.created_at)
            .order_by(
                IndependentHistoricalM455ReceiptVerificationRecord.created_at.asc(),
                IndependentHistoricalM455ReceiptVerificationRecord.id.asc(),
            )
        ).all())
        repository = IndependentHistoricalM455ReceiptVerificationRepository(self.session)
        try:
            for source_record in source_records:
                repository.verify(source_record.id)
        except IndependentHistoricalM455ReceiptVerificationPersistenceError as exc:
            raise IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.57 source verification history failed verification"
            ) from exc
        return source_records