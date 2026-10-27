import json
from dataclasses import replace
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import Base
from morva.rules.regression import fingerprint_values
from morva.rules.regression_cases import (
    RegressionCase,
    load_cases,
    regression_suite_hash,
    validate_repository,
    validate_repository_against_evidence,
)


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _case(
    case_id: str,
    *,
    component_code: str = "TAX",
    legal_source_hash: str = "a" * 64,
    expected_output_missing: bool = False,
) -> RegressionCase:
    input_values = {"taxable_base": Decimal("100.00")}
    return RegressionCase(
        case_id=case_id,
        rule_pack_version="1405.1",
        component_code=component_code,
        population_scope="all",
        effective_date="1405-01-01",
        status="approved",
        input_values=input_values,
        expected_output=None if expected_output_missing else {"amount": "10.00"},
        input_fingerprint=fingerprint_values(input_values),
        expected_output_fingerprint="b" * 64,
        legal_source_hash=legal_source_hash,
        legal_article="1",
        legal_clause=None,
    )


def test_1405_golden_repository_has_five_core_cases():
    cases = load_cases("1405.1")
    assert {case.component_code for case in cases} == {"TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"}
    assert all(case.rule_pack_version == "1405.1" for case in cases)
    assert regression_suite_hash("1405.1") == "efad8788dd84eaae67dc8034361a92e2b31010fa7be096358ace7520c63e5631"


def test_1405_golden_repository_fails_closed_until_authoritative_cases_exist():
    blockers = validate_repository("1405.1", required_components=("TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"))
    assert len(blockers) >= 25
    assert all("not approved" in blocker or "missing" in blocker or "no governed" in blocker or "invalid" in blocker for blocker in blockers)


def test_1405_golden_repository_must_match_registered_legal_evidence():
    with _session() as session:
        source = LegalSourceRecord(
            citation="Synthetic authority source",
            issuer="Synthetic issuer",
            adoption_date="2026-01-01",
            effective_from="2026-01-01",
            document_hash="a" * 64,
            status="approved",
        )
        session.add(source)
        session.flush()
        for component in ("TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"):
            session.add(
                RuleEvidenceRecord(
                    rule_pack_version="1405.1",
                    component_code=component,
                    legal_source_id=source.id,
                    issuer=source.issuer,
                    article="1",
                    clause=None,
                    population_scope="all",
                    source_hash=source.document_hash,
                    regression_suite_hash=regression_suite_hash("1405.1"),
                    status="approved",
                    reviewed_by="reviewer",
                    approved_by="approver",
                    approved_at=datetime(2026, 1, 3),
                )
            )
        session.commit()
        blockers = validate_repository_against_evidence(session, "1405.1", required_components=("TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"))
        assert any("source hash mismatch" in blocker for blocker in blockers)
        assert any("missing legal_article" in blocker for blocker in blockers)
        assert not any("regression suite hash mismatch" in blocker for blocker in blockers)


def test_validator_checks_every_golden_case_for_a_component(monkeypatch):
    # نمونه نامعتبر قبلی نباید با نمونه معتبر بعدی همان مؤلفه پنهان شود.
    invalid_case = _case("tax-missing-output", expected_output_missing=True)
    valid_case = _case("tax-valid")
    monkeypatch.setattr(
        "morva.rules.regression_cases.load_cases",
        lambda _version: (invalid_case, valid_case),
    )

    blockers = validate_repository("1405.1", required_components=("TAX",))

    assert "golden case tax-missing-output is missing expected output" in blockers


def test_validator_rejects_duplicate_golden_case_ids(monkeypatch):
    duplicate_id = "same-case-id"
    cases = (
        _case(duplicate_id, component_code="TAX"),
        _case(duplicate_id, component_code="PENSION"),
    )
    monkeypatch.setattr("morva.rules.regression_cases.load_cases", lambda _version: cases)

    blockers = validate_repository("1405.1", required_components=("TAX", "PENSION"))

    assert f"duplicate golden case_id {duplicate_id}" in blockers


