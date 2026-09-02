from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import InboxMessageRecord, OutboxMessageRecord, IntegrationReceiptRecord


def enqueue(
    session: Session,
    *,
    operation: str,
    provider: str,
    correlation_id: str,
    idempotency_key: str,
    payload: dict[str, object],
) -> OutboxMessageRecord:
    existing = session.scalar(select(OutboxMessageRecord).where(OutboxMessageRecord.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    message = OutboxMessageRecord(
        id=uuid4(), operation=operation, provider=provider,
        correlation_id=correlation_id, idempotency_key=idempotency_key,
        payload=payload, status="pending", attempts=0,
    )
    session.add(message)
    session.flush()
    return message


def mark_sent(session: Session, message: OutboxMessageRecord, *, external_id: str, status: str = "accepted") -> IntegrationReceiptRecord:
    message.status = "sent"
    message.sent_at = datetime.utcnow()
    receipt = IntegrationReceiptRecord(
        id=uuid4(), provider=message.provider, operation=message.operation,
        correlation_id=message.correlation_id, idempotency_key=message.idempotency_key,
        external_id=external_id, status=status, payload={},
    )
    session.add(receipt)
    session.flush()
    return receipt


def record_inbox(
    session: Session,
    *,
    provider: str,
    external_id: str,
    correlation_id: str,
    payload: dict[str, object],
) -> InboxMessageRecord:
    existing = session.scalar(
        select(InboxMessageRecord).where(
            InboxMessageRecord.provider == provider,
            InboxMessageRecord.external_id == external_id,
        )
    )
    if existing is not None:
        return existing
    message = InboxMessageRecord(
        id=uuid4(), provider=provider, external_id=external_id,
        correlation_id=correlation_id, payload=payload, status="received",
    )
    session.add(message)
    session.flush()
    return message
