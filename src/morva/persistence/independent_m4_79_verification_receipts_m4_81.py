from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
)
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    IndependentM477VerificationReceiptM480Error,
    IndependentM477VerificationReceiptM480,
    independently_verify_m4_79_verification_receipt,
)
from .models import Base


class IndependentM479VerificationReceiptM481PersistenceError(ValueError):
    """Raised when an M4.81 verification receipt is invalid or tampered."""


class IndependentM479VerificationReceiptM481Record(Base):
    """Append-only persisted result of independent M4.80 verification."""

    __tablename__ = "independent_m4_79_verification_receipts_m4_81"
    __table_args__ = (
        Index("ix_m4_81_verification_receipt_id", "verification_receipt_id"),
        Index("ix_m4_81_verification_valid", "valid"),
        Index("ix_m4_81_verification_created_at", "created_at"),
        Index(
            "ix_m4_81_verification_fingerprint",
            "verification_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    verification_receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("independent_m4_77_verification_receipts_m4_79.id"),
        nullable=False,
    )
    persisted_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    reconstructed_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    persisted_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    reconstructed_snapshot_id: Mapped[UUID] = mapped_column(nullable=False)
    persisted_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reconstructed_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blockers_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_verification(self) -> IndependentM477VerificationReceiptM480:
        try:
            blockers = tuple(json.loads(self.blockers_json))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "persisted M4.81 blockers payload is invalid"
            ) from exc
        try:
            return IndependentM477VerificationReceiptM480(
                verification_receipt_id=self.verification_receipt_id,
                persisted_fingerprint=self.persisted_fingerprint,
                reconstructed_fingerprint=self.reconstructed_fingerprint,
                persisted_snapshot_id=self.persisted_snapshot_id,
                reconstructed_snapshot_id=self.reconstructed_snapshot_id,
                persisted_valid=self.persisted_valid,
                reconstructed_valid=self.reconstructed_valid,
                valid=self.valid,
                blockers=blockers,
                verification_fingerprint=self.verification_fingerprint,
            )
        except (
            TypeError,
            ValueError,
            IndependentM477VerificationReceiptM480Error,
        ) as exc:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "persisted M4.81 verification receipt is structurally invalid"
            ) from exc


class IndependentM479VerificationReceiptM481Repository:
    """Append-only M4.81 persistence with independent source re-verification."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, *, verification_receipt_id: UUID, recorded_by: str):
        actor = recorded_by.strip()
        if not actor:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "recorded_by is required"
            )
        receipt = self._get_receipt(verification_receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        independent = self._reconstruct(receipt, snapshot)
        existing = self.session.scalar(
            select(IndependentM479VerificationReceiptM481Record).where(
                IndependentM479VerificationReceiptM481Record.verification_fingerprint
                == independent.verification_fingerprint
            )
        )
        if existing is not None:
            if existing.recorded_by != actor:
                raise IndependentM479VerificationReceiptM481PersistenceError(
                    "verification fingerprint is already recorded by a different actor"
                )
            self.verify(existing.id)
            return existing

        record = IndependentM479VerificationReceiptM481Record(
            verification_receipt_id=independent.verification_receipt_id,
            persisted_fingerprint=independent.persisted_fingerprint,
            reconstructed_fingerprint=independent.reconstructed_fingerprint,
            persisted_snapshot_id=independent.persisted_snapshot_id,
            reconstructed_snapshot_id=independent.reconstructed_snapshot_id,
            persisted_valid=independent.persisted_valid,
            reconstructed_valid=independent.reconstructed_valid,
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
        verification_receipt_id: UUID | None = None,
        valid: bool | None = None,
        before_created_at: datetime | None = None,
        before_id: UUID | None = None,
        limit: int = 50,
    ):
        if limit < 1 or limit > 100:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "limit must be between 1 and 100"
            )
        if before_created_at is not None and before_created_at.tzinfo is None:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "before_created_at must be timezone-aware"
            )
        query = select(IndependentM479VerificationReceiptM481Record)
        if verification_receipt_id is not None:
            query = query.where(
                IndependentM479VerificationReceiptM481Record.verification_receipt_id
                == verification_receipt_id
            )
        if valid is not None:
            query = query.where(
                IndependentM479VerificationReceiptM481Record.valid == valid
            )
        if before_created_at is not None and before_id is None:
            query = query.where(
                IndependentM479VerificationReceiptM481Record.created_at
                < before_created_at
            )
        elif before_created_at is not None and before_id is not None:
            query = query.where(
                (
                    IndependentM479VerificationReceiptM481Record.created_at
                    < before_created_at
                )
                | (
                    (
                        IndependentM479VerificationReceiptM481Record.created_at
                        == before_created_at
                    )
                    & (
                        IndependentM479VerificationReceiptM481Record.id
                        < before_id
                    )
                )
            )
        records = list(
            self.session.scalars(
                query.order_by(
                    IndependentM479VerificationReceiptM481Record.created_at.desc(),
                    IndependentM479VerificationReceiptM481Record.id.desc(),
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
            IndependentM479VerificationReceiptM481Record,
            verification_id,
        )
        if record is None:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.81 independent verification receipt not found"
            )
        stored = record.to_verification()
        receipt = self._get_receipt(record.verification_receipt_id)
        snapshot = self._get_snapshot(receipt.snapshot_id)
        expected = self._reconstruct(receipt, snapshot)
        if stored != expected:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.81 independent verification result differs from reconstruction"
            )
        return record

    def _get_receipt(self, verification_receipt_id: UUID):
        receipt = self.session.get(
            IndependentM477VerificationReceiptM479Record,
            verification_receipt_id,
        )
        if receipt is None:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.79 independent verification receipt not found"
            )
        try:
            receipt.to_verification()
        except IndependentM477VerificationReceiptM479PersistenceError as exc:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.79 source receipt is structurally invalid"
            ) from exc
        return receipt

    def _get_snapshot(self, snapshot_id: UUID):
        snapshot = self.session.get(
            HistoricalM475VerificationReceiptHistoryIntegrityRecord,
            snapshot_id,
        )
        if snapshot is None:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.77 history-integrity snapshot not found"
            )
        try:
            snapshot.to_integrity()
        except HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                "M4.77 source snapshot is structurally invalid"
            ) from exc
        return snapshot

    def _reconstruct(self, receipt, snapshot):
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
        try:
            return independently_verify_m4_79_verification_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
            )
        except (
            HistoricalM472VerificationReceiptM475PersistenceError,
            IndependentM477VerificationReceiptM480Error,
        ) as exc:
            raise IndependentM479VerificationReceiptM481PersistenceError(
                f"M4.80 independent reconstruction failed: {exc}"
            ) from exc
