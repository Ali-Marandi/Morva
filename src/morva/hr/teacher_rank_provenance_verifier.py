from __future__ import annotations

from typing import Mapping

from morva.hr.teacher_rank_decision_provenance import teacher_rank_decision_fingerprint


def verify_teacher_rank_decision_provenance(
    *,
    payload: Mapping[str, object],
    fingerprint: str,
) -> bool:
    return teacher_rank_decision_fingerprint(payload) == fingerprint
