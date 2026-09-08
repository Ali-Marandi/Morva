from __future__ import annotations

import json
from hashlib import sha256
from typing import Mapping


def canonical_teacher_rank_decision_payload(
    *,
    case_id: str,
    employee_no: str,
    proposed_rank: str,
    effect_period: str,
    decision_reference: str,
    committee_governance: Mapping[str, object],
    evidence_fingerprint: str,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "employee_no": employee_no,
        "proposed_rank": proposed_rank,
        "effect_period": effect_period,
        "decision_reference": decision_reference,
        "committee_governance": dict(committee_governance),
        "evidence_fingerprint": evidence_fingerprint,
    }


def teacher_rank_decision_fingerprint(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
