from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any


def canonical_personnel_order_payload(
    *,
    order_no: str,
    employee_no: str,
    order_type: str,
    issue_date: date,
    effective_from: date,
    effective_to: date | None,
    legal_reference: str | None,
    reason: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "order_no": order_no,
        "employee_no": employee_no,
        "order_type": order_type,
        "issue_date": issue_date.isoformat(),
        "effective_from": effective_from.isoformat(),
        "effective_to": effective_to.isoformat() if effective_to else None,
        "legal_reference": legal_reference,
        "reason": reason,
        "payload": payload,
    }


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"unsupported canonical personnel-order value: {type(value)!r}")


def personnel_order_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
