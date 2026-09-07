from decimal import Decimal

import pytest

from morva.payroll.three_way_reconciliation import ReconciliationMismatchError, ReconciliationSnapshot, ThreeWayReconciliation


def snapshot(*, gross: str = "120000000", deductions: str = "22800000", net: str = "97200000") -> ReconciliationSnapshot:
    return ReconciliationSnapshot(
        batch_id="BATCH-1405-01-0001",
        employee_count=1,
        gross=Decimal(gross),
        deductions=Decimal(deductions),
        net=Decimal(net),
    )


def test_three_way_reconciliation_release_gate_passes_on_exact_match() -> None:
    result = ThreeWayReconciliation(snapshot(), snapshot(), snapshot())
    assert result.matched
    result.assert_releaseable()


def test_three_way_reconciliation_is_a_hard_stop_on_amount_mismatch() -> None:
    result = ThreeWayReconciliation(snapshot(), snapshot(net="97200001"), snapshot())
    assert not result.matched
    with pytest.raises(ReconciliationMismatchError, match="accounting.net"):
        result.assert_releaseable()


def test_three_way_reconciliation_stops_on_batch_mismatch() -> None:
    bad_payment = ReconciliationSnapshot(
        batch_id="OTHER-BATCH",
        employee_count=1,
        gross=Decimal("120000000"),
        deductions=Decimal("22800000"),
        net=Decimal("97200000"),
    )
    result = ThreeWayReconciliation(snapshot(), snapshot(), bad_payment)
    with pytest.raises(ReconciliationMismatchError, match="payment.batch_id"):
        result.assert_releaseable()
