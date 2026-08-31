from decimal import Decimal
from datetime import date
from morva.domain.models import Money
from morva.payroll.service import PayrollService
from morva.rules.engine import RuleContext, RuleEngine

def test_money_defaults_to_irr():
    assert Money(amount=Decimal("10")).currency == "IRR"

def test_rule_engine_is_explainable():
    result = RuleEngine().calculate("TEST", RuleContext(date(2026, 1, 1), {}), lambda _: Decimal("12"))
    assert result.amount == Decimal("12")
    assert "TEST" in result.explanation

def test_payroll_period():
    assert PayrollService().period_key(date(2026, 9, 1)) == "2026-09"
