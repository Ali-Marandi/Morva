from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import Base
from morva.rules.regression_cases import (
    load_cases,
    regression_suite_hash,
    validate_repository,
    validate_repository_against_evidence,
)


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


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
