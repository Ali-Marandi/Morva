from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_verification_receipt_history_integrity_verifier_m4_51 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrity,
    IndependentHistoricalVerificationReceiptHistoryIntegrityError,
    independently_verify_historical_independent_verification_receipt_history_integrity,
)
from .models import Base


class IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
    ValueError
):
    """Raised when an M4.52 verification receipt is invalid or tampered."""


class IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord(Base):
    """Append-only persisted result of independent M4.51 verification."""

    __tablename__ = "independent_receipt_history_verification_m4_52"
    __table_args__ = (
        Index("ix_m4_52_verification_snapshot_id", "snapshot_id"),
        Index("ix_m4_52_verification_valid", "valid"),
        Index("ix_m4_52_verification_created_at", "created_at"),
        Index(
            "ix_m4_52_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_independent_verification_receipt_history_m4_50.id"),
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
    ) -> IndependentHistoricalVerificationReceiptHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.52 blockers payload is invalid"
            ) from exc
        try:
            return IndependentHistoricalVerificationReceiptHistoryIntegrity(
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
            IndependentHistoricalVerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "persisted M4.52 independent verification receipt is structurally invalid"
            ) from exc


class IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository:
    """Append-only M4.52 persistence with independent source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        snapshot_id: UUID,
        recorded_by: str,
    ) -> IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord:
        actor = recorded_by.strip()
        if not actor:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "recorded_by is required"
            )

        snapshot = self._get_snapshot(snapshot_id)
        independent = self._reconstruct(snapshot)
        existing = self.session.scalar(
            select(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord(
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
        list[IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
        )
        if snapshot_id is not None:
            query = query.where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.snapshot_id
                == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.valid
                == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.created_at.desc(),
                    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.id.desc(),
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
    ) -> IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord:
        record = self.session.get(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
            verification_receipt_id,
        )
        if record is None:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.52 independent verification receipt not found"
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        expected = self._reconstruct(snapshot)
        if stored != expected:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.52 independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(
        self,
        snapshot_id: UUID,
    ) -> HistoricalIndependentVerificationReceiptHistoryIntegrityRecord:
        snapshot = self.session.get(
            HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.50 history integrity snapshot not found"
            )
        source_repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            self.session
        )
        try:
            source_repository.verify(snapshot.id)
        except HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                "M4.50 source snapshot failed verification"
            ) from exc
        return snapshot

    def _reconstruct(
        self,
        snapshot: HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    ) -> IndependentHistoricalVerificationReceiptHistoryIntegrity:
        source_query = (
            select(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            )
            .where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(self.session.scalars(source_query).all())
        source_repository = (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
                self.session
            )
        )
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            return (
                independently_verify_historical_independent_verification_receipt_history_integrity(
                    snapshot=snapshot,
                    source_records=source_records,
                )
            )
        except (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            IndependentHistoricalVerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError(
                f"M4.51 independent reconstruction failed: {exc}"
            ) from exc
