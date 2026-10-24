from datetime import datetime
from decimal import Decimal

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
