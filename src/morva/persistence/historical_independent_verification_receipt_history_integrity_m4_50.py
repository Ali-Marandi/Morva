from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrity,
    HistoricalIndependentVerificationReceiptHistoryIntegrityError,
    build_historical_independent_verification_receipt_history_integrity,
)
from .models import Base


class HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(ValueError):
    """Raised when an M4.50 history-integrity snapshot is invalid or tampered."""


class HistoricalIndependentVerificationReceiptHistoryIntegrityRecord(Base):
    """Append-only point-in-time integrity snapshot of M4.49 receipt history."""

    __tablename__ = "historical_independent_verification_receipt_history_m4_50"
    __table_args__ = (
        Index("ix_m4_50_history_integrity_created_at", "created_at"),
        Index("ix_m4_50_history_integrity_fingerprint", "fingerprint", unique=True),
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

    def to_integrity(self) -> HistoricalIndependentVerificationReceiptHistoryIntegrity:
        try:
            return HistoricalIndependentVerificationReceiptHistoryIntegrity(
                integrity_version=self.integrity_version,
                record_count=self.record_count,
                valid_count=self.valid_count,
                history_fingerprint=self.history_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (
            TypeError,
            ValueError,
            HistoricalIndependentVerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "persisted M4.50 history integrity snapshot is structurally invalid"
            ) from exc


class HistoricalIndependentVerificationReceiptHistoryIntegrityRepository:
    """Append-only M4.50 capture, history and point-in-time verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        *,
        captured_by: str,
    ) -> HistoricalIndependentVerificationReceiptHistoryIntegrityRecord:
        actor = captured_by.strip()
        if not actor:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "captured_by is required"
            )

        source_repository = (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
                self.session
            )
        )
        source_records = list(
            self.session.scalars(
                select(
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
                ).order_by(
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)

        integrity = build_historical_independent_verification_receipt_history_integrity(
            source_records
        )
        existing = self.session.scalar(
            select(HistoricalIndependentVerificationReceiptHistoryIntegrityRecord).where(
                HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.fingerprint
                == integrity.fingerprint
            )
        )
        if existing is not None:
            if existing.captured_by != actor:
                raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                    "M4.50 history integrity fingerprint is already captured by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalIndependentVerificationReceiptHistoryIntegrityRecord(
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
    ) -> tuple[
        list[HistoricalIndependentVerificationReceiptHistoryIntegrityRecord], bool
    ]:
        if limit < 1 or limit > 100:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(HistoricalIndependentVerificationReceiptHistoryIntegrityRecord)
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.created_at.desc(),
                    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.id.desc(),
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
    ) -> HistoricalIndependentVerificationReceiptHistoryIntegrityRecord:
        record = self.session.get(
            HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "M4.50 history integrity snapshot not found"
            )
        stored = record.to_integrity()

        source_repository = (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
                self.session
            )
        )
        source_query = (
            select(IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            reconstructed = (
                build_historical_independent_verification_receipt_history_integrity(
                    source_records
                )
            )
        except (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            HistoricalIndependentVerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                f"M4.49 history reconstruction failed: {exc}"
            ) from exc

        if stored != reconstructed:
            raise HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError(
                "M4.50 history integrity snapshot differs from reconstructed M4.49 receipt history"
            )
        return record