def test_evidence_validation_checks_every_case_for_a_component(monkeypatch):
    # مغایرت منبع در نمونه قبلی نباید با نمونه منطبق بعدی پنهان شود.
    mismatched_case = _case("tax-wrong-source", legal_source_hash="b" * 64)
    matching_case = _case("tax-matching-source")
    monkeypatch.setattr(
        "morva.rules.regression_cases.load_cases",
        lambda _version: (mismatched_case, matching_case),
    )

    with _session() as session:
        source = LegalSourceRecord(
            citation="Synthetic authority source",
            issuer="Synthetic issuer",
            adoption_date="2026-01-01",
            effective_from="2026-01-01",
            document_hash="a" * 64,
            status="approved",
        )
        session.add(source)
        session.flush()
        session.add(
            RuleEvidenceRecord(
                rule_pack_version="1405.1",
                component_code="TAX",
                legal_source_id=source.id,
                issuer=source.issuer,
                article="1",
                clause=None,
                population_scope="all",
                source_hash=source.document_hash,
                regression_suite_hash="c" * 64,
                status="approved",
                reviewed_by="reviewer",
                approved_by="approver",
                approved_at=datetime(2026, 1, 3),
            )
        )
        session.commit()

        blockers = validate_repository_against_evidence(
            session,
            "1405.1",
            required_components=("TAX",),
        )

    assert "golden case tax-wrong-source source hash mismatch" in blockers


def test_validator_checks_unrequested_cases_in_the_repository(monkeypatch):
    valid_required_case = _case("tax-valid", component_code="TAX")
    invalid_additional_case = _case(
        "extra-missing-output",
        component_code="EXTRA",
        expected_output_missing=True,
    )
    monkeypatch.setattr(
        "morva.rules.regression_cases.load_cases",
        lambda _version: (valid_required_case, invalid_additional_case),
    )

    blockers = validate_repository("1405.1", required_components=("TAX",))

    assert "golden case extra-missing-output is missing expected output" in blockers


def test_evidence_validation_requires_evidence_for_unrequested_components(monkeypatch):
    # نمونه خارج از فهرست اجباری نیز باید شواهد مستقل مؤلفه خودش را داشته باشد.
    tax_case = _case("tax-valid", component_code="TAX")
    extra_case = _case("extra-without-evidence", component_code="EXTRA")
    monkeypatch.setattr(
        "morva.rules.regression_cases.load_cases",
        lambda _version: (tax_case, extra_case),
    )

    with _session() as session:
        source = LegalSourceRecord(
            citation="Synthetic authority source",
            issuer="Synthetic issuer",
            adoption_date="2026-01-01",
            effective_from="2026-01-01",
            document_hash="a" * 64,
            status="approved",
        )
        session.add(source)
        session.flush()
        session.add(
            RuleEvidenceRecord(
                rule_pack_version="1405.1",
                component_code="TAX",
                legal_source_id=source.id,
                issuer=source.issuer,
                article="1",
                clause=None,
                population_scope="all",
                source_hash=source.document_hash,
                regression_suite_hash="c" * 64,
                status="approved",
                reviewed_by="reviewer",
                approved_by="approver",
                approved_at=datetime(2026, 1, 3),
            )
        )
        session.commit()

        blockers = validate_repository_against_evidence(
            session,
            "1405.1",
            required_components=("TAX",),
        )

    assert "missing rule evidence for golden case extra-without-evidence" in blockers


@pytest.mark.parametrize("case_id", [None, "", "   ", 123])
def test_load_cases_rejects_empty_or_non_string_case_ids(monkeypatch, tmp_path, case_id):
    cases_dir = tmp_path / "1405.1"
    cases_dir.mkdir()
    (cases_dir / "cases.json").write_text(
        json.dumps([{"case_id": case_id}]),
        encoding="utf-8",
    )
    monkeypatch.setattr("morva.rules.regression_cases._REPOSITORY_ROOT", tmp_path)

    with pytest.raises(ValueError, match="case_id must be a non-empty string"):
        load_cases("1405.1")


