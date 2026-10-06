from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_m4_78 import (
    IndependentHistoricalM475VerificationReceiptM478,
    IndependentHistoricalM475VerificationReceiptM478Error,
    independently_verify_historical_m4_75_verification_receipt_m4_77,
)
from .models import Base


class IndependentM478VerificationReceiptM479PersistenceError(ValueError):
    """Raised when an M4.79 persisted independent-verification receipt is invalid."""


class IndependentM478VerificationReceiptM479Record(Base):
    """Append-only persisted result of independent M4.78 verification."""

    __tablename__ = "independent_m4_78_verification_receipts_m4_79"
    __table_args__ = (
        Index("ix_m4_79_verification_receipt_id", "verification_receipt_id"),
        Index("ix_m4_79_verification_valid", "valid"),
        Index("ix_m4_79_verification_created_at", "created_at"),
        Index("ix_m4_79_verification_recorded_by", "recorded_by"),
        Index("ix_m4_79_verification_fingerprint", "verification_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("independent_historical_m4_75_verification_receipts_m4_77.id"),
        nullable=False,
    )
    persisted_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    reconstructed_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    persisted_verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    persisted_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reconstructed_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    persisted_blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    reconstructed_blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentHistoricalM475VerificationReceiptM478:
        try:
            persisted_blockers = tuple(json.loads(self.persisted_blockers_json))
            reconstructed_blockers = tuple(json.loads(self.reconstructed_blockers_json))
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "persisted M4.79 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM475VerificationReceiptM478(
                verification_receipt_id=self.verification_receipt_id,
                persisted_snapshot_id=self.persisted_snapshot_id,
                reconstructed_snapshot_id=self.reconstructed_snapshot_id,
                persisted_verification_fingerprint=self.persisted_verification_fingerprint,
                reconstructed_verification_fingerprint=self.reconstructed_verification_fingerprint,
                persisted_valid=self.persisted_valid,
                reconstructed_valid=self.reconstructed_valid,
                persisted_blockers=persisted_blockers,
                reconstructed_blockers=reconstructed_blockers,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (TypeError, ValueError, IndependentHistoricalM475VerificationReceiptM478Error) as exc:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "persisted M4.79 independent verification receipt is structurally invalid"
            ) from exc


class IndependentM478VerificationReceiptM479Repository:
    """Persist M4.78 results and independently reconstruct them on record/read."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, verification_receipt_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentM478VerificationReceiptM479PersistenceError("recorded_by is required")
        source_receipt = self._get_source_receipt(verification_receipt_id)
        independent = self._reconstruct(source_receipt)
        existing = self.session.scalar(
            select(IndependentM478VerificationReceiptM479Record).where(
                IndependentM478VerificationReceiptM479Record.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentM478VerificationReceiptM479PersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentM478VerificationReceiptM479Record(
            verification_receipt_id=independent.verification_receipt_id,
            persisted_snapshot_id=independent.persisted_snapshot_id,
            reconstructed_snapshot_id=independent.reconstructed_snapshot_id,
            persisted_verification_fingerprint=independent.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=independent.reconstructed_verification_fingerprint,
            persisted_valid=independent.persisted_valid,
            reconstructed_valid=independent.reconstructed_valid,
            persisted_blockers_json=json.dumps(list(independent.persisted_blockers), ensure_ascii=True, separators=(",", ":")),
            reconstructed_blockers_json=json.dumps(list(independent.reconstructed_blockers), ensure_ascii=True, separators=(",", ":")),
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
        verification_receipt_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise IndependentM478VerificationReceiptM479PersistenceError("limit must be between 1 and 100")
        if (before_created_at is None) != (before_id is None):
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "before_created_at and before_id must be supplied together"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentM478VerificationReceiptM479PersistenceError("before_created_at must be timezone-aware")

        query = select(IndependentM478VerificationReceiptM479Record)
        if verification_receipt_id is not None:
            query = query.where(
                IndependentM478VerificationReceiptM479Record.verification_receipt_id == verification_receipt_id
            )
        if valid is not None:
            query = query.where(IndependentM478VerificationReceiptM479Record.valid == valid)
        if before_created_at is not None:
            query = query.where(
                (IndependentM478VerificationReceiptM479Record.created_at < before_created_at)
                | (
                    (IndependentM478VerificationReceiptM479Record.created_at == before_created_at)
                    & (IndependentM478VerificationReceiptM479Record.id < before_id)
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentM478VerificationReceiptM479Record.created_at.desc(),
                    IndependentM478VerificationReceiptM479Record.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_id: UUID):
        record = self.session.get(IndependentM478VerificationReceiptM479Record, verification_id)
        if record is None:
            raise IndependentM478VerificationReceiptM479PersistenceError("M4.79 independent verification receipt not found")
        stored = record.to_verification()
        expected = self._reconstruct(self._get_source_receipt(record.verification_receipt_id))
        if stored != expected:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "M4.79 independent verification result differs from reconstruction"
            )
        return record

    def _get_source_receipt(self, verification_receipt_id: UUID):
        receipt = self.session.get(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
            verification_receipt_id,
        )
        if receipt is None:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "M4.77 independent verification receipt not found"
            )
        return receipt

    def _reconstruct(self, source_receipt):
        snapshot = self.session.get(
            HistoricalM474VerificationReceiptHistoryIntegrityRecord,
            source_receipt.snapshot_id,
        )
        if snapshot is None:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "M4.75 verification-receipt history integrity snapshot not found"
            )
        try:
            snapshot.to_integrity()
        except HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                "M4.75 source snapshot is structurally invalid"
            ) from exc

        source_query = (
            select(IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(self.session)
        try:
            return independently_verify_historical_m4_75_verification_receipt_m4_77(
                receipt=source_receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
        except IndependentHistoricalM475VerificationReceiptM478Error as exc:
            raise IndependentM478VerificationReceiptM479PersistenceError(
                f"M4.78 independent reconstruction failed: {exc}"
            ) from exc
