from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_60_receipt_history_integrity_m4_61 import (
    HistoricalM460ReceiptHistoryIntegrityPersistenceError,
    HistoricalM460ReceiptHistoryIntegrityRecord,
    HistoricalM460ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_61_receipt_history_verifier_m4_62 import (
    IndependentHistoricalM461ReceiptHistoryIntegrity,
    IndependentHistoricalM461ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_61_receipt_history_integrity,
)
from .models import Base


class IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
    ValueError
):
    """Raised when an M4.63 verification receipt is invalid or tampered."""


class IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord(Base):
    """Append-only persisted result of independent M4.62 verification."""

    __tablename__ = "independent_m4_61_verification_receipts_m4_63"
    __table_args__ = (
        Index("ix_m4_63_snapshot_id", "snapshot_id"),
        Index("ix_m4_63_valid", "valid"),
        Index("ix_m4_63_created_at", "created_at"),
        Index(
            "ix_m4_63_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_m4_60_receipt_history_integrity_m4_61.id"),
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
    ) -> IndependentHistoricalM461ReceiptHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.63 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalM461ReceiptHistoryIntegrity(
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
            IndependentHistoricalM461ReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.63 independent verification receipt is structurally invalid"
            ) from exc


class IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository:
    """Append-only M4.63 persistence with independent snapshot/source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        snapshot_id: UUID,
        recorded_by: str,
    ) -> IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord:
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "recorded_by is required"
            )

        snapshot = self._get_snapshot(snapshot_id)
        independent = self._reconstruct(snapshot)
        existing = self.session.scalar(
            select(IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord).where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord(
            snapshot_id=independent.snapshot_id,
            persisted_fingerprint=independent.persisted_fingerprint,
            reconstructed_fingerprint=independent.reconstructed_fingerprint,
            persisted_history_fingerprint=independent.persisted_history_fingerprint,
            reconstructed_history_fingerprint=independent.reconstructed_history_fingerprint,
            persisted_record_count=independent.persisted_record_count,
            reconstructed_record_count=independent.reconstructed_record_count,
            persisted_valid_count=independent.persisted_valid_count,
            reconstructed_valid_count=independent.reconstructed_valid_count,
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
        snapshot_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> tuple[
        list[IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord)
        if snapshot_id is not None:
            query = query.where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.snapshot_id
                == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.created_at.desc(),
                    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord.id.desc(),
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
    ) -> IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord:
        record = self.session.get(
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if record is None:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.63 independent verification receipt not found"
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        expected = self._reconstruct(snapshot)
        if stored != expected:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.63 independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(
        self,
        snapshot_id: UUID,
    ) -> HistoricalM460ReceiptHistoryIntegrityRecord:
        snapshot = self.session.get(
            HistoricalM460ReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.61 history integrity snapshot not found"
            )
        source_repository = HistoricalM460ReceiptHistoryIntegrityRepository(self.session)
        try:
            source_repository.verify(snapshot.id)
        except HistoricalM460ReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.61 source snapshot failed verification"
            ) from exc
        return snapshot

    def _reconstruct(
        self,
        snapshot: HistoricalM460ReceiptHistoryIntegrityRecord,
    ) -> IndependentHistoricalM461ReceiptHistoryIntegrity:
        source_query = (
            select(IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            self.session
        )
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            return independently_verify_historical_m4_61_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        except (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalM461ReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalM461ReceiptHistoryIntegrityReceiptPersistenceError(
                f"M4.62 independent reconstruction failed: {exc}"
            ) from exc
