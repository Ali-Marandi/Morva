import pytest

from morva.payroll.payment_exceptions import (
    PaymentException,
    PaymentExceptionStatus,
    PaymentExceptionType,
    release_is_allowed,
)


def test_open_exception_blocks_release() -> None:
    exception = PaymentException(
        exception_id="ex-1",
        payment_item_id="item-1",
        exception_type=PaymentExceptionType.RETURN,
        reason="provider returned payment",
    )
    assert release_is_allowed([exception]) is False


def test_resolved_exception_allows_release() -> None:
    exception = PaymentException(
        exception_id="ex-1",
        payment_item_id="item-1",
        exception_type=PaymentExceptionType.REVERSAL,
        reason="authorized reversal",
    )
    resolved = exception.resolve(
        actor="ops-1",
        reason="verified settlement reversal",
        evidence_ref="receipt-1",
    )
    assert resolved.status is PaymentExceptionStatus.RESOLVED
    assert release_is_allowed([resolved]) is True


@pytest.mark.parametrize("field", ["actor", "reason", "evidence_ref"])
def test_resolution_requires_explicit_evidence(field: str) -> None:
    exception = PaymentException(
        exception_id="ex-1",
        payment_item_id="item-1",
        exception_type=PaymentExceptionType.UNRESOLVED_MISMATCH,
        reason="amount mismatch",
    )
    kwargs = {
        "actor": "ops-1",
        "reason": "verified mismatch",
        "evidence_ref": "receipt-1",
    }
    kwargs[field] = ""
    with pytest.raises(ValueError, match="required"):
        exception.resolve(**kwargs)


def test_non_open_exception_cannot_be_resolved_twice() -> None:
    exception = PaymentException(
        exception_id="ex-1",
        payment_item_id="item-1",
        exception_type=PaymentExceptionType.REJECT,
        reason="bank rejected payment",
    ).resolve(actor="ops-1", reason="confirmed", evidence_ref="receipt-1")

    with pytest.raises(ValueError, match="only open"):
        exception.resolve(actor="ops-2", reason="reopened", evidence_ref="receipt-2")
