from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationRepository,
    IndependentHistoricalFreshnessReceiptVerificationRecord,
    IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
)
from morva.runtime.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrity,
    HistoricalFreshnessVerificationHistoryIntegrityError,
    build_historical_freshness_verification_history_integrity,
)
from .models import Base


class HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(ValueError):
    """Raised when an M4.47 integrity snapshot is invalid or tampered."""


class HistoricalFreshnessVerificationHistoryIntegrityRecord(Base):
    """Append-only point-in-time integrity snapshot of the M4.46 history."""

    __tablename__ = "historical_freshness_verification_history_integrity_m4_47"
    __table_args__ = (
        Index(
            "ix_m4_47_history_integrity_created_at",
            "created_at",
        ),
        Index(
            "ix_m4_47_history_integrity_fingerprint",
            "fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    integrity_version: Mapped[int] = mapped_column(nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False)
    valid_count: Mapped[int] = mapped_column(nullable=False)
    chain_valid_count: Mapped[int] = mapped_column(nullable=False)
    history_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_integrity(self) -> HistoricalFreshnessVerificationHistoryIntegrity:
        try:
            return HistoricalFreshnessVerificationHistoryIntegrity(
                integrity_version=self.integrity_version,
                record_count=self.record_count,
                valid_count=self.valid_count,
                chain_valid_count=self.chain_valid_count,
                history_fingerprint=self.history_fingerprint,
                fingerprint=self.fingerprint,
            )
        except (
            TypeError,
            ValueError,
            HistoricalFreshnessVerificationHistoryIntegrityError,
        ) as exc:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "persisted M4.47 history integrity snapshot is structurally invalid"
            ) from exc


class HistoricalFreshnessVerificationHistoryIntegrityRepository:
    """Append-only M4.47 capture, history and point-in-time verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def capture(
        self,
        *,
        captured_by: str,
    ) -> HistoricalFreshnessVerificationHistoryIntegrityRecord:
        actor = captured_by.strip()
        if not actor:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "captured_by is required"
            )

        source_repository = IndependentHistoricalFreshnessReceiptVerificationRepository(
            self.session
        )
        source_records = list(
            self.session.scalars(
                select(IndependentHistoricalFreshnessReceiptVerificationRecord).order_by(
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.asc(),
                    IndependentHistoricalFreshnessReceiptVerificationRecord.id.asc(),
                )
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)

        integrity = build_historical_freshness_verification_history_integrity(
            source_records
        )
        existing = self.session.scalar(
            select(HistoricalFreshnessVerificationHistoryIntegrityRecord).where(
                HistoricalFreshnessVerificationHistoryIntegrityRecord.fingerprint
                == integrity.fingerprint
            )
        )
        if existing is not None:
            if existing.captured_by != actor:
                raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                    "history integrity fingerprint is already captured by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = HistoricalFreshnessVerificationHistoryIntegrityRecord(
            integrity_version=integrity.integrity_version,
            record_count=integrity.record_count,
            valid_count=integrity.valid_count,
            chain_valid_count=integrity.chain_valid_count,
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
    ) -> tuple[list[HistoricalFreshnessVerificationHistoryIntegrityRecord], bool]:
        if limit < 1 or limit > 100:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(HistoricalFreshnessVerificationHistoryIntegrityRecord)
        if before_created_at is not None and before_id is None:
            query = query.where(
                HistoricalFreshnessVerificationHistoryIntegrityRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    HistoricalFreshnessVerificationHistoryIntegrityRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        HistoricalFreshnessVerificationHistoryIntegrityRecord.created_at
                        == before_created_at
                    )
                    & (
                        HistoricalFreshnessVerificationHistoryIntegrityRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    HistoricalFreshnessVerificationHistoryIntegrityRecord.created_at.desc(),
                    HistoricalFreshnessVerificationHistoryIntegrityRecord.id.desc(),
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
    ) -> HistoricalFreshnessVerificationHistoryIntegrityRecord:
        record = self.session.get(
            HistoricalFreshnessVerificationHistoryIntegrityRecord,
            snapshot_id,
        )
        if record is None:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "M4.47 history integrity snapshot not found"
            )
        stored = record.to_integrity()

        source_repository = IndependentHistoricalFreshnessReceiptVerificationRepository(
            self.session
        )
        source_records = list(
            self.session.scalars(
                select(IndependentHistoricalFreshnessReceiptVerificationRecord).order_by(
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.asc(),
                    IndependentHistoricalFreshnessReceiptVerificationRecord.id.asc(),
                )
            ).all()
        )
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            reconstructed = build_historical_freshness_verification_history_integrity(
                source_records
            )
        except (
            IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
            HistoricalFreshnessVerificationHistoryIntegrityError,
        ) as exc:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                f"M4.46 history reconstruction failed: {exc}"
            ) from exc

        if stored != reconstructed:
            raise HistoricalFreshnessVerificationHistoryIntegrityPersistenceError(
                "M4.47 history integrity snapshot differs from reconstructed M4.46 history"
            )
        return record
