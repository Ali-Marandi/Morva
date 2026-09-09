from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Mapping

from .engine import RuleResult


def _canonical_decimal(value: Decimal) -> str:
    decimal = Decimal(value)
    if decimal == 0:
        decimal = Decimal(0)
    return format(decimal.normalize(), "f")


def canonical_result_payload(result: RuleResult) -> dict[str, object]:
    return {
        "code": result.code,
        "amount": _canonical_decimal(result.amount),
        "legal_reference": result.legal_reference,
        "taxable": result.taxable,
        "pensionable": result.pensionable,
        "insurable": result.insurable,
    }


def fingerprint_rule_result(result: RuleResult) -> str:
    payload = json.dumps(
        canonical_result_payload(result),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_values(values: Mapping[str, Decimal]) -> str:
    canonical = {key: _canonical_decimal(value) for key, value in sorted(values.items())}
    payload = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
