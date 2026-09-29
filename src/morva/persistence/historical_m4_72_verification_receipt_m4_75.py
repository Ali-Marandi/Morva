from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityPersistenceError,
    HistoricalM471VerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_72_verification_receipt_m4_75 import (
    IndependentHistoricalM472VerificationReceiptVerification,
    IndependentHistoricalM472VerificationReceiptVerificationError,
    independently_verify_historical_m4_72_verification_receipt,
)
from .models import Base


class HistoricalM472VerificationReceiptM475PersistenceError(ValueError):
    """Raised when an M4.75 verification result is invalid or tampered."""


class HistoricalM472VerificationReceiptM475Record(Base):
    """Append-only persisted result of independent M4.75 verification."""

    __tablename__ = "historical_m4_72_verification_receipt_m4_75"
    __table_args__ = (
        Index("ix_m4_75_verification_receipt_id", "verification_receipt_id"),
        Index("ix_m4_75_verification_valid", "valid"),
        Index("ix_m4_75_verification_created_at", "created_at"),
        Index(
            "ix_m4_75_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "independent_historical_m4_72_verification_receipts_m4_74.id"
        ),
        nullable=False,
    )
    persisted_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    persisted_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    reconstructed_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    persisted_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reconstructed_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalM472VerificationReceiptVerification:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "persisted M4.75 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM472VerificationReceiptVerification(
                verification_receipt_id=self.verification_receipt_id,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                persisted_snapshot_id=self.persisted_snapshot_id,
                reconstructed_snapshot_id=self.reconstructed_snapshot_id,
                persisted_valid=self.persisted_valid,
                reconstructed_valid=self.reconstructed_valid,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentHistoricalM472VerificationReceiptVerificationError,
        ) as exc:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "persisted M4.75 independent verification result is structurally invalid"
            ) from exc


class HistoricalM472VerificationReceiptM475Repository:
    """Append-only M4.75 persistence with independent source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, verification_receipt_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "recorded_by is required"
            )

        receipt = self._get_receipt(verification_receipt_id)
        independent = self._reconstruct(receipt)
        existing = self.session.scalar(
            select(HistoricalM472VerificationReceiptM475Record).where(
                HistoricalM472VerificationReceiptM475Record.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise HistoricalM472VerificationReceiptM475PersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalM472VerificationReceiptM475Record(
            verification_receipt_id=independent.verification_receipt_id,
            persisted_fingerprint=independent.persisted_fingerprint,
            reconstructed_fingerprint=independent.reconstructed_fingerprint,
            persisted_snapshot_id=independent.persisted_snapshot_id,
            reconstructed_snapshot_id=independent.reconstructed_snapshot_id,
            persisted_valid=independent.persisted_valid,
            reconstructed_valid=independent.reconstructed_valid,
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
        verification_receipt_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(HistoricalM472VerificationReceiptM475Record)
        if verification_receipt_id is not None:
            query = query.where(
                HistoricalM472VerificationReceiptM475Record.verification_receipt_id
                == verification_receipt_id
            )
        if valid is not None:
            query = query.where(
                HistoricalM472VerificationReceiptM475Record.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalM472VerificationReceiptM475Record.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalM472VerificationReceiptM475Record.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalM472VerificationReceiptM475Record.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalM472VerificationReceiptM475Record.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalM472VerificationReceiptM475Record.created_at.desc(),
                    HistoricalM472VerificationReceiptM475Record.id.desc(),
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
            HistoricalM472VerificationReceiptM475Record,
            verification_id,
        )
        if record is None:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.75 independent verification result not found"
            )
        stored = record.to_verification()
        expected = self._reconstruct(self._get_receipt(record.verification_receipt_id))
        if stored != expected:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.75 independent verification result differs from reconstruction"
            )
        return record

    def _get_receipt(self, verification_receipt_id: UUID):
        receipt = self.session.get(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if receipt is None:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.74 independent verification receipt not found"
            )
        try:
            receipt.to_verification()
        except IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError as exc:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.74 source receipt is structurally invalid"
            ) from exc
        return receipt

    def _reconstruct(self, receipt):
        snapshot = self.session.get(
            HistoricalM471VerificationHistoryIntegrityRecord,
            receipt.snapshot_id,
        )
        if snapshot is None:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.72 receipt-history integrity snapshot not found"
            )
        try:
            snapshot.to_integrity()
        except HistoricalM471VerificationHistoryIntegrityPersistenceError as exc:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                "M4.72 source snapshot is structurally invalid"
            ) from exc

        source_query = (
            select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            self.session
        )
        try:
            return independently_verify_historical_m4_72_verification_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
        except (
            IndependentHistoricalM472VerificationReceiptVerificationError,
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
        ) as exc:
            raise HistoricalM472VerificationReceiptM475PersistenceError(
                f"M4.75 independent reconstruction failed: {exc}"
            ) from exc
