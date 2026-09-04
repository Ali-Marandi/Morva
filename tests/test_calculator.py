from dataclasses import replace
from datetime import date
from decimal import Decimal

import morva.payroll.policies as policies_module
from morva.payroll import PayrollCalculator, PayrollLine, calculate_retroactive, demo_iranian_policy_pack


def test_calculator_is_deterministic():
    lines = (
        PayrollLine("BASE", "Base", Decimal("100000000"), "earning", taxable=True, pensionable=True),
        PayrollLine("ALLOW", "Allowance", Decimal("20000000"), "earning", taxable=True),
    )
    calculator = PayrollCalculator()
    first = calculator.calculate(employee_no="E1", period=date(2026, 9, 1), ruleset_version="r1", lines=lines)
    second = calculator.calculate(employee_no="E1", period=date(2026, 9, 1), ruleset_version="r1", lines=lines)
    assert first.fingerprint == second.fingerprint
    assert first.result.gross == Decimal("120000000")


def test_demo_policy_adds_traceable_tax_and_contribution_lines(monkeypatch):
    monkeypatch.setattr(policies_module, "settings", replace(policies_module.settings, allow_demo_policies=True))
    tax, contributions = demo_iranian_policy_pack()
    calculation = PayrollCalculator().calculate(
        employee_no="E2",
        period=date(2026, 9, 1),
        ruleset_version="demo",
        lines=(PayrollLine("BASE", "Base", Decimal("500000000"), "earning", taxable=True, pensionable=True),),
        tax_policy=tax,
        contribution_policies=contributions,
    )
    assert any(line.code == "TAX" for line in calculation.result.lines)
    assert any(line.code == "PENSION_DEMO" for line in calculation.result.lines)
    assert calculation.fingerprint


def test_retroactive_difference_is_sum_of_monthly_changes():
    result = calculate_retroactive(
        {"2026-01": Decimal("100"), "2026-02": Decimal("120")},
        {"2026-01": Decimal("130"), "2026-02": Decimal("125"), "2026-03": Decimal("10")},
    )
    assert result.net_difference == Decimal("45")
