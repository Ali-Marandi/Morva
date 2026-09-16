"""Append-only payment exception resolution ledger foundation for M3.29."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

from .payment_exceptions import PaymentException, PaymentExceptionStatus


@dataclass(frozen=True)
class PaymentExceptionEvent:
    exception_id: str
    status: PaymentExceptionStatus
    actor: str
    reason: str
    evidence_ref: str
    occurred_at: datetime
    fingerprint: str


def _fingerprint(*, exception_id: str, status: PaymentExceptionStatus, actor: str, reason: str, evidence_ref: str, occurred_at: datetime) -> str:
    payload = "|".join((exception_id, status.value, actor, reason, evidence_ref, occurred_at.astimezone(timezone.utc).isoformat()))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_resolution(exception: PaymentException, *, actor: str, reason: str, evidence_ref: str, occurred_at: datetime | None = None) -> PaymentExceptionEvent:
    """Create an immutable resolution event for a valid open exception."""
    if exception.status is not PaymentExceptionStatus.OPEN:
        raise ValueError("only open payment exceptions can be resolved")
    if not actor.strip() or not reason.strip() or not evidence_ref.strip():
        raise ValueError("resolution actor, reason and evidence are required")
    timestamp = occurred_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("occurred_at must be timezone-aware")
    actor = actor.strip()
    reason = reason.strip()
    evidence_ref = evidence_ref.strip()
    return PaymentExceptionEvent(
        exception_id=exception.exception_id,
        status=PaymentExceptionStatus.RESOLVED,
        actor=actor,
        reason=reason,
        evidence_ref=evidence_ref,
        occurred_at=timestamp,
        fingerprint=_fingerprint(exception_id=exception.exception_id, status=PaymentExceptionStatus.RESOLVED, actor=actor, reason=reason, evidence_ref=evidence_ref, occurred_at=timestamp),
    )


def verify_event(event: PaymentExceptionEvent) -> bool:
    """Verify the deterministic event fingerprint."""
    return event.fingerprint == _fingerprint(
        exception_id=event.exception_id,
        status=event.status,
        actor=event.actor,
        reason=event.reason,
        evidence_ref=event.evidence_ref,
        occurred_at=event.occurred_at,
    )
