from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS, is_1405_rule_pack


def test_1405_rule_pack_detection_and_required_coverage_manifest():
    assert is_1405_rule_pack("1405.0")
    assert is_1405_rule_pack("1405.1")
    assert not is_1405_rule_pack("1404.9")
    assert len(REQUIRED_1405_COMPONENTS) == len(set(REQUIRED_1405_COMPONENTS))
    assert {
        "JOB_RIGHT",
        "TAX",
        "PENSION",
        "INSURANCE",
        "LOAN",
        "COURT_ORDER",
        "REGION_WEATHER",
    }.issubset(REQUIRED_1405_COMPONENTS)
    assert len(REQUIRED_1405_COMPONENTS) == 14
