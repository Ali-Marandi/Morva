from decimal import Decimal

from morva.payroll.reconciliation_engine import reconcile_population
from morva.payroll.snapshot import EffectiveOrder, PayrollSnapshot


def _snapshot() -> PayrollSnapshot:
    return PayrollSnapshot(
        employee_key="E-1",
        period="1405-05",
        employment_type="permanent",
        org_unit="U-1",
        service_region="R-1",
        work_days="31",
        gross=Decimal("1200"),
        deductions=Decimal("100"),
        net=Decimal("1100"),
        employer_commitments=Decimal("0"),
        components={"BASE": Decimal("1000"), "ALLOW": Decimal("200")},
        deduction_components={"TAX": Decimal("60"), "PENSION": Decimal("40")},
        latest_order=EffectiveOrder("O-1", "employment", "1405/01/01", "1405/01/01", None, None, "active", Decimal("0")),
        loan_installment_total=Decimal("0"),
        loan_count=0,
        supplementary=None,
        health=None,
        social=None,
    )


def test_reconcile_population_compares_earnings_and_deductions():
    result = reconcile_population(
        [_snapshot()],
        {"E-1": {"BASE": Decimal("1000"), "ALLOW": Decimal("210")}},
        {"E-1": {"TAX": Decimal("60"), "PENSION": Decimal("50")}},
    )

    assert result.gross_delta == Decimal("10")
    assert result.deduction_delta == Decimal("10")
    assert result.net_delta == Decimal("0")
    assert result.matched_employees == 0
    assert result.by_classification() == {"MATCH": 2, "VALUE_DELTA": 2}


def test_reconcile_population_flags_missing_and_new_components():
    result = reconcile_population(
        [_snapshot()],
        {"E-1": {"BASE": Decimal("1000"), "NEW": Decimal("25")}},
        {"E-1": {"TAX": Decimal("60")}},
    )

    assert result.by_classification() == {
        "MATCH": 2,
        "MISSING_COMPONENT": 2,
        "NEW_COMPONENT": 1,
    }
