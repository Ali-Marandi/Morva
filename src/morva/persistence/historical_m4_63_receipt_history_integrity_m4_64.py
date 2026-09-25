from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrity,
    HistoricalM463ReceiptHistoryIntegrityError,
    build_historical_m4_63_receipt_history_integrity,
)
from .models import Base


class HistoricalM463ReceiptHistoryIntegrityPersistenceError(ValueError):
    """Raised when an M4.64 history-integrity snapshot is invalid or tampered."""


class HistoricalM463ReceiptHistoryIntegrityRecord(Base):
    """Append-only point-in-time integrity snapshot of M4.63 receipt history."""

    __tablename__ = "historical_m4_63_receipt_history_integrity_m4_64"
    __table_args__ = (
        Index("ix_m4_64_history_created_at", "created_at"),
        Index("ix_m4_64_history_fingerprint", "fingerprint", unique=True),
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

    def to_integrity(self) -> HistoricalM463ReceiptHistoryIntegrity:
        try:
            return HistoricalM463ReceiptHistoryIntegrity(
                integrity_version=self.integrity_version,
                record_count=self.record_count,
                valid_count=self.valid_count,
                history_fingerprint=self.history_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (
            TypeError,
            ValueError,
            HistoricalM463ReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "persisted M4.64 history integrity snapshot is structurally invalid"
            ) from exc


class HistoricalM463ReceiptHistoryIntegrityRepository:
    """Append-only M4.64 capture, history and point-in-time verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        *,
        captured_by: str,
    ) -> HistoricalM463ReceiptHistoryIntegrityRecord:
        actor = captured_by.strip()
        if not actor:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "captured_by is required"
            )

        source_repository = IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(
            self.session
        )
        source_records = list(
            self.session.scalars(
                select(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
                ).order_by(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)

        integrity = build_historical_m4_63_receipt_history_integrity(source_records)
        existing = self.session.scalar(
            select(HistoricalM463ReceiptHistoryIntegrityRecord).where(
                HistoricalM463ReceiptHistoryIntegrityRecord.fingerprint
                == integrity.fingerprint
            )
        )
        if existing is not None:
            if existing.captured_by != actor:
                raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                    "M4.64 history integrity fingerprint is already captured by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalM463ReceiptHistoryIntegrityRecord(
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
    ) -> tuple[list[HistoricalM463ReceiptHistoryIntegrityRecord], bool]:
        if limit < 1 or limit > 100:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(HistoricalM463ReceiptHistoryIntegrityRecord)
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalM463ReceiptHistoryIntegrityRecord.created_at < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalM463ReceiptHistoryIntegrityRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalM463ReceiptHistoryIntegrityRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalM463ReceiptHistoryIntegrityRecord.id < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalM463ReceiptHistoryIntegrityRecord.created_at.desc(),
                    HistoricalM463ReceiptHistoryIntegrityRecord.id.desc(),
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
        snapshot_id: UUID,
    ) -> HistoricalM463ReceiptHistoryIntegrityRecord:
        record = self.session.get(
            HistoricalM463ReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "M4.64 history integrity snapshot not found"
            )
        stored = record.to_integrity()

        source_query = (
            select(IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(
            self.session
        )
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            reconstructed = build_historical_m4_63_receipt_history_integrity(
                source_records
            )
        except (
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError,
            HistoricalM463ReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                f"M4.63 history reconstruction failed: {exc}"
            ) from exc

        if stored != reconstructed:
            raise HistoricalM463ReceiptHistoryIntegrityPersistenceError(
                "M4.64 history integrity snapshot differs from reconstructed M4.63 receipt history"
            )
        return record