def _raw_case(**overrides):
    value = {
        "case_id": "schema-case-001",
        "rule_pack_version": "1405.1",
        "component_code": "TAX",
        "population_scope": "all",
        "effective_date": "1405-01-01",
        "status": "review_required",
        "input_values": {"taxable_base": "100.00"},
        "expected_output": None,
        "input_fingerprint": None,
        "expected_output_fingerprint": None,
        "legal_source_hash": None,
        "legal_article": None,
        "legal_clause": None,
    }
    value.update(overrides)
    return value


def _write_case_file(tmp_path, monkeypatch, case):
    cases_dir = tmp_path / "1405.1"
    cases_dir.mkdir(exist_ok=True)
    (cases_dir / "cases.json").write_text(json.dumps([case]), encoding="utf-8")
    monkeypatch.setattr("morva.rules.regression_cases._REPOSITORY_ROOT", tmp_path)


@pytest.mark.parametrize(
    "raw_json",
    [
        '[{"case_id":"first","case_id":"second"}]',
        '[{"case_id":"duplicate-input","input_values":{"taxable_base":"100.00","taxable_base":"1.00"}}]',
        '[{"case_id":"duplicate-output","expected_output":{"amount":"100.00","amount":"1.00"}}]',
    ],
)
def test_load_cases_rejects_duplicate_json_object_keys(monkeypatch, tmp_path, raw_json):
    cases_dir = tmp_path / "1405.1"
    cases_dir.mkdir()
    (cases_dir / "cases.json").write_text(raw_json, encoding="utf-8")
    monkeypatch.setattr("morva.rules.regression_cases._REPOSITORY_ROOT", tmp_path)

    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_cases("1405.1")


@pytest.mark.parametrize("version", ["../outside", "nested/1405.1", r"..\\outside", ".."])
def test_load_cases_rejects_unsafe_rule_pack_path_identifiers(monkeypatch, tmp_path, version):
    monkeypatch.setattr("morva.rules.regression_cases._REPOSITORY_ROOT", tmp_path)

    with pytest.raises(ValueError, match="rule_pack_version must be a safe version identifier"):
        load_cases(version)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rule_pack_version", None),
        ("rule_pack_version", 1405),
        ("rule_pack_version", "   "),
        ("component_code", None),
        ("component_code", 7),
        ("component_code", ""),
        ("population_scope", None),
        ("population_scope", 12),
        ("population_scope", " "),
        ("effective_date", None),
        ("effective_date", 20260101),
        ("effective_date", ""),
        ("status", None),
        ("status", False),
        ("status", " "),
    ],
)
def test_load_cases_rejects_malformed_required_text_fields(monkeypatch, tmp_path, field, value):
    raw_case = _raw_case(**{field: value})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match=f"{field} must be a non-empty string"):
        load_cases("1405.1")


@pytest.mark.parametrize("input_value", [None, True, "NaN", "Infinity", "-Infinity", "not-decimal", {}, []])
def test_load_cases_rejects_non_finite_or_non_decimal_inputs(monkeypatch, tmp_path, input_value):
    raw_case = _raw_case(input_values={"taxable_base": input_value})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match="input value taxable_base must be a finite decimal"):
        load_cases("1405.1")


def test_load_cases_rejects_blank_input_value_keys(monkeypatch, tmp_path):
    raw_case = _raw_case(input_values={"  ": "1"})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match="input_values keys must be non-empty strings"):
        load_cases("1405.1")


