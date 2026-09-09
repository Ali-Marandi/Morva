from decimal import Decimal

import pytest

from morva.ledger.deductions import Debt, DeductionEntry, DeductionLedger, Loan


def test_loan_rejects_invalid_schedule_configuration():
    with pytest.raises(ValueError, match="loan principal must be positive"):
        Loan("L-1", "E-1", "BANK", Decimal("0"), "1405-01", 12, Decimal("100"))

    with pytest.raises(ValueError, match="installment_count must be positive"):
        Loan("L-1", "E-1", "BANK", Decimal("1000"), "1405-01", 0, Decimal("100"))

    with pytest.raises(ValueError, match="installment_amount must be positive"):
        Loan("L-1", "E-1", "BANK", Decimal("1000"), "1405-01", 12, Decimal("0"))


def test_loan_rejects_invalid_period_instead_of_returning_empty_schedule():
    with pytest.raises(ValueError, match="start_period must use YYYY-MM format"):
        Loan("L-1", "E-1", "BANK", Decimal("1000"), "1405-13", 12, Decimal("100"))


def test_loan_schedule_is_complete_and_bounded_by_principal():
    loan = Loan("L-1", "E-1", "BANK", Decimal("250"), "1405-11", 12, Decimal("100"))
    schedule = loan.schedule()

    assert [item.number for item in schedule] == [1, 2, 3]
    assert sum((item.principal for item in schedule), Decimal(0)) == Decimal("250")
    assert schedule[-1].due_period == "1406-01"


def test_deduction_entry_rejects_invalid_identity_period_amount_and_priority():
    with pytest.raises(ValueError, match="employee_no"):
        DeductionEntry("", "1405-01", "TAX", Decimal("1"), "src")

    with pytest.raises(ValueError, match="period must use YYYY-MM format"):
        DeductionEntry("E-1", "1405-00", "TAX", Decimal("1"), "src")

    with pytest.raises(ValueError, match="deduction amount cannot be negative"):
        DeductionEntry("E-1", "1405-01", "TAX", Decimal("-1"), "src")

    with pytest.raises(ValueError, match="deduction priority cannot be negative"):
        DeductionEntry("E-1", "1405-01", "TAX", Decimal("1"), "src", priority=-1)


def test_debt_rejects_negative_balance():
    with pytest.raises(ValueError, match="debt balance cannot be negative"):
        Debt("D-1", "E-1", "COURT_ORDER", Decimal("-1"), "order")


def test_deduction_ledger_order_is_deterministic():
    entries = (
        DeductionEntry("E-1", "1405-01", "LOAN-B", Decimal("2"), "src-b", priority=20),
        DeductionEntry("E-1", "1405-01", "LOAN-A", Decimal("3"), "src-a", priority=20),
        DeductionEntry("E-1", "1405-01", "TAX", Decimal("1"), "src-tax", priority=10, mandatory=True),
    )
    ledger = DeductionLedger(entries)

    assert [(x.code, x.mandatory, x.priority) for x in ledger.for_period("E-1", "1405-01")] == [
        ("TAX", True, 10),
        ("LOAN-A", False, 20),
        ("LOAN-B", False, 20),
    ]
    assert ledger.total("E-1", "1405-01") == Decimal("6")


def test_deduction_ledger_query_rejects_invalid_period():
    ledger = DeductionLedger()
    with pytest.raises(ValueError, match="period must use YYYY-MM format"):
        ledger.for_period("E-1", "bad")
