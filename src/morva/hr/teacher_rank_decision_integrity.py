from __future__ import annotations

from collections.abc import Mapping

from morva.hr.teacher_rank_decision_provenance import (
    canonical_teacher_rank_decision_payload,
    teacher_rank_decision_fingerprint,
)


def verify_persisted_teacher_rank_decision_provenance(
    *,
    case_id: str,
    employee_no: str,
    proposed_rank: str,
    effect_period: str,
    decision_reference: str,
    committee_payload: Mapping[str, object],
) -> bool:
    """Verify that a persisted rank decision is still bound to its provenance.

    The check is deliberately fail-closed. It validates the persisted provenance
    envelope, reconstructs the canonical payload from the current decision record,
    and then verifies both payload equality and its SHA-256 fingerprint.
    """
    provenance = committee_payload.get("_decision_provenance")
    if not isinstance(provenance, Mapping):
        return False

    stored_payload = provenance.get("payload")
    fingerprint = provenance.get("fingerprint")
    if not isinstance(stored_payload, Mapping) or not isinstance(fingerprint, str):
        return False

    governance = committee_payload.get("_governance")
    if not isinstance(governance, Mapping):
        return False

    evidence_fingerprint = stored_payload.get("evidence_fingerprint")
    if not isinstance(evidence_fingerprint, str) or not evidence_fingerprint:
        return False

    expected_payload = canonical_teacher_rank_decision_payload(
        case_id=case_id,
        employee_no=employee_no,
        proposed_rank=proposed_rank,
        effect_period=effect_period,
        decision_reference=decision_reference,
        committee_governance=governance,
        evidence_fingerprint=evidence_fingerprint,
    )
    if dict(stored_payload) != expected_payload:
        return False

    return teacher_rank_decision_fingerprint(expected_payload) == fingerprint
