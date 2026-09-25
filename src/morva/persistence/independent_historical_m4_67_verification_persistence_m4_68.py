from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityPersistenceError,
    HistoricalM463ReceiptHistoryIntegrityRecord,
    HistoricalM463ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_64_verification_receipts_m4_66 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_67_verification_persistence_m4_68 import (
    IndependentHistoricalM466VerificationPersistenceError,
    IndependentHistoricalM466VerificationPersistenceReceipt,
    persist_historical_m4_67_verification,
)
from .models import Base


class IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
    ValueError
):
    """Raised when an M4.68 persisted verification result is invalid or tampered."""


class IndependentHistoricalM466VerificationPersistenceReceiptRecord(Base):
    """Append-only persisted result of independent M4.67 verification."""

    __tablename__ = "independent_m4_66_verification_results_m4_68"
    __table_args__ = (
        Index("ix_m4_68_receipt_id", "verification_receipt_id"),
        Index("ix_m4_68_valid", "valid"),
        Index("ix_m4_68_created_at", "created_at"),
        Index(
            "ix_m4_68_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("independent_m4_64_verification_receipts_m4_66.id"),
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

    def to_verification(self) -> IndependentHistoricalM466VerificationPersistenceReceipt:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "persisted M4.68 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM466VerificationPersistenceReceipt(
                verification_receipt_id=self.verification_receipt_id,
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
            IndependentHistoricalM466VerificationPersistenceError,
        ) as exc:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "persisted M4.68 independent verification result is structurally invalid"
            ) from exc


class IndependentHistoricalM466VerificationPersistenceReceiptRepository:
    """Append-only M4.68 persistence with source-chain re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, verification_receipt_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "recorded_by is required"
            )
        receipt = self._get_receipt(verification_receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        source_records = self._source_records(snapshot)
        verification = persist_historical_m4_67_verification(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
        existing = self.session.scalar(
            select(IndependentHistoricalM466VerificationPersistenceReceiptRecord).where(
                IndependentHistoricalM466VerificationPersistenceReceiptRecord.verification_fingerprint
                == verification.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalM466VerificationPersistenceReceiptRecord(
            verification_receipt_id=verification.verification_receipt_id,
            persisted_snapshot_id=verification.persisted_snapshot_id,
            reconstructed_snapshot_id=verification.reconstructed_snapshot_id,
            persisted_verification_fingerprint=verification.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=verification.reconstructed_verification_fingerprint,
            valid=verification.valid,
            blockers_json=json.dumps(
                list(verification.blockers),
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            verification_fingerprint=verification.verification_fingerprint,
            recorded_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_verification()
        return record

    def list(
        self,
        *,
        verification_receipt_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
        if verification_receipt_id is not None:
            query = query.where(
                IndependentHistoricalM466VerificationPersistenceReceiptRecord.verification_receipt_id
                == verification_receipt_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalM466VerificationPersistenceReceiptRecord.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalM466VerificationPersistenceReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalM466VerificationPersistenceReceiptRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentHistoricalM466VerificationPersistenceReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalM466VerificationPersistenceReceiptRecord.id
                        < before_id
                    )
                )
            )
        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalM466VerificationPersistenceReceiptRecord.created_at.desc(),
                    IndependentHistoricalM466VerificationPersistenceReceiptRecord.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_id: UUID):
        record = self.session.get(
            IndependentHistoricalM466VerificationPersistenceReceiptRecord,
            verification_id,
        )
        if record is None:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.68 independent verification result not found"
            )
        stored = record.to_verification()
        receipt = self._get_receipt(record.verification_receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        source_records = self._source_records(snapshot)
        reconstructed = persist_historical_m4_67_verification(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
        if stored != reconstructed:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.68 persisted independent verification result differs from reconstruction"
            )
        return record

    def _get_receipt(self, verification_receipt_id: UUID):
        receipt = self.session.get(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if receipt is None:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.66 verification receipt not found"
            )
        try:
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
                self.session
            ).verify(receipt.id)
        except IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.66 source verification receipt failed verification"
            ) from exc
        return receipt

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(HistoricalM463ReceiptHistoryIntegrityRecord, snapshot_id)
        if snapshot is None:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.64 receipt-history integrity snapshot not found"
            )
        try:
            HistoricalM463ReceiptHistoryIntegrityRepository(self.session).verify(snapshot.id)
        except HistoricalM463ReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.64 source snapshot failed verification"
            ) from exc
        return snapshot

    def _source_records(self, snapshot):
        records = list(
            self.session.scalars(
                select(IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord)
                .where(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                    < snapshot.created_at
                )
                .order_by(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        repository = IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(
            self.session
        )
        try:
            for source in records:
                repository.verify(source.id)
        except IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError(
                "M4.63 source verification history failed verification"
            ) from exc
        return records
