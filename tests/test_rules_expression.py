from datetime import date
from decimal import Decimal

from morva.rules import RuleContext, RuleDefinition, RuleEngine


def test_expression_rule_is_effective_dated_and_explainable():
    engine = RuleEngine([
        RuleDefinition(
            code="PERCENT",
            title="Percentage",
            effective_from=date(2026, 1, 1),
            expression={
                "op": "mul",
                "args": [
                    {"op": "value", "name": "base"},
                    {"op": "value", "name": "rate"},
                ],
            },
            legal_reference="TEST-LAW",
        )
    ])
    result = engine.calculate("PERCENT", RuleContext(date(2026, 9, 1), {"base": Decimal("200"), "rate": Decimal("0.2")}))
    assert result.amount == Decimal("40.0")
    assert result.legal_reference == "TEST-LAW"


def test_expression_rejects_unknown_operations():
    engine = RuleEngine([
        RuleDefinition(
            code="BAD",
            title="Bad",
            effective_from=date(2026, 1, 1),
            expression={"op": "sqrt", "args": [{"op": "value", "name": "x"}]},
        )
    ])
    try:
        engine.calculate("BAD", RuleContext(date(2026, 9, 1), {"x": Decimal("4")}))
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unknown rule operation should fail")
