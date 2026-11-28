from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Mapping

from .engine import RuleResult


MAX_DECIMAL_REPRESENTATION_CHARS = 256


def _canonical_decimal(value: Decimal) -> str:
    decimal = Decimal(value)
    if not decimal.is_finite():
        raise ValueError("decimal value must be finite")
    if decimal.is_zero():
        return "0"

    sign, raw_digits, exponent = decimal.as_tuple()
    digits = list(raw_digits)
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    coefficient = "".join(str(digit) for digit in digits)

    if exponent >= 0:
        rendered_length = len(coefficient) + exponent
        decimal_point = None
    else:
        decimal_point = len(coefficient) + exponent
        rendered_length = (
            len(coefficient) + 1
            if decimal_point > 0
            else 2 - decimal_point + len(coefficient)
        )
    if sign:
        rendered_length += 1
    if rendered_length > MAX_DECIMAL_REPRESENTATION_CHARS:
        raise ValueError("decimal value exceeds the maximum representation length")

    if exponent >= 0:
        rendered = coefficient + ("0" * exponent)
    elif decimal_point > 0:
        rendered = coefficient[:decimal_point] + "." + coefficient[decimal_point:]
    else:
        rendered = "0." + ("0" * -decimal_point) + coefficient
    return ("-" if sign else "") + rendered


def canonical_result_payload(result: RuleResult) -> dict[str, object]:
    return {
        "code": result.code,
        "amount": _canonical_decimal(result.amount),
        "legal_reference": result.legal_reference,
        "rule_version": result.rule_version,
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
