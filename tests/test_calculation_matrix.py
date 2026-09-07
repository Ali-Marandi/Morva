from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import Base, RulePackRecord
from morva.rules.calculation_matrix import (
    approve_matrix_entry,
    create_matrix_entry,
    matrix_readiness,
    validate_matrix_payload,
)


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _setup(session, *, source_status="approved", evidence_status="approved"):
    pack = RulePackRecord(version="1405.0-test", status="reviewed", reviewed_by="legal-reviewer")
    source = LegalSourceRecord(
        citation="Synthetic authority source",
        issuer="Synthetic issuer",
        adoption_date="2026-01-01",
        effective_from="2026-01-01",
        document_hash="a" * 64,
        status=source_status,
    )
    session.add_all([pack, source])
    session.flush()
    evidence = RuleEvidenceRecord(
        rule_pack_version=pack.version,
        component_code="TEST_EARNING",
        legal_source_id=source.id,
        issuer=source.issuer,
        article="1",
        population_scope="all",
        source_hash=source.document_hash,
        regression_suite_hash="b" * 64,
        status=evidence_status,
        reviewed_by="evidence-reviewer" if evidence_status != "review_required" else None,
        approved_by="evidence-approver" if evidence_status == "approved" else None,
    )
    session.add(evidence)
    session.commit()
    return pack, source, evidence


def test_matrix_payload_rejects_unknown_expression_operation():
    try:
        validate_matrix_payload(
            treatment="earning",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            regression_suite_hash="b" * 64,
            expression={"op": "pow", "args": [{"op": "const", "value": "2"}]},
            legal_article="1",
            population_scope="all",
        )
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unknown expression operation must be rejected")


def test_matrix_requires_approved_source_and_evidence():
    with _session() as session:
        _setup(session, source_status="review_required")
        try:
            create_matrix_entry(
                session,
                {
                    "rule_pack_version": "1405.0-test",
                    "component_code": "TEST_EARNING",
                    "population_scope": "all",
                    "treatment": "earning",
                    "expression": {"op": "value", "name": "base"},
                    "effective_from": date(2026, 1, 1),
                    "effective_to": None,
                    "legal_source_id": session.query(LegalSourceRecord).first().id,
                    "legal_article": "1",
                    "legal_clause": None,
                    "taxable": True,
                    "pensionable": False,
                    "insurable": False,
                    "regression_suite_hash": "b" * 64,
                    "notes": None,
                },
                "matrix-user",
            )
        except ValueError as exc:
            assert "approved" in str(exc)
        else:
            raise AssertionError("unapproved legal evidence must block matrix creation")


def test_matrix_entry_review_approval_and_readiness():
    with _session() as session:
        pack, source, evidence = _setup(session)
        entry = create_matrix_entry(
            session,
            {
                "rule_pack_version": pack.version,
                "component_code": evidence.component_code,
                "population_scope": "all",
                "treatment": "earning",
                "expression": {"op": "mul", "args": [{"op": "value", "name": "base"}, {"op": "value", "name": "rate"}]},
                "effective_from": date(2026, 1, 1),
                "effective_to": None,
                "legal_source_id": source.id,
                "legal_article": "1",
                "legal_clause": None,
                "taxable": True,
                "pensionable": False,
                "insurable": False,
                "regression_suite_hash": evidence.regression_suite_hash,
                "notes": None,
            },
            "matrix-creator",
        )
        session.commit()
        entry = session.get(CalculationMatrixRecord, entry.id)
        entry.reviewed_by = "matrix-reviewer"
        entry.status = "reviewed"
        session.commit()
        approve_matrix_entry(entry, "matrix-approver")
        session.commit()
        readiness = matrix_readiness(session, pack.version)
        assert readiness.ready is True
        assert readiness.entry_count == 1


def test_empty_matrix_is_blocking():
    with _session() as session:
        session.add(RulePackRecord(version="1405.empty", status="approved"))
        session.commit()
        readiness = matrix_readiness(session, "1405.empty")
        assert readiness.ready is False
        assert "no calculation-matrix entries" in readiness.blockers[0]
