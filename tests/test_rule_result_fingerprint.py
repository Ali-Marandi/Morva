from datetime import date
from decimal import Decimal

from morva.rules.engine import RuleContext, RuleDefinition, RuleEngine
from morva.rules.regression import fingerprint_rule_result, fingerprint_values


def test_rule_result_fingerprint_is_stable() -> None:
    definition = RuleDefinition(
        code="TAX",
        title="Synthetic tax regression",
        effective_from=date(2026, 1, 1),
        expression={"op": "value", "name": "amount"},
        legal_reference="synthetic:TAX",
        taxable=True,
        pensionable=False,
        insurable=False,
    )
    result = RuleEngine([definition]).calculate(
        "TAX",
        RuleContext(date(2026, 1, 1), {"amount": Decimal("123.4500")}),
    )

    assert fingerprint_values({"amount": Decimal("123.4500")}) == fingerprint_values(
        {"amount": Decimal("123.45")}
    )
    assert fingerprint_rule_result(result) == (
        "acb898fb72c647efe0067bb31c40b30b8e51e46fbccb77ef4a9704617d541736"
    )


def test_zero_decimal_representations_share_a_fingerprint() -> None:
    assert fingerprint_values({"amount": Decimal("0.00")}) == fingerprint_values(
        {"amount": Decimal("0")}
    )


def test_classification_changes_fingerprint() -> None:
    definition = RuleDefinition(
        code="INSURANCE",
        title="Synthetic insurance regression",
        effective_from=date(2026, 1, 1),
        expression={"op": "value", "name": "amount"},
        legal_reference="synthetic:INSURANCE",
    )
    result = RuleEngine([definition]).calculate(
        "INSURANCE",
        RuleContext(date(2026, 1, 1), {"amount": Decimal("10")}),
    )
    classified = result.__class__(
        result.code,
        result.amount,
        result.explanation,
        result.legal_reference,
        True,
        False,
        False,
        result.rule_version,
    )
    assert fingerprint_rule_result(result) != fingerprint_rule_result(classified)


def test_rule_version_changes_fingerprint() -> None:
    base = RuleResultForTest(
        code="RULE",
        amount=Decimal("10"),
        explanation="explanation",
        legal_reference="LAW",
        rule_version="1405.1",
    )
    changed = RuleResultForTest(
        code="RULE",
        amount=Decimal("10"),
        explanation="explanation",
        legal_reference="LAW",
        rule_version="1405.2",
    )
    assert fingerprint_rule_result(base) != fingerprint_rule_result(changed)
