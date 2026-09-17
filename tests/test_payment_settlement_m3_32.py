from morva.payroll.payment_settlement import (
    PaymentBatch,
    SettlementBlockedError,
    assert_batch_release_is_allowed,
    blocked_payment_items,
    evaluate_batch_release,
)


def test_batch_is_allowed_when_all_items_are_clear() -> None:
    batch = PaymentBatch("batch-1", ("item-1", "item-2"))
    decision = evaluate_batch_release(batch, release_is_allowed=lambda item_id: True)
    assert decision.allowed is True
    assert decision.blocked_item_ids == ()
    assert decision.reason == "no unresolved payment exceptions"


def test_batch_is_blocked_when_any_item_has_open_exception() -> None:
    batch = PaymentBatch("batch-2", ("item-1", "item-2", "item-3"))
    decision = evaluate_batch_release(
        batch,
        release_is_allowed=lambda item_id: item_id != "item-2",
    )
    assert decision.allowed is False
    assert decision.blocked_item_ids == ("item-2",)


def test_assertion_fails_closed_and_does_not_call_provider() -> None:
    batch = PaymentBatch("batch-3", ("item-9",))
    try:
        assert_batch_release_is_allowed(batch, release_is_allowed=lambda _: False)
    except SettlementBlockedError as exc:
        assert "batch-3" in str(exc)
        assert "item-9" in str(exc)
    else:
        raise AssertionError("expected settlement to be blocked")


def test_blocked_item_helper_preserves_order_and_ignores_empty_ids() -> None:
    blocked = blocked_payment_items(
        (" item-2 ", "", "item-1", "item-3"),
        release_is_allowed=lambda item_id: item_id == "item-1",
    )
    assert blocked == ("item-2", "item-3")


def test_payment_batch_rejects_duplicate_items() -> None:
    try:
        PaymentBatch("batch-4", ("item-1", "item-1"))
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("expected duplicate items to be rejected")
