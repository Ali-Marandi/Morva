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
from morva.runtime.independent_historical_m4_64_receipt_history_verifier_m4_65 import (
    IndependentHistoricalM464ReceiptHistoryIntegrity,
    IndependentHistoricalM464ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_64_receipt_history_integrity,
)
from .models import Base


class IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
    ValueError
):
    """Raised when an M4.66 verification receipt is invalid or tampered."""


class IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord(Base):
    """Append-only persisted result of independent M4.65 verification."""

    __tablename__ = "independent_m4_64_verification_receipts_m4_66"
    __table_args__ = (
        Index("ix_m4_66_snapshot_id", "snapshot_id"),
        Index("ix_m4_66_valid", "valid"),
        Index("ix_m4_66_created_at", "created_at"),
        Index(
            "ix_m4_66_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_m4_63_receipt_history_integrity_m4_64.id"),
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

    def to_verification(
        self,
    ) -> IndependentHistoricalM464ReceiptHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.66 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM464ReceiptHistoryIntegrity(
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
            IndependentHistoricalM464ReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.66 independent verification receipt is structurally invalid"
            ) from exc


class IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository:
    """Append-only M4.66 persistence with independent snapshot/source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        snapshot_id: UUID,
        recorded_by: str,
    ) -> IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord:
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "recorded_by is required"
            )

        snapshot = self._get_snapshot(snapshot_id)
        source_records = self._source_records(snapshot)
        verification = independently_verify_historical_m4_64_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        existing = self.session.scalar(
            select(IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord).where(
                IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.verification_fingerprint
                == verification.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord(
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
        snapshot_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[
        list[IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord)
        if snapshot_id is not None:
            query = query.where(
                IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.snapshot_id
                == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.created_at.desc(),
                    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.id.desc(),
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
        verification_receipt_id: UUID,
    ) -> IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord:
        record = self.session.get(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if record is None:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.66 independent verification receipt not found"
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        source_records = self._source_records(snapshot)
        reconstructed = independently_verify_historical_m4_64_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        if stored != reconstructed:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.66 persisted independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(
        self,
        snapshot_id: UUID,
    ) -> HistoricalM463ReceiptHistoryIntegrityRecord:
        snapshot = self.session.get(
            HistoricalM463ReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.64 history integrity snapshot not found"
            )
        try:
            HistoricalM463ReceiptHistoryIntegrityRepository(self.session).verify(
                snapshot.id
            )
        except HistoricalM463ReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.64 source snapshot failed verification"
            ) from exc
        return snapshot

    def _source_records(
        self,
        snapshot: HistoricalM463ReceiptHistoryIntegrityRecord,
    ) -> list[IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord]:
        source_records = list(
            self.session.scalars(
                select(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
                )
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
            for source_record in source_records:
                repository.verify(source_record.id)
        except IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.63 source verification history failed verification"
            ) from exc
        return source_records
