from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column

from morva.payroll.payment_exception_ledger import PaymentExceptionEvent, record_resolution, verify_event
from morva.payroll.payment_exceptions import PaymentException, PaymentExceptionStatus, PaymentExceptionType
from .models import Base


class PaymentExceptionRecord(Base):
    """Current persisted state for a provider-neutral payment exception."""

    __tablename__ = "payment_exceptions"
    __table_args__ = (UniqueConstraint("payment_item_id", "exception_type", "status", name="uq_payment_exception_item_type_status"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exception_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    payment_item_id: Mapped[str] = mapped_column(String(100), index=True)
    exception_type: Mapped[str] = mapped_column(String(40), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default=PaymentExceptionStatus.OPEN.value, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class PaymentExceptionEventRecord(Base):
    """Append-only resolution evidence; application code never updates this table."""

    __tablename__ = "payment_exception_events"
    __table_args__ = (UniqueConstraint("exception_id", "idempotency_key", name="uq_payment_exception_event_idempotency"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    exception_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_ref: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(150), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)


class PaymentExceptionRepository:
    """Transactional persistence boundary for M3.30 payment exceptions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, exception: PaymentException, *, opened_at: datetime | None = None) -> PaymentExceptionRecord:
        if not exception.exception_id.strip() or not exception.payment_item_id.strip() or not exception.reason.strip():
            raise ValueError("exception id, payment item id and reason are required")
        record = PaymentExceptionRecord(
            exception_id=exception.exception_id.strip(),
            payment_item_id=exception.payment_item_id.strip(),
            exception_type=exception.exception_type.value,
            reason=exception.reason.strip(),
            status=exception.status.value,
            opened_at=opened_at or datetime.now(timezone.utc),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def resolve(
        self,
        exception_id: str,
        *,
        actor: str,
        reason: str,
        evidence_ref: str,
        idempotency_key: str,
        occurred_at: datetime | None = None,
    ) -> PaymentExceptionEventRecord:
        """Resolve an open exception and append one immutable resolution event."""
        exception_id = exception_id.strip()
        idempotency_key = idempotency_key.strip()
        if not exception_id or not idempotency_key:
            raise ValueError("exception id and idempotency key are required")

        existing_event = (
            self.session.query(PaymentExceptionEventRecord)
            .filter(
                PaymentExceptionEventRecord.exception_id == exception_id,
                PaymentExceptionEventRecord.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        if existing_event is not None:
            return existing_event

        record = (
            self.session.query(PaymentExceptionRecord)
            .filter(PaymentExceptionRecord.exception_id == exception_id)
            .with_for_update()
            .one_or_none()
        )
        if record is None:
            raise KeyError(f"payment exception not found: {exception_id}")

        domain_exception = PaymentException(
            exception_id=record.exception_id,
            payment_item_id=record.payment_item_id,
            exception_type=PaymentExceptionType(record.exception_type),
            reason=record.reason,
            status=PaymentExceptionStatus(record.status),
            resolution_actor=record.resolution_actor,
            resolution_reason=record.resolution_reason,
            evidence_ref=record.evidence_ref,
        )
        event: PaymentExceptionEvent = record_resolution(
            domain_exception,
            actor=actor,
            reason=reason,
            evidence_ref=evidence_ref,
            occurred_at=occurred_at,
        )
        if not verify_event(event):
            raise ValueError("resolution event fingerprint verification failed")

        event_record = PaymentExceptionEventRecord(
            exception_id=event.exception_id,
            status=event.status.value,
            actor=event.actor,
            reason=event.reason,
            evidence_ref=event.evidence_ref,
            occurred_at=event.occurred_at,
            idempotency_key=idempotency_key,
            fingerprint=event.fingerprint,
        )
        self.session.add(event_record)
        record.status = PaymentExceptionStatus.RESOLVED.value
        record.resolved_at = event.occurred_at
        record.resolution_actor = event.actor
        record.resolution_reason = event.reason
        record.evidence_ref = event.evidence_ref
        record.resolution_fingerprint = event.fingerprint
        self.session.flush()
        return event_record

    def list_open(self, *, payment_item_id: str | None = None) -> list[PaymentExceptionRecord]:
        query = self.session.query(PaymentExceptionRecord).filter(
            PaymentExceptionRecord.status != PaymentExceptionStatus.RESOLVED.value
        )
        if payment_item_id is not None:
            query = query.filter(PaymentExceptionRecord.payment_item_id == payment_item_id.strip())
        return query.order_by(PaymentExceptionRecord.opened_at.asc()).all()

    def release_is_allowed(self, *, payment_item_id: str | None = None) -> bool:
        return not self.list_open(payment_item_id=payment_item_id)
