from morva.hr.teacher_rank_decision_provenance import (
    canonical_teacher_rank_decision_payload,
    teacher_rank_decision_fingerprint,
)


def test_teacher_rank_decision_fingerprint_is_deterministic() -> None:
    payload = canonical_teacher_rank_decision_payload(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-A",
        effect_period="1405-06",
        decision_reference="DEC-1",
        committee_governance={"actor_id": "approver", "reviewer_id": "reviewer"},
        evidence_fingerprint="evidence-1:source-1",
    )
    assert teacher_rank_decision_fingerprint(payload) == teacher_rank_decision_fingerprint(payload)


def test_teacher_rank_decision_fingerprint_changes_when_provenance_changes() -> None:
    base = canonical_teacher_rank_decision_payload(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-A",
        effect_period="1405-06",
        decision_reference="DEC-1",
        committee_governance={"actor_id": "approver", "reviewer_id": "reviewer"},
        evidence_fingerprint="evidence-1:source-1",
    )
    changed = {**base, "decision_reference": "DEC-2"}
    assert teacher_rank_decision_fingerprint(base) != teacher_rank_decision_fingerprint(changed)
