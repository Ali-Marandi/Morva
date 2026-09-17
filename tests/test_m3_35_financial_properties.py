from decimal import Decimal
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from morva.payroll import PayrollCalculator, PayrollLine
from morva.payroll.policies import ContributionPolicy


@st.composite
def payroll_lines(draw: Any) -> tuple[PayrollLine, ...]:
    count = draw(st.integers(min_value=1, max_value=12))
    lines: list[PayrollLine] = []
    for index in range(count):
        amount = Decimal(draw(st.integers(min_value=0, max_value=2_000_000_000)))
        kind = draw(st.sampled_from(("earning", "deduction")))
        lines.append(
            PayrollLine(
                code=f"L{index}",
                title=f"Line {index}",
                amount=amount,
                kind=kind,
                taxable=draw(st.booleans()),
                pensionable=draw(st.booleans()),
                insurable=draw(st.booleans()),
                rule_code=f"R{index}",
            )
        )
    return tuple(lines)


def test_taxable_flag_is_enforced() -> None:
    lines = (
        PayrollLine("T", "Taxable", Decimal("100"), "earning", taxable=True),
        PayrollLine("N", "Non taxable", Decimal("900"), "earning", taxable=False),
    )
    calculation = PayrollCalculator().calculate(
        employee_no="E-M3-35", period="1405-01", ruleset_version="explicit", lines=lines
    )

    assert calculation.taxable_income == Decimal("100")


def test_pensionable_flag_is_enforced() -> None:
    policy = ContributionPolicy("PENSION_EXPLICIT", Decimal("1.00"))
    lines = (
        PayrollLine("P", "Pensionable", Decimal("100"), "earning", pensionable=True),
        PayrollLine("N", "Other", Decimal("900"), "earning", pensionable=False),
    )
    calculation = PayrollCalculator().calculate(
        employee_no="E-M3-35",
        period="1405-01",
        ruleset_version="explicit",
        lines=lines,
        contribution_policies=(policy,),
    )

    assert calculation.contributions == Decimal("100.00")


def test_net_is_subtractive() -> None:
    result = PayrollCalculator().calculate(
        employee_no="E-M3-35",
        period="1405-01",
        ruleset_version="explicit",
        lines=(
            PayrollLine("E", "Earning", Decimal("100"), "earning"),
            PayrollLine("D", "Deduction", Decimal("40"), "deduction"),
        ),
    ).result

    assert result.net == Decimal("60")


def test_contribution_ceiling_is_enforced() -> None:
    policy = ContributionPolicy("CEILING_EXPLICIT", Decimal("1.00"), Decimal("100"))

    assert policy.calculate(Decimal("1000")) == Decimal("100.00")


@given(payroll_lines())
@settings(max_examples=100, deadline=None)
def test_payroll_result_preserves_financial_conservation(lines: tuple[PayrollLine, ...]) -> None:
    calculation = PayrollCalculator().calculate(
        employee_no="M3-35",
        period="1405-01",
        ruleset_version="property",
        lines=lines,
    )
    result = calculation.result

    assert result.gross == sum(
        (line.amount for line in lines if line.kind == "earning"), Decimal(0)
    )
    assert result.deductions == sum(
        (line.amount for line in lines if line.kind == "deduction"), Decimal(0)
    )
    assert result.net == result.gross - result.deductions
    assert Decimal(0) <= result.taxable_gross <= result.gross
    assert Decimal(0) <= result.pensionable_gross <= result.gross
    assert Decimal(0) <= result.insurable_gross <= result.gross


@given(payroll_lines())
@settings(max_examples=80, deadline=None)
def test_calculation_replay_is_deterministic(lines: tuple[PayrollLine, ...]) -> None:
    calculator = PayrollCalculator()
    first = calculator.calculate(
        employee_no="E-M3-35",
        period="1405-02",
        ruleset_version="property-v1",
        lines=lines,
    )
    second = calculator.calculate(
        employee_no="E-M3-35",
        period="1405-02",
        ruleset_version="property-v1",
        lines=lines,
    )

    assert first.fingerprint == second.fingerprint
    assert first == second


@given(
    taxable_amount=st.integers(min_value=0, max_value=2_000_000_000),
    extra_amount=st.integers(min_value=0, max_value=2_000_000_000),
)
@settings(max_examples=80, deadline=None)
def test_non_taxable_earning_changes_gross_but_not_taxable_income(
    taxable_amount: int, extra_amount: int
) -> None:
    base = PayrollLine(
        "BASE", "Base", Decimal(taxable_amount), "earning", taxable=True
    )
    extra = PayrollLine(
        "EXTRA", "Extra", Decimal(extra_amount), "earning", taxable=False
    )
    calculator = PayrollCalculator()
    before = calculator.calculate(
        employee_no="E-M3-35", period="1405-03", ruleset_version="property", lines=(base,)
    )
    after = calculator.calculate(
        employee_no="E-M3-35",
        period="1405-03",
        ruleset_version="property",
        lines=(base, extra),
    )

    assert after.taxable_income == before.taxable_income
    assert after.result.gross == before.result.gross + Decimal(extra_amount)
    assert after.result.net == before.result.net + Decimal(extra_amount)


@given(
    pensionable_amount=st.integers(min_value=0, max_value=2_000_000_000),
    non_pensionable_amount=st.integers(min_value=0, max_value=2_000_000_000),
)
@settings(max_examples=80, deadline=None)
def test_contribution_base_uses_only_pensionable_earnings(
    pensionable_amount: int, non_pensionable_amount: int
) -> None:
    policy = ContributionPolicy("PENSION_PROPERTY", Decimal("1.00"))
    lines = (
        PayrollLine(
            "P", "Pensionable", Decimal(pensionable_amount), "earning", pensionable=True
        ),
        PayrollLine("N", "Other", Decimal(non_pensionable_amount), "earning"),
    )
    calculation = PayrollCalculator().calculate(
        employee_no="E-M3-35",
        period="1405-04",
        ruleset_version="property",
        lines=lines,
        contribution_policies=(policy,),
    )

    assert calculation.contributions == Decimal(pensionable_amount).quantize(Decimal("0.01"))


@given(
    gross=st.integers(min_value=0, max_value=2_000_000_000),
    rate_basis_points=st.integers(min_value=0, max_value=10_000),
    ceiling=st.one_of(st.none(), st.integers(min_value=0, max_value=2_000_000_000)),
)
@settings(max_examples=100, deadline=None)
def test_contribution_policy_honors_rate_and_ceiling(
    gross: int, rate_basis_points: int, ceiling: int | None
) -> None:
    rate = Decimal(rate_basis_points) / Decimal(10_000)
    policy = ContributionPolicy(
        "CONTRIBUTION_PROPERTY", rate, None if ceiling is None else Decimal(ceiling)
    )
    base = Decimal(gross) if ceiling is None else min(Decimal(gross), Decimal(ceiling))
    expected = (base * rate).quantize(Decimal("0.01"))

    assert policy.calculate(Decimal(gross)) == expected
