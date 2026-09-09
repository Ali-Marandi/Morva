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
    assert fingerprint_rule_result(result) == "a1f2e62b6a6f0ac8bb5c6c37815cb4ce2a9ea5fc8fca4c7f365e1112b3a2a5ef"


def test_classification_changes_fingerprint() -> None:
    base = RuleResultProxy = None
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
    )
    assert fingerprint_rule_result(result) != fingerprint_rule_result(classified)
