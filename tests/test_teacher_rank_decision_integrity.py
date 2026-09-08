from morva.hr.teacher_rank_decision_integrity import verify_persisted_teacher_rank_decision_provenance
from morva.hr.teacher_rank_decision_provenance import (
    canonical_teacher_rank_decision_payload,
    teacher_rank_decision_fingerprint,
)


def _payload() -> tuple[dict[str, object], dict[str, object]]:
    governance = {"actor_id": "committee-1", "reviewer_id": "reviewer-1"}
    payload = canonical_teacher_rank_decision_payload(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-X",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_governance=governance,
        evidence_fingerprint="evidence-1:source-1",
    )
    return governance, payload


def _committee_payload() -> dict[str, object]:
    governance, payload = _payload()
    return {
        "_governance": governance,
        "_decision_provenance": {
            "payload": payload,
            "fingerprint": teacher_rank_decision_fingerprint(payload),
        },
    }


def test_integrity_accepts_unchanged_persisted_record() -> None:
    assert verify_persisted_teacher_rank_decision_provenance(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-X",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_payload=_committee_payload(),
    )


def test_integrity_rejects_current_record_mutation() -> None:
    assert not verify_persisted_teacher_rank_decision_provenance(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-Y",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_payload=_committee_payload(),
    )


def test_integrity_rejects_provenance_payload_mutation() -> None:
    committee_payload = _committee_payload()
    provenance = committee_payload["_decision_provenance"]
    assert isinstance(provenance, dict)
    stored_payload = provenance["payload"]
    assert isinstance(stored_payload, dict)
    stored_payload["decision_reference"] = "DEC-2"

    assert not verify_persisted_teacher_rank_decision_provenance(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-X",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_payload=committee_payload,
    )


def test_integrity_rejects_missing_or_malformed_provenance() -> None:
    assert not verify_persisted_teacher_rank_decision_provenance(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-X",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_payload={},
    )
    assert not verify_persisted_teacher_rank_decision_provenance(
        case_id="case-1",
        employee_no="E-1",
        proposed_rank="rank-X",
        effect_period="1405-01",
        decision_reference="DEC-1",
        committee_payload={"_decision_provenance": {"payload": {}, "fingerprint": "bad"}},
    )
