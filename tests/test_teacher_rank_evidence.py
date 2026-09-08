from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.hr.teacher_rank_evidence import check_teacher_rank_evidence
from morva.persistence.domain_extensions import TeacherRankCaseRecord
from morva.persistence.enterprise_models import Base, LegalSourceRecord, RuleEvidenceRecord

_HASH = "a" * 64
_REGRESSION = "b" * 64


def _case(effect_period: str = "1405-06", proposed_rank: str = "rank-A") -> TeacherRankCaseRecord:
    return TeacherRankCaseRecord(
        employee_no="E-1",
        current_rank="rank-0",
        proposed_rank=proposed_rank,
        status="committee_approved",
        effect_period=effect_period,
        assessment_payload={},
        committee_payload={},
        appeal_payload={},
    )


def _source(*, source_hash: str = _HASH, status: str = "approved", effective_from: str = "1405-01-01", effective_to: str | None = None) -> LegalSourceRecord:
    return LegalSourceRecord(
        citation="authoritative-test-source",
        issuer="test-authority",
        adoption_date="1404-12-01",
        effective_from=effective_from,
        effective_to=effective_to,
        document_hash=source_hash,
        source_uri="https://example.invalid/source",
        status=status,
    )


def _evidence(source_id, *, status: str = "approved", source_hash: str = _HASH, reviewer: str = "reviewer", approver: str = "approver") -> RuleEvidenceRecord:
    return RuleEvidenceRecord(
        rule_pack_version="teacher-rank-test-1",
        component_code="teacher_rank:rank-A",
        legal_source_id=source_id,
        issuer="test-authority",
        article="article-1",
        clause=None,
        population_scope="teacher-rank-population",
        source_hash=source_hash,
        regression_suite_hash=_REGRESSION,
        status=status,
        reviewed_by=reviewer,
        approved_by=approver,
    )


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_missing_evidence_fails_closed() -> None:
    with _session() as session:
        result = check_teacher_rank_evidence(session, _case())
        assert result.ready is False
        assert "no approved evidence" in result.blockers[0]


def test_approved_matching_source_and_evidence_is_ready() -> None:
    with _session() as session:
        source = _source()
        session.add(source)
        session.flush()
        evidence = _evidence(source.id)
        session.add(evidence)
        session.flush()
        result = check_teacher_rank_evidence(session, _case())
        assert result.ready is True
        assert result.blockers == ()
        assert result.legal_source_id == source.id
        assert result.evidence_id == evidence.id


def test_unapproved_source_and_evidence_block_decision() -> None:
    with _session() as session:
        source = _source(status="reviewed")
        session.add(source)
        session.flush()
        session.add(_evidence(source.id, status="reviewed"))
        session.flush()
        result = check_teacher_rank_evidence(session, _case())
        assert result.ready is False
        assert any("legal source is not approved" in blocker for blocker in result.blockers)
        assert any("teacher rank evidence is not approved" in blocker for blocker in result.blockers)


def test_hash_mismatch_blocks_even_when_records_are_approved() -> None:
    with _session() as session:
        source = _source(source_hash="c" * 64)
        session.add(source)
        session.flush()
        session.add(_evidence(source.id))
        session.flush()
        result = check_teacher_rank_evidence(session, _case())
        assert result.ready is False
        assert any("source hash does not match legal source" in blocker for blocker in result.blockers)


def test_effect_period_outside_source_window_blocks() -> None:
    with _session() as session:
        source = _source(effective_from="1405-07-01", effective_to="1405-12-29")
        session.add(source)
        session.flush()
        session.add(_evidence(source.id))
        session.flush()
        result = check_teacher_rank_evidence(session, _case(effect_period="1405-06"))
        assert result.ready is False
        assert any("effect period predates legal source" in blocker for blocker in result.blockers)


def test_invalid_source_hash_is_rejected() -> None:
    with _session() as session:
        source = _source(source_hash="not-a-sha256")
        session.add(source)
        session.flush()
        session.add(_evidence(source.id, source_hash="not-a-sha256"))
        session.flush()
        result = check_teacher_rank_evidence(session, _case())
        assert result.ready is False
        assert any("legal source document hash is invalid" in blocker for blocker in result.blockers)
        assert any("teacher rank evidence source hash is invalid" in blocker for blocker in result.blockers)
