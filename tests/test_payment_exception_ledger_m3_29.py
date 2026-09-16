from datetime import datetime, timezone

import pytest

from morva.payroll.payment_exception_ledger import record_resolution, verify_event
from morva.payroll.payment_exceptions import PaymentException, PaymentExceptionStatus, PaymentExceptionType


def open_exception() -> PaymentException:
    return PaymentException(
        exception_id="EX-001",
        payment_item_id="PAY-001",
        exception_type=PaymentExceptionType.RETURN,
        reason="provider returned the payment",
    )


def test_record_resolution_requires_explicit_evidence() -> None:
    with pytest.raises(ValueError, match="resolution actor, reason and evidence"):
        record_resolution(open_exception(), actor="operator", reason="resolved", evidence_ref="")


def test_record_resolution_is_deterministic_for_a_fixed_timestamp() -> None:
    occurred_at = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    event = record_resolution(
        open_exception(),
        actor="operator-1",
        reason="bank receipt reviewed",
        evidence_ref="receipt:abc",
        occurred_at=occurred_at,
    )
    assert event.status is PaymentExceptionStatus.RESOLVED
    assert event.fingerprint
    assert verify_event(event)


def test_tampered_resolution_event_fails_verification() -> None:
    occurred_at = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
    event = record_resolution(
        open_exception(),
        actor="operator-1",
        reason="bank receipt reviewed",
        evidence_ref="receipt:abc",
        occurred_at=occurred_at,
    )
    object.__setattr__(event, "reason", "tampered")
    assert not verify_event(event)


def test_closed_exception_cannot_generate_second_resolution_event() -> None:
    exception = PaymentException(
        exception_id="EX-002",
        payment_item_id="PAY-002",
        exception_type=PaymentExceptionType.REVERSAL,
        reason="already resolved",
        status=PaymentExceptionStatus.RESOLVED,
    )
    with pytest.raises(ValueError, match="only open payment exceptions"):
        record_resolution(
            exception,
            actor="operator-1",
            reason="second resolution",
            evidence_ref="receipt:def",
        )
