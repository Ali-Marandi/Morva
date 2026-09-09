from datetime import date
from decimal import Decimal

from morva.rules.engine import RuleDefinition, RuleEngine, RuleContext
from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS


REQUIRED_COMPONENTS = {
    "TAX",
    "PENSION",
    "INSURANCE",
    "LOAN",
    "COURT_ORDER",
}


def _definitions() -> list[RuleDefinition]:
    return [
        RuleDefinition(
            code=code,
            title=f"Synthetic {code} regression rule",
            effective_from=date(2026, 1, 1),
            expression={"op": "value", "name": "amount"},
            legal_reference=f"synthetic:{code}",
        )
        for code in sorted(REQUIRED_COMPONENTS)
    ]


def test_required_components_have_engine_regression_rules() -> None:
    engine = RuleEngine(_definitions())
    assert REQUIRED_COMPONENTS <= set(REQUIRED_1405_COMPONENTS)
    for code in REQUIRED_COMPONENTS:
        result = engine.calculate(
            code,
            RuleContext(date(2026, 1, 1), {"amount": Decimal("123.45")}),
        )
        assert result.code == code
        assert result.amount == Decimal("123.45")
        assert result.legal_reference == f"synthetic:{code}"


def test_engine_result_is_deterministic_for_same_input() -> None:
    engine = RuleEngine(_definitions())
    context = RuleContext(date(2026, 1, 1), {"amount": Decimal("42.00")})

    first = engine.calculate("TAX", context)
    second = engine.calculate("TAX", context)

    assert first == second


def test_unknown_component_fails_closed() -> None:
    engine = RuleEngine(_definitions())

    try:
        engine.calculate("UNKNOWN_COMPONENT", RuleContext(date(2026, 1, 1), {"amount": Decimal("1")}))
    except LookupError as exc:
        assert "UNKNOWN_COMPONENT" in str(exc)
    else:
        raise AssertionError("unknown components must fail closed")


def test_negative_result_fails_closed() -> None:
    engine = RuleEngine(
        [
            RuleDefinition(
                code="LOAN",
                title="Synthetic loan regression rule",
                effective_from=date(2026, 1, 1),
                expression={"op": "sub", "args":[{"op":"const","value":"0"},{"op":"value","name":"amount"}]},
            )
        ]
    )

    try:
        engine.calculate("LOAN", RuleContext(date(2026, 1, 1), {"amount": Decimal("10")}))
    except ValueError as exc:
        assert "negative amount" in str(exc)
    else:
        raise AssertionError("negative calculation results must be rejected")
