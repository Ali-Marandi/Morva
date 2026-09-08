from morva.hr.teacher_rank_decision_provenance import teacher_rank_decision_fingerprint
from morva.hr.teacher_rank_provenance_verifier import verify_teacher_rank_decision_provenance


def test_verifier_accepts_unchanged_payload() -> None:
    payload = {"case_id": "case-1", "decision_reference": "DEC-1"}
    assert verify_teacher_rank_decision_provenance(
        payload=payload,
        fingerprint=teacher_rank_decision_fingerprint(payload),
    )


def test_verifier_rejects_modified_payload() -> None:
    payload = {"case_id": "case-1", "decision_reference": "DEC-1"}
    fingerprint = teacher_rank_decision_fingerprint(payload)
    modified = {**payload, "decision_reference": "DEC-2"}
    assert not verify_teacher_rank_decision_provenance(
        payload=modified,
        fingerprint=fingerprint,
    )


def test_verifier_rejects_malformed_fingerprint() -> None:
    payload = {"case_id": "case-1", "decision_reference": "DEC-1"}
    assert not verify_teacher_rank_decision_provenance(
        payload=payload,
        fingerprint="not-a-sha256",
    )
