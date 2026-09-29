from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrity,
    HistoricalM471VerificationHistoryIntegrityError,
    build_historical_m4_71_verification_history_integrity,
)
from .models import Base


class HistoricalM471VerificationHistoryIntegrityPersistenceError(ValueError):
    """Raised when an M4.72 verification-receipt history snapshot is invalid or tampered."""


class HistoricalM471VerificationHistoryIntegrityRecord(Base):
    """Append-only point-in-time integrity snapshot of M4.71 receipts."""

    __tablename__ = "historical_m4_71_verification_history_integrity_m4_72"
    __table_args__ = (
        Index("ix_m4_72_history_integrity_created_at", "created_at"),
        Index("ix_m4_72_history_integrity_fingerprint", "fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    integrity_version: Mapped[int] = mapped_column(nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False)
    valid_count: Mapped[int] = mapped_column(nullable=False)
    history_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_integrity(self) -> HistoricalM471VerificationHistoryIntegrity:
        try:
            return HistoricalM471VerificationHistoryIntegrity(
                integrity_version=self.integrity_version,
                record_count=self.record_count,
                valid_count=self.valid_count,
                history_fingerprint=self.history_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (
            TypeError,
            ValueError,
            HistoricalM471VerificationHistoryIntegrityError,
        ) as exc:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "persisted M4.72 verification-receipt history integrity is structurally invalid"
            ) from exc


class HistoricalM471VerificationHistoryIntegrityRepository:
    """Append-only M4.72 capture, history and point-in-time verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(self, *, captured_by: str):
        actor = captured_by.strip()
        if not actor:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "captured_by is required"
            )
        source_repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            self.session
        )
        source_records = list(
            self.session.scalars(
                select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord).order_by(
                    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)

        integrity = build_historical_m4_71_verification_history_integrity(source_records)
        existing = self.session.scalar(
            select(HistoricalM471VerificationHistoryIntegrityRecord).where(
                HistoricalM471VerificationHistoryIntegrityRecord.fingerprint
                == integrity.fingerprint
            )
        )
        if existing is not None:
            if existing.captured_by != actor:
                raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                    "M4.72 history integrity fingerprint is already captured by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalM471VerificationHistoryIntegrityRecord(
            integrity_version=integrity.integrity_version,
            record_count=integrity.record_count,
            valid_count=integrity.valid_count,
            history_fingerprint=integrity.history_fingerprint,
            fingerprint=integrity.fingerprint,
            captured_by=actor,
        )
        self.session.add(record)
        self.session.flush()
        record.to_integrity()
        return record

    def list(
        self,
        *,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(HistoricalM471VerificationHistoryIntegrityRecord)
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalM471VerificationHistoryIntegrityRecord.created_at < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalM471VerificationHistoryIntegrityRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalM471VerificationHistoryIntegrityRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalM471VerificationHistoryIntegrityRecord.id < before_id
                    )
                )
            )
        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalM471VerificationHistoryIntegrityRecord.created_at.desc(),
                    HistoricalM471VerificationHistoryIntegrityRecord.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, snapshot_id: UUID):
        record = self.session.get(HistoricalM471VerificationHistoryIntegrityRecord, snapshot_id)
        if record is None:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "M4.72 verification-receipt history integrity snapshot not found"
            )
        stored = record.to_integrity()
        source_repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            self.session
        )
        source_records = list(
            self.session.scalars(
                select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord)
                .where(
                    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at
                    < record.created_at
                )
                .order_by(
                    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            reconstructed = build_historical_m4_71_verification_history_integrity(source_records)
        except (
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
            HistoricalM471VerificationHistoryIntegrityError,
        ) as exc:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                f"M4.71 history reconstruction failed: {exc}"
            ) from exc
        if stored != reconstructed:
            raise HistoricalM471VerificationHistoryIntegrityPersistenceError(
                "M4.72 history integrity snapshot differs from reconstructed M4.71 receipt history"
            )
        return record
