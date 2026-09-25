from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrity,
    HistoricalM452VerificationReceiptHistoryIntegrityError,
    build_historical_m4_52_verification_receipt_history_integrity,
)
from .models import Base


class HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(ValueError):
    """Raised when an M4.53 history-integrity snapshot is invalid or tampered."""


class HistoricalM452VerificationReceiptHistoryIntegrityRecord(Base):
    """Append-only point-in-time integrity snapshot of M4.52 receipt history."""

    __tablename__ = "historical_m4_52_receipt_history_integrity_m4_53"
    __table_args__ = (
        Index("ix_m4_53_history_integrity_created_at", "created_at"),
        Index("ix_m4_53_history_integrity_fingerprint", "fingerprint", unique=True),
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

    def to_integrity(self) -> HistoricalM452VerificationReceiptHistoryIntegrity:
        try:
            return HistoricalM452VerificationReceiptHistoryIntegrity(
                integrity_version=self.integrity_version,
                record_count=self.record_count,
                valid_count=self.valid_count,
                history_fingerprint=self.history_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (
            TypeError,
            ValueError,
            HistoricalM452VerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "persisted M4.53 history integrity snapshot is structurally invalid"
            ) from exc


class HistoricalM452VerificationReceiptHistoryIntegrityRepository:
    """Append-only M4.53 capture, history and point-in-time verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        *,
        captured_by: str,
    ) -> HistoricalM452VerificationReceiptHistoryIntegrityRecord:
        actor = captured_by.strip()
        if not actor:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "captured_by is required"
            )

        source_repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                self.session
            )
        )
        source_records = list(
            self.session.scalars(
                select(
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
                ).order_by(
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.asc(),
                )
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)

        integrity = build_historical_m4_52_verification_receipt_history_integrity(
            source_records
        )
        existing = self.session.scalar(
            select(HistoricalM452VerificationReceiptHistoryIntegrityRecord).where(
                HistoricalM452VerificationReceiptHistoryIntegrityRecord.fingerprint
                == integrity.fingerprint
            )
        )
        if existing is not None:
            if existing.captured_by != actor:
                raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                    "M4.53 history integrity fingerprint is already captured by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalM452VerificationReceiptHistoryIntegrityRecord(
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
    ) -> tuple[list[HistoricalM452VerificationReceiptHistoryIntegrityRecord], bool]:
        if limit < 1 or limit > 100:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(HistoricalM452VerificationReceiptHistoryIntegrityRecord)
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalM452VerificationReceiptHistoryIntegrityRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalM452VerificationReceiptHistoryIntegrityRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalM452VerificationReceiptHistoryIntegrityRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalM452VerificationReceiptHistoryIntegrityRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalM452VerificationReceiptHistoryIntegrityRecord.created_at.desc(),
                    HistoricalM452VerificationReceiptHistoryIntegrityRecord.id.desc(),
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
    ) -> HistoricalM452VerificationReceiptHistoryIntegrityRecord:
        record = self.session.get(
            HistoricalM452VerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "M4.53 history integrity snapshot not found"
            )
        stored = record.to_integrity()

        source_repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                self.session
            )
        )
        source_query = (
            select(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                < record.created_at
            )
            .order_by(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            reconstructed = (
                build_historical_m4_52_verification_receipt_history_integrity(
                    source_records
                )
            )
        except (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            HistoricalM452VerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                f"M4.52 history reconstruction failed: {exc}"
            ) from exc

        if stored != reconstructed:
            raise HistoricalM452VerificationReceiptHistoryIntegrityPersistenceError(
                "M4.53 history integrity snapshot differs from reconstructed M4.52 receipt history"
            )
        return record
