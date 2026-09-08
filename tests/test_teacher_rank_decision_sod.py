import pytest

from morva.hr.teacher_rank import check_decision_separation_of_duties
from morva.persistence.domain_extensions import TeacherRankCaseRecord


def _case(**governance: str) -> TeacherRankCaseRecord:
    return TeacherRankCaseRecord(
        employee_no="E-1",
        current_rank="rank-0",
        proposed_rank="rank-A",
        status="committee_approved",
        effect_period="1405-06",
        assessment_payload={},
        committee_payload={"evidence": "approved", "_governance": governance},
        appeal_payload={},
    )


def test_decision_requires_committee_provenance() -> None:
    record = _case()
    with pytest.raises(ValueError, match="committee (approval|approver) provenance is missing"):
        check_decision_separation_of_duties(record, "decision-maker")


def test_decision_requires_distinct_committee_approver_and_reviewer() -> None:
    record = _case(actor_id="reviewer", reviewer_id="reviewer")
    with pytest.raises(Exception):
        check_decision_separation_of_duties(record, "decision-maker")


def test_decision_maker_must_differ_from_committee_approver() -> None:
    record = _case(actor_id="approver", reviewer_id="reviewer")
    with pytest.raises(Exception):
        check_decision_separation_of_duties(record, "approver")


def test_distinct_decision_actor_passes() -> None:
    record = _case(actor_id="approver", reviewer_id="reviewer")
    check_decision_separation_of_duties(record, "decision-maker")
