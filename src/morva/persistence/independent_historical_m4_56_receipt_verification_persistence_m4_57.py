from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM452VerificationReceiptHistoryIntegrityRecord,
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_55_receipt_verifier_m4_56 import (
    independently_verify_historical_m4_55_receipt,
)
from morva.runtime.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationPersistenceError as RuntimePersistenceError,
    IndependentHistoricalM455ReceiptVerificationReceipt,
)
from .models import Base


class IndependentHistoricalM455ReceiptVerificationPersistenceError(ValueError):
    """Raised when an M4.57 persisted verification result is invalid or tampered."""


class IndependentHistoricalM455ReceiptVerificationRecord(Base):
    """Append-only persisted result of independent M4.56 verification."""

    __tablename__ = "independent_m4_54_verification_receipts_m4_57"
    __table_args__ = (
        Index("ix_m4_57_receipt_id", "receipt_id"),
        Index("ix_m4_57_valid", "valid"),
        Index("ix_m4_57_created_at", "created_at"),
        Index("ix_m4_57_verification_fingerprint", "verification_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("independent_m4_53_verification_receipts_m4_55.id"),
        nullable=False,
    )
    persisted_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    reconstructed_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    persisted_verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalM455ReceiptVerificationReceipt:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "persisted M4.57 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM455ReceiptVerificationReceipt(
                verification_receipt_id=self.receipt_id,
                persisted_snapshot_id=self.persisted_snapshot_id,
                reconstructed_snapshot_id=self.reconstructed_snapshot_id,
                persisted_verification_fingerprint=self.persisted_verification_fingerprint,
                reconstructed_verification_fingerprint=self.reconstructed_verification_fingerprint,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            RuntimePersistenceError,
        ) as exc:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "persisted M4.57 independent verification result is structurally invalid"
            ) from exc


class IndependentHistoricalM455ReceiptVerificationRepository:
    """Append-only M4.57 persistence with independent M4.56/source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, receipt_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError("recorded_by is required")
        receipt = self._get_receipt(receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        source_records = self._source_records(snapshot)
        verification = independently_verify_historical_m4_55_receipt(
            receipt=receipt, snapshot=snapshot, source_records=source_records
        )
        existing = self.session.scalar(
            select(IndependentHistoricalM455ReceiptVerificationRecord).where(
                IndependentHistoricalM455ReceiptVerificationRecord.verification_fingerprint
                == verification.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing
        record = IndependentHistoricalM455ReceiptVerificationRecord(
            receipt_id=receipt.id,
            persisted_snapshot_id=verification.persisted_snapshot_id,
            reconstructed_snapshot_id=verification.reconstructed_snapshot_id,
            persisted_verification_fingerprint=verification.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=verification.reconstructed_verification_fingerprint,
            valid=verification.valid,
            blockers_json=json.dumps(list(verification.blockers), ensure_ascii=True, separators=(",", ":")),
            verification_fingerprint=verification.verification_fingerprint,
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_verification()
        return record

    def list(self, *, receipt_id: UUID | None = None, valid: bool | None = None, before_created_at: datetime | None = None, before_id: UUID | None = None, limit: int = 50):
        if limit < 1 or limit > 100:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(IndependentHistoricalM455ReceiptVerificationRecord)
        if receipt_id is not None:
            query = query.where(IndependentHistoricalM455ReceiptVerificationRecord.receipt_id == receipt_id)
        if valid is not None:
            query = query.where(IndependentHistoricalM455ReceiptVerificationRecord.valid == valid)
        if before_created_at is not None and before_id is None:
            query = query.where(IndependentHistoricalM455ReceiptVerificationRecord.created_at < before_created_at)
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (IndependentHistoricalM455ReceiptVerificationRecord.created_at < before_created_at)
                | ((IndependentHistoricalM455ReceiptVerificationRecord.created_at == before_created_at)
                   & (IndependentHistoricalM455ReceiptVerificationRecord.id < before_id))
            )
        records = list(self.session.scalars(
            query.order_by(
                IndependentHistoricalM455ReceiptVerificationRecord.created_at.desc(),
                IndependentHistoricalM455ReceiptVerificationRecord.id.desc(),
            ).limit(limit + 1)
        ).all())
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_id: UUID):
        record = self.session.get(IndependentHistoricalM455ReceiptVerificationRecord, verification_id)
        if record is None:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.57 independent verification receipt not found"
            )
        stored = record.to_verification()
        receipt = self._get_receipt(record.receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        source_records = self._source_records(snapshot)
        reconstructed = independently_verify_historical_m4_55_receipt(
            receipt=receipt, snapshot=snapshot, source_records=source_records
        )
        expected = IndependentHistoricalM455ReceiptVerificationReceipt(
            verification_receipt_id=receipt.id,
            persisted_snapshot_id=reconstructed.persisted_snapshot_id,
            reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
            persisted_verification_fingerprint=reconstructed.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=reconstructed.reconstructed_verification_fingerprint,
            valid=reconstructed.valid,
            blockers=reconstructed.blockers,
            verification_fingerprint=reconstructed.verification_fingerprint,
        )
        if stored != expected:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.57 persisted independent verification result differs from reconstruction"
            )
        return record

    def _get_receipt(self, receipt_id: UUID):
        receipt = self.session.get(IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord, receipt_id)
        if receipt is None:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.55 independent verification receipt not found"
            )
        try:
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(self.session).verify(receipt.id)
        except IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.55 source verification receipt failed verification"
            ) from exc
        return receipt

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(HistoricalM452VerificationReceiptHistoryIntegrityRecord, snapshot_id)
        if snapshot is None:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.53 history integrity snapshot not found"
            )
        try:
            HistoricalM452VerificationReceiptHistoryIntegrityRepository(self.session).verify(snapshot.id)
        except HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.53 source snapshot failed verification"
            ) from exc
        return snapshot

    def _source_records(self, snapshot):
        records = list(self.session.scalars(
            select(IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord)
            .where(IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at < snapshot.created_at)
            .order_by(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        ).all())
        repo = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(self.session)
        try:
            for source in records:
                repo.verify(source.id)
        except IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "M4.52 source verification history failed verification"
            ) from exc
        return records