from morva.rules.regression_cases import load_cases, regression_suite_hash, validate_repository


def test_1405_golden_repository_has_five_core_cases():
    cases = load_cases("1405.1")
    assert {case.component_code for case in cases} == {"TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"}
    assert all(case.rule_pack_version == "1405.1" for case in cases)
    assert regression_suite_hash("1405.1") == "40713034bc6f1004c6eab332f066cd4312584ea8a214f03ecaa5ace0d00482d6"


def test_1405_golden_repository_fails_closed_until_authoritative_cases_exist():
    blockers = validate_repository(
        "1405.1",
        required_components=("TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"),
    )
    assert len(blockers) >= 20
    assert all("not approved" in blocker or "missing" in blocker or "no governed" in blocker for blocker in blockers)
