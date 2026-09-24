from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
    IndependentHistoricalFreshnessReceiptVerificationRecord,
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from morva.runtime.independent_historical_freshness_verification_history_integrity_verifier_m4_48 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrity,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
    verify_historical_freshness_verification_history_integrity,
)
from .models import Base


class IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
    ValueError
):
    """Raised when an M4.48 independent history-integrity verification is invalid."""


class IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord(Base):
    """Append-only persisted independent verification of an M4.47 snapshot."""

    __tablename__ = (
        "independent_historical_freshness_verification_history_integrity_m4_48"
    )
    __table_args__ = (
        Index("ix_m4_48_history_integrity_snapshot_id", "snapshot_id"),
        Index("ix_m4_48_history_integrity_valid", "valid"),
        Index("ix_m4_48_history_integrity_created_at", "created_at"),
        Index(
            "ix_m4_48_history_integrity_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("historical_freshness_verification_history_integrity_m4_47.id"),
        nullable=False,
    )
    persisted_history_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    reconstructed_history_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    persisted_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    persisted_record_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_record_count: Mapped[int] = mapped_column(nullable=False)
    persisted_valid_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_valid_count: Mapped[int] = mapped_column(nullable=False)
    persisted_chain_valid_count: Mapped[int] = mapped_column(nullable=False)
    reconstructed_chain_valid_count: Mapped[int] = mapped_column(nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    verified_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(
        self,
    ) -> IndependentHistoricalFreshnessVerificationHistoryIntegrity:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "persisted M4.48 blockers payload is invalid"
                )
            ) from exc
        try:
            return IndependentHistoricalFreshnessVerificationHistoryIntegrity(
                snapshot_id=self.snapshot_id,
                persisted_history_fingerprint=self.persisted_history_fingerprint,
                reconstructed_history_fingerprint=self.reconstructed_history_fingerprint,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                persisted_record_count=self.persisted_record_count,
                reconstructed_record_count=self.reconstructed_record_count,
                persisted_valid_count=self.persisted_valid_count,
                reconstructed_valid_count=self.reconstructed_valid_count,
                persisted_chain_valid_count=self.persisted_chain_valid_count,
                reconstructed_chain_valid_count=self.reconstructed_chain_valid_count,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
        ) as exc:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "persisted M4.48 verification is structurally invalid"
                )
            ) from exc


class IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRepository:
    """Append-only M4.48 persistence with point-in-time re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        snapshot_id: UUID,
        verified_by: str,
    ) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord:
        actor = verified_by.strip()
        if not actor:
            raise IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                "verified_by is required"
            )

        snapshot = self._get_snapshot(snapshot_id)
        source_records = self._source_records(snapshot)
        verification = verify_historical_freshness_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        existing = self.session.scalar(
            select(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord
            ).where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.verification_fingerprint
                == verification.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.verified_by != actor:
                raise (
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                        "verification fingerprint is already recorded by a different actor"
                    )
                )
            self.verify(existing.id)
            return existing

        record = (
            IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord(
                snapshot_id=verification.snapshot_id,
                persisted_history_fingerprint=verification.persisted_history_fingerprint,
                reconstructed_history_fingerprint=verification.reconstructed_history_fingerprint,
                persisted_fingerprint=verification.persisted_fingerprint,
                reconstructed_fingerprint=verification.reconstructed_fingerprint,
                persisted_record_count=verification.persisted_record_count,
                reconstructed_record_count=verification.reconstructed_record_count,
                persisted_valid_count=verification.persisted_valid_count,
                reconstructed_valid_count=verification.reconstructed_valid_count,
                persisted_chain_valid_count=verification.persisted_chain_valid_count,
                reconstructed_chain_valid_count=verification.reconstructed_chain_valid_count,
                valid=verification.valid,
                blockers_json=json.dumps(
                    list(verification.blockers),
                    ensure_ascii=True,
                    separators=(",", ":"),
                ),
                verification_fingerprint=verification.verification_fingerprint,
                verified_by=actor,
            )
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
        list[
            IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord
        ],
        bool,
    ]:
        if limit < 1 or limit > 100:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "limit must be between 1 and 100"
                )
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "before_created_at must be timezone-aware"
                )
            )

        query = select(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord
        )
        if snapshot_id is not None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.snapshot_id
                == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.valid
                == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.created_at
                    < before_created_at
                )
                |
                (
                    (
                        IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.created_at
                        == before_created_at
                    )
                    & (
                        IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.id
                        < before_id
                    )
                )
            )

        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.created_at.desc(),
                    IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord.id.desc(),
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
        verification_id: UUID,
    ) -> IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord:
        record = self.session.get(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationRecord,
            verification_id,
        )
        if record is None:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "M4.48 independent history-integrity verification not found"
                )
            )
        stored = record.to_verification()
        snapshot = self._get_snapshot(record.snapshot_id)
        expected = verify_historical_freshness_verification_history_integrity(
            snapshot=snapshot,
            source_records=self._source_records(snapshot),
        )
        if stored != expected:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "M4.48 verification result differs from independent reconstruction"
                )
            )
        return record

    def _get_snapshot(
        self,
        snapshot_id: UUID,
    ) -> HistoricalFreshnessVerificationHistoryIntegrityRecord:
        snapshot = self.session.get(
            HistoricalFreshnessVerificationHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "M4.47 history-integrity snapshot not found"
                )
            )
        try:
            snapshot.to_integrity()
        except HistoricalFreshnessVerificationHistoryIntegrityPersistenceError as exc:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    "M4.47 history-integrity snapshot is structurally invalid"
                )
            ) from exc
        return snapshot

    def _source_records(
        self,
        snapshot: HistoricalFreshnessVerificationHistoryIntegrityRecord,
    ) -> list[IndependentHistoricalFreshnessReceiptVerificationRecord]:
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(
            self.session
        )
        records = list(
            self.session.scalars(
                select(IndependentHistoricalFreshnessReceiptVerificationRecord)
                .where(
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at
                    < snapshot.created_at
                )
                .order_by(
                    IndependentHistoricalFreshnessReceiptVerificationRecord.created_at.asc(),
                    IndependentHistoricalFreshnessReceiptVerificationRecord.id.asc(),
                )
            ).all()
        )
        try:
            for record in records:
                repository.verify(record.id)
        except IndependentHistoricalFreshnessReceiptVerificationPersistenceError as exc:
            raise (
                IndependentHistoricalFreshnessVerificationHistoryIntegrityVerificationPersistenceError(
                    f"M4.47 source history verification failed: {exc}"
                )
            ) from exc
        return records