@pytest.mark.parametrize("expected_output", ["10.00", [], 3])
def test_load_cases_requires_expected_output_object_or_null(monkeypatch, tmp_path, expected_output):
    raw_case = _raw_case(expected_output=expected_output)
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match="expected_output must be an object or null"):
        load_cases("1405.1")


def test_load_cases_rejects_non_finite_expected_output_numbers(monkeypatch, tmp_path):
    raw_case = _raw_case(expected_output={"amount": float("nan")})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match="expected_output must not contain non-finite numbers"):
        load_cases("1405.1")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_fingerprint", 123),
        ("expected_output_fingerprint", {}),
        ("legal_source_hash", 123),
        ("legal_article", False),
        ("legal_clause", 3),
    ],
)
def test_load_cases_rejects_wrong_optional_metadata_types(monkeypatch, tmp_path, field, value):
    raw_case = _raw_case(**{field: value})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match=f"{field} must be a string or null"):
        load_cases("1405.1")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("input_fingerprint", "not-a-sha256", "invalid input fingerprint"),
        ("expected_output_fingerprint", "not-a-sha256", "invalid expected output fingerprint"),
        ("legal_source_hash", "not-a-sha256", "invalid legal_source_hash"),
    ],
)
def test_validator_rejects_malformed_sha256_fingerprints(
    monkeypatch, field, value, message
):
    case = replace(_case("schema-fingerprint-001"), **{field: value})
    monkeypatch.setattr("morva.rules.regression_cases.load_cases", lambda _version: (case,))

    blockers = validate_repository("1405.1", required_components=("TAX",))

    assert f"golden case {case.case_id} has an {message}" in blockers




def test_fingerprint_values_preserves_significant_digits_beyond_decimal_context():
    first = fingerprint_values(
        {"amount": Decimal("123456789012345678901234567890")}
    )
    second = fingerprint_values(
        {"amount": Decimal("123456789012345678901234567891")}
    )

    assert first != second


@pytest.mark.parametrize(
    "value",
    [Decimal("1e999999999"), Decimal("1e-999999999")],
)
def test_fingerprint_values_rejects_unbounded_decimal_representations(value):
    with pytest.raises(ValueError, match="maximum representation length"):
        fingerprint_values({"amount": value})


@pytest.mark.parametrize(
    "input_value",
    ["1e999999999", "1e-999999999", "0e-999999999", "1." + ("0" * 300)],
)
def test_load_cases_rejects_unbounded_decimal_representations(
    monkeypatch, tmp_path, input_value
):
    raw_case = _raw_case(input_values={"taxable_base": input_value})
    _write_case_file(tmp_path, monkeypatch, raw_case)

    with pytest.raises(ValueError, match="maximum decimal representation length"):
        load_cases("1405.1")



def test_evidence_validation_rejects_stale_regression_suite_hash(monkeypatch):
    case = _case("tax-stale-suite-hash")
    monkeypatch.setattr(
        "morva.rules.regression_cases.load_cases",
        lambda _version: (case,),
    )

    with _session() as session:
        source = LegalSourceRecord(
            citation="Synthetic authority source",
            issuer="Synthetic issuer",
            adoption_date="2026-01-01",
            effective_from="2026-01-01",
            document_hash="a" * 64,
            status="approved",
        )
        session.add(source)
        session.flush()
        session.add(
            RuleEvidenceRecord(
                rule_pack_version="1405.1",
                component_code="TAX",
                legal_source_id=source.id,
                issuer=source.issuer,
                article="1",
                clause=None,
                population_scope="all",
                source_hash=source.document_hash,
                regression_suite_hash="c" * 64,
                status="approved",
                reviewed_by="reviewer",
                approved_by="approver",
                approved_at=datetime(2026, 1, 3),
            )
        )
        session.commit()

        blockers = validate_repository_against_evidence(
            session,
            "1405.1",
            required_components=("TAX",),
        )

    assert blockers == (
        "rule evidence regression suite hash mismatch for golden case tax-stale-suite-hash",
    )
