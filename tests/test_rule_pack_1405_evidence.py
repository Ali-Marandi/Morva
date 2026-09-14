from datetime import date, datetime, timezone

from morva.rules.rule_pack_1405_evidence import (
    REQUIRED_1405_COMPONENTS,
    RuleComponentEvidence,
    validate_1405_rule_pack_evidence,
)

EXPECTED_SOURCE_IDS = {
    "JOB_RIGHT": "LMS-CSC-64-68",
    "INCUMBENT_RIGHT": "LMS-CSC-64-68",
    "JOB_ALLOWANCE": "LMS-CSC-64-68",
    "RANK_ALLOWANCE": "TEACHER-RANK-REG-1404",
    "FAMILY_ALLOWANCE": "LMS-CSC-64-68",
    "CHILD_ALLOWANCE": "LMS-CSC-64-68",
    "OVERTIME": "PAY-1405",
    "TEACHING_FEE": "PAY-1405",
    "REGION_WEATHER": "PAY-1405",
    "TAX": "TAX-1405",
    "PENSION": "PAY-1405",
    "INSURANCE": "PAY-1405",
    "LOAN": "PAY-1405",
    "COURT_ORDER": "PAY-1405",
}


def _evidence(**overrides):
    code = overrides.pop("component_code", REQUIRED_1405_COMPONENTS[0])
    values = {
        "component_code": code,
        "source_id": EXPECTED_SOURCE_IDS[code],
        "citation": "official primary-source citation",
        "issuer": "official issuer",
        "source_uri": "https://official.example.invalid/doc.pdf",
        "document_hash": "a" * 64,
        "adoption_date": date(2026, 3, 1),
        "effective_from": date(2026, 3, 20),
        "effective_to": None,
        "retrieved_at": datetime(2026, 9, 14, tzinfo=timezone.utc),
        "reviewer_id": "reviewer-1",
        "approver_id": "approver-1",
        "regression_reference": "tests/test_rule_pack_regression.py::test_component",
        "treatment": "earning" if code not in {"TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"} else "deduction",
        "taxable": True,
        "pensionable": True,
        "insurable": True,
    }
    values.update(overrides)
    return RuleComponentEvidence(**values)


def _complete_evidence():
    return tuple(_evidence(component_code=code) for code in REQUIRED_1405_COMPONENTS)


def test_complete_evidence_set_is_accepted_without_activation():
    result = validate_1405_rule_pack_evidence(_complete_evidence(), EXPECTED_SOURCE_IDS)
    assert result.accepted is True
    assert result.blockers == ()
    assert len(result.fingerprint) == 64


def test_missing_component_is_blocking():
    evidence = tuple(item for item in _complete_evidence() if item.component_code != "TAX")
    result = validate_1405_rule_pack_evidence(evidence, EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "missing evidence for component TAX" in result.blockers


def test_source_register_mismatch_is_blocking():
    evidence = list(_complete_evidence())
    evidence[0] = _evidence(component_code="JOB_RIGHT", source_id="TAX-1405")
    result = validate_1405_rule_pack_evidence(tuple(evidence), EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "JOB_RIGHT source_id does not match governed source register" in result.blockers


def test_review_and_approval_must_be_distinct():
    evidence = list(_complete_evidence())
    evidence[0] = _evidence(component_code="JOB_RIGHT", reviewer_id="same")
    evidence[0] = _evidence(component_code="JOB_RIGHT", reviewer_id="same", approver_id="same")
    result = validate_1405_rule_pack_evidence(tuple(evidence), EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "JOB_RIGHT reviewer and approver must be distinct" in result.blockers


def test_unresolved_treatment_blocks_activation_readiness():
    evidence = list(_complete_evidence())
    evidence[0] = _evidence(component_code="JOB_RIGHT", taxable=None)
    result = validate_1405_rule_pack_evidence(tuple(evidence), EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "JOB_RIGHT tax/pension/insurance treatment must be explicitly resolved before activation" in result.blockers


def test_review_required_is_the_only_nonactivated_status():
    evidence = list(_complete_evidence())
    evidence[0] = _evidence(component_code="JOB_RIGHT", activation_status="approved")
    result = validate_1405_rule_pack_evidence(tuple(evidence), EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "JOB_RIGHT.activation_status must remain review_required until formal approval" in result.blockers


def test_retrieval_timestamp_requires_timezone():
    evidence = list(_complete_evidence())
    evidence[0] = _evidence(component_code="JOB_RIGHT", retrieved_at=datetime(2026, 9, 14))
    result = validate_1405_rule_pack_evidence(tuple(evidence), EXPECTED_SOURCE_IDS)
    assert result.accepted is False
    assert "JOB_RIGHT.retrieved_at must be timezone-aware" in result.blockers
