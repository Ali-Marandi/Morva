from morva.hr.teacher_rank_provenance_verifier import verify_teacher_rank_decision_provenance


def test_verifier_accepts_unchanged_payload() -> None:
    payload = {"case_id": "case-1", "decision_reference": "DEC-1"}
    from morva.hr.teacher_rank_decision_provenance import teacher_rank_decision_fingerprint

    assert verify_teacher_rank_decision_provenance(
        payload=payload,
        fingerprint=teacher_rank_decision_fingerprint(payload),
    )


def test_verifier_rejects_modified_payload() -> None:
    payload = {"case_id": "case-1", "decision_reference": "DEC-1"}
    from morva.hr.teacher_rank_decision_provenance import teacher_rank_decision_fingerprint

    fingerprint = teacher_rank_decision_fingerprint(payload)
    modified = {**payload, "decision_reference": "DEC-2"}
    assert not verify_teacher_rank_decision_provenance(payload=modified, fingerprint=fingerprint)
