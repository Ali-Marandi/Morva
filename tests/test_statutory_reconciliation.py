from decimal import Decimal

import pytest

from morva.integrations.statutory_funds import StatutoryFund
from morva.payroll.statutory_reconciliation import (
    StatutoryFundSettlementSnapshot,
    StatutoryReconciliationMismatch,
    assert_all_statutory_funds_reconciled,
)


def test_statutory_settlement_requires_exact_amount_match() -> None:
    snapshot = StatutoryFundSettlementSnapshot(
        fund=StatutoryFund.SOCIAL_SECURITY,
        batch_id="SS-1405-05-001",
        employee_count=1116,
        expected_total=Decimal("15492415986"),
        settled_total=Decimal("15492415986"),
    )
    assert snapshot.matched
    snapshot.assert_reconciled()


def test_statutory_settlement_mismatch_is_a_hard_stop() -> None:
    snapshot = StatutoryFundSettlementSnapshot(
        fund=StatutoryFund.CENTRAL_CIVIL_SERVANTS_PENSION,
        batch_id="P-1405-05-001",
        employee_count=100,
        expected_total=Decimal("1000"),
        settled_total=Decimal("999"),
    )
    assert not snapshot.matched
    with pytest.raises(StatutoryReconciliationMismatch, match="settlement mismatch"):
        snapshot.assert_reconciled()


def test_all_statutory_funds_reject_duplicate_provider_entries() -> None:
    snapshot = StatutoryFundSettlementSnapshot(
        fund=StatutoryFund.SOCIAL_SECURITY,
        batch_id="SS-1",
        employee_count=1,
        expected_total=Decimal("10"),
        settled_total=Decimal("10"),
    )
    with pytest.raises(StatutoryReconciliationMismatch, match="duplicate"):
        assert_all_statutory_funds_reconciled((snapshot, snapshot))
