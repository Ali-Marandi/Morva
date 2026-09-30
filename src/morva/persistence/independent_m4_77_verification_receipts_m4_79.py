from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrity,
    independently_verify_historical_m4_75_verification_receipt_history_integrity,
)
from .models import Base


class IndependentM477VerificationReceiptM479PersistenceError(ValueError):
    """Raised when an M4.79 independent-verification receipt is invalid or tampered."""


class IndependentM477VerificationReceiptM479Record(Base):
    """Append-only persisted result of independent M4.78 verification."""

    __tablename__ = "independent_m4_77_verification_receipts_m4_79"
    __table_args__ = (
        Index("ix_m4_79_verification_snapshot_id", "snapshot_id"),
        Index("ix_m4_79_verification_valid", "valid"),
        Index("ix_m4_79_verification_created_at", "created_at"),
        Index(
            "ix_m4_79_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "historical_m4_75_verification_receipt_history_integrity_m4_77.id"
        ),
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

    def to_verification(self) -> IndependentHistoricalM475VerificationReceiptHistoryIntegrity:
        try:
            raw_blockers = json.loads(self.blockers_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "persisted M4.79 blockers payload is invalid"
            ) from exc
        if (
            not isinstance(raw_blockers, list)
            or any(not isinstance(item, str) for item in raw_blockers)
        ):
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "persisted M4.79 blockers payload must be a list of strings"
            )
        blockers = tuple(raw_blockers)
        try:
            return IndependentHistoricalM475VerificationReceiptHistoryIntegrity(
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
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "persisted M4.79 independent verification receipt is structurally invalid"
            ) from exc


class IndependentM477VerificationReceiptM479Repository:
    """Append-only M4.79 persistence with source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, snapshot_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "recorded_by is required"
            )
        snapshot = self._get_snapshot(snapshot_id)
        independent = self._reconstruct(snapshot)
        existing = self.session.scalar(
            select(IndependentM477VerificationReceiptM479Record).where(
                IndependentM477VerificationReceiptM479Record.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentM477VerificationReceiptM479PersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentM477VerificationReceiptM479Record(
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
    ):
        if limit < 1 or limit > 100:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "before_created_at must be timezone-aware"
            )

        query = select(IndependentM477VerificationReceiptM479Record)
        if snapshot_id is not None:
            query = query.where(
                IndependentM477VerificationReceiptM479Record.snapshot_id == snapshot_id
            )
        if valid is not None:
            query = query.where(
                IndependentM477VerificationReceiptM479Record.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentM477VerificationReceiptM479Record.created_at < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentM477VerificationReceiptM479Record.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentM477VerificationReceiptM479Record.created_at
                        == before_created_at
                    )
                    & (
                        IndependentM477VerificationReceiptM479Record.id < before_id
                    )
                )
            )
        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentM477VerificationReceiptM479Record.created_at.desc(),
                    IndependentM477VerificationReceiptM479Record.id.desc(),
                ).limit(limit + 1)
            ).all()
        )
        has_more = len(records) > limit
        records = records[:limit]
        for record in records:
            self.verify(record.id)
        return records, has_more

    def verify(self, verification_id: UUID):
        record = self.session.get(
            IndependentM477VerificationReceiptM479Record,
            verification_id,
        )
        if record is None:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "M4.79 independent verification receipt not found"
            )
        stored = record.to_verification()
        expected = self._reconstruct(self._get_snapshot(record.snapshot_id))
        if stored != expected:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "M4.79 independent verification result differs from reconstruction"
            )
        return record

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(
            HistoricalM475VerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "M4.77 history-integrity snapshot not found"
            )
        try:
            snapshot.to_integrity()
        except HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                "M4.77 source snapshot is structurally invalid"
            ) from exc
        return snapshot

    def _reconstruct(self, snapshot):
        source_records = list(
            self.session.scalars(
                select(HistoricalM472VerificationReceiptM475Record)
                .where(
                    HistoricalM472VerificationReceiptM475Record.created_at
                    < snapshot.created_at
                )
                .order_by(
                    HistoricalM472VerificationReceiptM475Record.created_at.asc(),
                    HistoricalM472VerificationReceiptM475Record.id.asc(),
                )
            ).all()
        )
        source_repository = HistoricalM472VerificationReceiptM475Repository(self.session)
        try:
            for source_record in source_records:
                source_repository.verify(source_record.id)
            return independently_verify_historical_m4_75_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        except (
            HistoricalM472VerificationReceiptM475PersistenceError,
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
        ) as exc:
            raise IndependentM477VerificationReceiptM479PersistenceError(
                f"M4.78 independent reconstruction failed: {exc}"
            ) from exc
