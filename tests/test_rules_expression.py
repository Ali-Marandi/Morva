from datetime import date
from decimal import Decimal

import pytest

from morva.rules.engine import RuleContext, RuleDefinition, RuleEngine


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
            rule_version="1405.1",
        )
    ])
    result = engine.calculate(
        "PERCENT",
        RuleContext(date(2026, 9, 1), {"base": Decimal("200"), "rate": Decimal("0.2")}),
    )
    assert result.amount == Decimal("40.0")
    assert result.legal_reference == "TEST-LAW"
    assert result.rule_version == "1405.1"


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


def test_production_rule_requires_versioned_approved_legal_metadata():
    definition = RuleDefinition(
        code="PROD_RULE",
        title="Production candidate",
        effective_from=date(2026, 1, 1),
        expression={"op": "value", "name": "amount"},
        legal_reference="LAW-REF",
        rule_version="1405.2",
        review_status="approved",
        regression_case_ids=("REG-001",),
    )
    engine = RuleEngine([definition])
    result = engine.calculate(
        "PROD_RULE",
        RuleContext(date(2026, 9, 1), {"amount": Decimal("25")}),
        production=True,
        rule_pack_version="1405.2",
    )
    assert result.amount == Decimal("25")
    assert result.rule_version == "1405.2"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"rule_version": None}, "rule_version"),
        ({"rule_version": "1405.1"}, "rule_version"),
        ({"review_status": "review_required"}, "approved"),
        ({"legal_reference": None}, "legal_reference"),
        ({"regression_case_ids": ()}, "regression_case_ids"),
    ],
)
def test_production_rule_rejects_missing_governance_metadata(changes, message):
    values = {
        "rule_version": "1405.2",
        "review_status": "approved",
        "legal_reference": "LAW-REF",
        "regression_case_ids": ("REG-001",),
    }
    values.update(changes)
    definition = RuleDefinition(
        code="PROD_RULE",
        title="Production candidate",
        effective_from=date(2026, 1, 1),
        expression={"op": "value", "name": "amount"},
        **values,
    )
    engine = RuleEngine([definition])
    with pytest.raises(ValueError, match=message):
        engine.calculate(
            "PROD_RULE",
            RuleContext(date(2026, 9, 1), {"amount": Decimal("25")}),
            production=True,
            rule_pack_version="1405.2",
        )


def test_production_rule_rejects_pack_version_mismatch():
    definition = RuleDefinition(
        code="PROD_RULE",
        title="Production candidate",
        effective_from=date(2026, 1, 1),
        expression={"op": "value", "name": "amount"},
        legal_reference="LAW-REF",
        rule_version="1405.2",
        review_status="approved",
        regression_case_ids=("REG-001",),
    )
    engine = RuleEngine([definition])
    with pytest.raises(ValueError, match="matching rule pack"):
        engine.calculate(
            "PROD_RULE",
            RuleContext(date(2026, 9, 1), {"amount": Decimal("25")}),
            production=True,
            rule_pack_version="1405.3",
        )
