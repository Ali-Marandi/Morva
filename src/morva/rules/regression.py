from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Mapping

from .engine import RuleResult


MAX_DECIMAL_REPRESENTATION_CHARS = 256
_EXPECTED_RESULT_FIELDS = frozenset(
    {
        "code",
        "amount",
        "legal_reference",
        "rule_version",
        "taxable",
        "pensionable",
        "insurable",
    }
)


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



def canonical_expected_result_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Validate and canonicalize the complete JSON representation of a RuleResult."""
    if not isinstance(payload, Mapping):
        raise ValueError("expected output must be an object")

    if set(payload) != _EXPECTED_RESULT_FIELDS:
        raise ValueError("expected output must contain exactly the canonical RuleResult fields")

    code = payload["code"]
    if not isinstance(code, str) or not code.strip():
        raise ValueError("expected output code must be a non-empty string")

    raw_amount = payload["amount"]
    if not isinstance(raw_amount, str) or not raw_amount.strip():
        raise ValueError("expected output amount must be a decimal string")
    try:
        amount = _canonical_decimal(Decimal(raw_amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("expected output amount must be a finite bounded decimal string") from exc

    canonical: dict[str, object] = {
        "code": code,
        "amount": amount,
    }
    for field in ("legal_reference", "rule_version"):
        value = payload[field]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"expected output {field} must be a string or null")
        canonical[field] = value

    for field in ("taxable", "pensionable", "insurable"):
        value = payload[field]
        if not isinstance(value, bool):
            raise ValueError(f"expected output {field} must be a boolean")
        canonical[field] = value

    return canonical


def _fingerprint_payload(payload: Mapping[str, object]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def fingerprint_expected_result_payload(payload: Mapping[str, object]) -> str:
    """Fingerprint the canonical seven-field expected RuleResult payload."""
    return _fingerprint_payload(canonical_expected_result_payload(payload))


def fingerprint_rule_result(result: RuleResult) -> str:
    return _fingerprint_payload(canonical_result_payload(result))


def fingerprint_values(values: Mapping[str, Decimal]) -> str:
    canonical = {key: _canonical_decimal(value) for key, value in sorted(values.items())}
    payload = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
