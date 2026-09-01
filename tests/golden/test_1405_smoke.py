from decimal import Decimal
from datetime import date

from morva.payroll.calculator import PayrollCalculator
from morva.payroll.models import PayrollLine
from morva.payroll.policies import TaxBracket, TaxPolicy, ContributionPolicy
from morva.payroll.retro import calculate_retroactive
from morva.rank.models import Rank


def test_golden_payroll_is_deterministic():
    lines = (
        PayrollLine("BASE", "Base salary", Decimal("100000000"), "earning", taxable=True, pensionable=True, insurable=True),
        PayrollLine("RANK", "Rank", Decimal("20000000"), "earning", taxable=True, pensionable=True),
    )
    tax = TaxPolicy("golden-1405", Decimal("40000000"), (TaxBracket(Decimal("700000000"), Decimal("0.10")), TaxBracket(None, Decimal("0.20"))))
    contribution = ContributionPolicy("PENSION", Decimal("0.09"))
    calc = PayrollCalculator().calculate(employee_no="E0001", period=date(2026, 4, 1), ruleset_version="golden-1405", lines=lines, tax_policy=tax, contribution_policies=(contribution,))
    assert calc.result.gross == Decimal("120000000")
    assert calc.tax == Decimal("8000000.00")
    assert calc.contributions == Decimal("10800000.00")
    assert calc.result.net == Decimal("101200000.00")
    assert len(calc.fingerprint) == 64


def test_retro_difference_preserves_zero_and_negative_changes():
    result = calculate_retroactive({"1405-01": Decimal("100"), "1405-02": Decimal("120")}, {"1405-01": Decimal("110"), "1405-02": Decimal("115")})
    assert result.periods[0].difference == Decimal("10")
    assert result.periods[1].difference == Decimal("-5")
    assert result.net_difference == Decimal("5")


def test_rank_values_are_explicit():
    assert [r.value for r in Rank] == ["education_assistant", "instructor", "assistant_professor", "associate_professor", "professor"]
