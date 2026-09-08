from __future__ import annotations

import hmac
import re
from typing import Mapping

from morva.hr.teacher_rank_decision_provenance import teacher_rank_decision_fingerprint

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def verify_teacher_rank_decision_provenance(
    *,
    payload: Mapping[str, object],
    fingerprint: str,
) -> bool:
    if not _HEX64.fullmatch(fingerprint):
        return False
    expected = teacher_rank_decision_fingerprint(payload)
    return hmac.compare_digest(expected, fingerprint)
