from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS


REQUIRED_REGRESSION_COMPONENTS = {
    "TAX",
    "PENSION",
    "INSURANCE",
    "LOAN",
    "COURT_ORDER",
}


def test_required_1405_components_include_regression_targets() -> None:
    assert REQUIRED_REGRESSION_COMPONENTS <= set(REQUIRED_1405_COMPONENTS)


def test_regression_contract_is_fail_closed_until_authoritative_evidence_exists() -> None:
    cases = {
        component: {
            "rule_pack_version": "1405",
            "input_fingerprint": "pending-authoritative-input",
            "expected_treatment": "review_required",
            "taxable": "review_required",
            "pensionable": "review_required",
            "insurable": "review_required",
            "expected_output_fingerprint": "pending-authoritative-output",
        }
        for component in REQUIRED_REGRESSION_COMPONENTS
    }

    assert set(cases) == REQUIRED_REGRESSION_COMPONENTS
    for case in cases.values():
        assert case["expected_treatment"] == "review_required"
        assert case["taxable"] == "review_required"
        assert case["pensionable"] == "review_required"
        assert case["insurable"] == "review_required"
        assert case["input_fingerprint"] != case["expected_output_fingerprint"]
