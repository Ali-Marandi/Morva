from decimal import Decimal

from hypothesis import given, strategies as st

from morva.payroll import PayrollCalculator, PayrollLine


@st.composite
def decimal_amounts(draw):
    values = draw(st.lists(st.integers(min_value=0, max_value=10_000_000), min_size=1, max_size=20))
    return [Decimal(value) for value in values]


@given(earnings=decimal_amounts(), deductions=decimal_amounts())
def test_payroll_result_preserves_decimal_money_invariants(earnings, deductions) -> None:
    earning_lines = [
        PayrollLine(
            code=f"E{i}",
            title=f"earning {i}",
            amount=amount,
            kind="earning",
            taxable=False,
            pensionable=False,
            insurable=False,
            rule_code=f"E{i}",
            explanation="property test",
        )
        for i, amount in enumerate(earnings)
    ]
    deduction_lines = [
        PayrollLine(
            code=f"D{i}",
            title=f"deduction {i}",
            amount=amount,
            kind="deduction",
            taxable=False,
            pensionable=False,
            insurable=False,
            rule_code=f"D{i}",
            explanation="property test",
        )
        for i, amount in enumerate(deductions)
    ]

    result = PayrollCalculator().calculate(
        employee_no="PROPERTY",
        period="1405-05",
        ruleset_version="property-1",
        lines=[*earning_lines, *deduction_lines],
    ).result

    expected_gross = sum(earnings, Decimal("0"))
    expected_deductions = sum(deductions, Decimal("0"))
    assert result.gross == expected_gross
    assert result.deductions == expected_deductions
    assert result.net == expected_gross - expected_deductions
    assert all(isinstance(line.amount, Decimal) for line in result.lines)
