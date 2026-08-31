from datetime import date
from decimal import Decimal

import pytest

from morva.domain.models import Employee, EmploymentType, Money
from morva.payroll.models import PayrollLine
from morva.payroll.service import PayrollService
from morva.rules.catalog import demo_ruleset
from morva.rules.engine import RuleContext, RuleDefinition, RuleEngine, RuleNotFoundError


def test_employee_model_has_explicit_status():
    employee = Employee(
        national_id="0012345678",
        first_name="A",
        last_name="B",
        employee_no="E-1",
        employment_type=EmploymentType.PERMANENT,
        organization_unit_id="U-1",
        position_id="P-1",
    )
    assert employee.status.value == "active"


def test_money_is_decimal_and_non_negative():
    assert Money(amount=Decimal("100.25")).amount == Decimal("100.25")
    with pytest.raises(ValueError):
        Money(amount=Decimal("-1"))


def test_effective_dated_rule_resolution_prefers_newest_active_rule():
    engine = RuleEngine(
        [
            RuleDefinition("X", "old", date(2026, 1, 1), formula=lambda _: Decimal("10")),
            RuleDefinition("X", "new", date(2026, 7, 1), formula=lambda _: Decimal("20")),
        ]
    )
    result = engine.calculate("X", RuleContext(date(2026, 9, 1), {}))
    assert result.amount == Decimal("20")
    assert "new" in result.explanation


def test_rule_engine_rejects_missing_effective_rule():
    engine = RuleEngine([])
    with pytest.raises(RuleNotFoundError):
        engine.resolve("MISSING", date(2026, 1, 1))


def test_payroll_exposes_tax_and_pension_bases():
    lines = PayrollService().build_standard_lines(
        base_salary=Decimal("1000"),
        allowances=[("A", "Allowance", Decimal("200"), True, False, True)],
        deductions=[("D", "Deduction", Decimal("100"), False)],
    )
    result = PayrollService().calculate(
        employee_no="E-1",
        period=date(2026, 9, 1),
        lines=lines,
        ruleset_version="dev-1",
    )
    assert result.gross == Decimal("1200")
    assert result.taxable_gross == Decimal("1200")
    assert result.pensionable_gross == Decimal("1000")
    assert result.insurable_gross == Decimal("1200")
    assert result.deductions == Decimal("100")
    assert result.net == Decimal("1100")
    assert result.ruleset_version == "dev-1"


def test_demo_ruleset_percentage_calculation():
    result = demo_ruleset().calculate(
        "ALLOWANCE_PERCENT",
        RuleContext(date(2026, 9, 1), {"base": Decimal("1000"), "rate": Decimal("0.15")}),
    )
    assert result.amount == Decimal("150.00")
