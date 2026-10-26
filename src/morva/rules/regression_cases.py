from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord

from .regression import (
    MAX_DECIMAL_REPRESENTATION_CHARS,
    fingerprint_rule_result,
    fingerprint_values,
)
from .rule_pack_1405 import REQUIRED_1405_COMPONENTS

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3] / "docs" / "legal" / "golden-cases"
_ALLOWED_STATUSES = {"review_required", "approved", "published"}
_HEX64 = set("0123456789abcdefABCDEF")
_SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


@dataclass(frozen=True, slots=True)
class RegressionCase:
    case_id: str
    rule_pack_version: str
    component_code: str
    population_scope: str
    effective_date: str
    status: str
    input_values: Mapping[str, Decimal]
    expected_output: Mapping[str, object] | None
    input_fingerprint: str | None
    expected_output_fingerprint: str | None
    legal_source_hash: str | None
    legal_article: str | None
    legal_clause: str | None


def _validate_rule_pack_version(rule_pack_version: str) -> None:
    # نسخه مستقیماً نام پوشه مخزن را می‌سازد؛ فقط شناسه تک‌مسیره و محدود را می‌پذیریم.
    if not isinstance(rule_pack_version, str) or not _SAFE_VERSION.fullmatch(rule_pack_version):
        raise ValueError("rule_pack_version must be a safe version identifier")


def _required_text(item: dict[str, object], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_text(item: dict[str, object], field: str) -> str | None:
    value = item.get(field)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    return value


def _fixed_point_representation_length(value: Decimal) -> int:
    sign, digits, exponent = value.as_tuple()
    digit_count = len(digits)
    if exponent >= 0:
        length = digit_count + exponent
    else:
        decimal_point = digit_count + exponent
        length = (
            digit_count + 1
            if decimal_point > 0
            else 2 - decimal_point + digit_count
        )
    return length + int(bool(sign))


def _decimal_input_values(values: dict[str, object]) -> dict[str, Decimal]:
    converted: dict[str, Decimal] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("input_values keys must be non-empty strings")
        if value is None or isinstance(value, bool) or isinstance(value, (dict, list)):
            raise ValueError(f"input value {key} must be a finite decimal")
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"input value {key} must be a finite decimal") from exc
        if not decimal_value.is_finite():
            raise ValueError(f"input value {key} must be a finite decimal")
        if (
            _fixed_point_representation_length(decimal_value)
            > MAX_DECIMAL_REPRESENTATION_CHARS
        ):
            raise ValueError(
                f"input value {key} exceeds the maximum decimal representation length"
            )
        converted[key] = decimal_value
    return converted


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _validate_finite_json(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("expected_output must not contain non-finite numbers")
    if isinstance(value, dict):
        for nested in value.values():
            _validate_finite_json(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_finite_json(nested)


def _canonical_case(case: RegressionCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "rule_pack_version": case.rule_pack_version,
        "component_code": case.component_code,
        "population_scope": case.population_scope,
        "effective_date": case.effective_date,
        "status": case.status,
        "input_values": {key: format(Decimal(value), "f") for key, value in sorted(case.input_values.items())},
        "expected_output": case.expected_output,
        "input_fingerprint": case.input_fingerprint,
        "expected_output_fingerprint": case.expected_output_fingerprint,
        "legal_source_hash": case.legal_source_hash,
        "legal_article": case.legal_article,
        "legal_clause": case.legal_clause,
    }


def _reject_duplicate_json_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate keys before Python's JSON decoder can silently overwrite them."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def load_cases(rule_pack_version: str) -> tuple[RegressionCase, ...]:
    _validate_rule_pack_version(rule_pack_version)
    path = _REPOSITORY_ROOT / rule_pack_version / "cases.json"
    if not path.is_file():
        return ()
    raw = json.loads(\n        path.read_text(encoding="utf-8"),\n        object_pairs_hook=_reject_duplicate_json_object_keys,\n    )
    if not isinstance(raw, list):
        raise ValueError("golden case repository must contain a JSON list")
    cases: list[RegressionCase] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("golden regression cases must be JSON objects")
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        values = item.get("input_values", {})
        if not isinstance(values, dict):
            raise ValueError("input_values must be an object")
        expected_output = item.get("expected_output")
        if expected_output is not None and not isinstance(expected_output, dict):
            raise ValueError("expected_output must be an object or null")
        if expected_output is not None:
            _validate_finite_json(expected_output)
        cases.append(
            RegressionCase(
                case_id=case_id,
                rule_pack_version=_required_text(item, "rule_pack_version"),
                component_code=_required_text(item, "component_code"),
                population_scope=_required_text(item, "population_scope"),
                effective_date=_required_text(item, "effective_date"),
                status=_required_text(item, "status"),
                input_values=_decimal_input_values(values),
                expected_output=expected_output,
                input_fingerprint=_optional_text(item, "input_fingerprint"),
                expected_output_fingerprint=_optional_text(item, "expected_output_fingerprint"),
                legal_source_hash=_optional_text(item, "legal_source_hash"),
                legal_article=_optional_text(item, "legal_article"),
                legal_clause=_optional_text(item, "legal_clause"),
            )
        )
    return tuple(cases)


def regression_suite_hash(rule_pack_version: str) -> str:
    cases = load_cases(rule_pack_version)
    canonical = [_canonical_case(case) for case in cases]
    payload = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_repository(rule_pack_version: str, *, required_components: tuple[str, ...] = ()) -> tuple[str, ...]:
    cases = load_cases(rule_pack_version)
    blockers: list[str] = []
    required = required_components or REQUIRED_1405_COMPONENTS

    # همه نمونه‌ها را حفظ می‌کنیم تا سناریوی بعدی، نمونه قبلی همان مؤلفه را بی‌صدا جایگزین نکند.
    cases_by_component: dict[str, list[RegressionCase]] = {}
    seen_case_ids: set[str] = set()
    for case in cases:
        if case.case_id in seen_case_ids:
            blockers.append(f"duplicate golden case_id {case.case_id}")
        seen_case_ids.add(case.case_id)
        cases_by_component.setdefault(case.component_code, []).append(case)

    for component in required:
        if not cases_by_component.get(component):
            blockers.append(f"missing golden regression case for component {component}")

    # همه نمونه‌های مخزن باید اعتبارسنجی شوند، حتی اگر مؤلفه‌ای در فهرست اجباری صریح نیامده باشد.
    for case in cases:
        if not case.case_id.strip():
            blockers.append("golden case has an empty case_id")
        if case.rule_pack_version != rule_pack_version:
            blockers.append(f"golden case {case.case_id} has a mismatched rule-pack version")
        if case.status not in _ALLOWED_STATUSES:
            blockers.append(f"golden case {case.case_id} has an invalid status")
        if case.status not in {"approved", "published"}:
            blockers.append(f"golden case {case.case_id} is not approved")
        if not case.population_scope.strip():
            blockers.append(f"golden case {case.case_id} requires population_scope")
        if not case.input_values:
            blockers.append(f"golden case {case.case_id} has no governed input values")
        elif case.input_fingerprint is None:
            blockers.append(f"golden case {case.case_id} is missing input_fingerprint")
        elif not _is_hex64(case.input_fingerprint):
            blockers.append(f"golden case {case.case_id} has an invalid input fingerprint")
        elif fingerprint_values(case.input_values) != case.input_fingerprint:
            blockers.append(f"golden case {case.case_id} input fingerprint mismatch")
        if case.expected_output is None:
            blockers.append(f"golden case {case.case_id} is missing expected output")
        if not case.expected_output_fingerprint:
            blockers.append(f"golden case {case.case_id} is missing expected output fingerprint")
        elif not _is_hex64(case.expected_output_fingerprint):
            blockers.append(f"golden case {case.case_id} has an invalid expected output fingerprint")
        if not case.legal_source_hash:
            blockers.append(f"golden case {case.case_id} is missing legal_source_hash")
        elif not _is_hex64(case.legal_source_hash):
            blockers.append(f"golden case {case.case_id} has an invalid legal_source_hash")
        if not case.legal_article or not case.legal_article.strip():
            blockers.append(f"golden case {case.case_id} is missing legal_article")
    return tuple(blockers)


def validate_repository_against_evidence(
    session: Session,
    rule_pack_version: str,
    *,
    required_components: tuple[str, ...] = (),
) -> tuple[str, ...]:
    blockers = list(validate_repository(rule_pack_version, required_components=required_components))
    cases_by_component: dict[str, list[RegressionCase]] = {}
    for case in load_cases(rule_pack_version):
        cases_by_component.setdefault(case.component_code, []).append(case)

    # شواهد هر مؤلفه‌ای که در مخزن نمونه دارد باید بررسی شود؛ نه فقط مؤلفه‌های اجباری.
    for component, component_cases in cases_by_component.items():
        evidence = session.scalar(
            select(RuleEvidenceRecord).where(
                RuleEvidenceRecord.rule_pack_version == rule_pack_version,
                RuleEvidenceRecord.component_code == component,
            )
        )
        if evidence is None:
            blockers.extend(
                f"missing rule evidence for golden case {case.case_id}" for case in component_cases
            )
            continue
        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        if source is None:
            blockers.extend(
                f"missing legal source for golden case {case.case_id}" for case in component_cases
            )
            continue

        # شواهد همان مؤلفه را برای تک‌تک نمونه‌ها بررسی می‌کنیم؛ هیچ نمونه‌ای نباید نادیده گرفته شود.
        for case in component_cases:
            if case.legal_source_hash and case.legal_source_hash != evidence.source_hash:
                blockers.append(f"golden case {case.case_id} source hash mismatch")
            if case.legal_source_hash and case.legal_source_hash != source.document_hash:
                blockers.append(f"golden case {case.case_id} legal source hash mismatch")
            if case.legal_article and case.legal_article.strip() != evidence.article.strip():
                blockers.append(f"golden case {case.case_id} article mismatch")
            if (case.legal_clause or "").strip() != (evidence.clause or "").strip():
                blockers.append(f"golden case {case.case_id} clause mismatch")
            if case.population_scope.strip() != evidence.population_scope.strip():
                blockers.append(f"golden case {case.case_id} population scope mismatch")
            if evidence.status not in {"approved", "published"}:
                blockers.append(f"rule evidence for golden case {case.case_id} is not approved")
            if source.status not in {"approved", "published"}:
                blockers.append(f"legal source for golden case {case.case_id} is not approved")
    return tuple(blockers)


def verify_expected_result(case: RegressionCase, actual_result: object) -> None:
    if not _is_hex64(case.expected_output_fingerprint):
        raise ValueError(f"golden case {case.case_id} has no valid expected output fingerprint")
    actual = fingerprint_rule_result(actual_result)
    if actual != case.expected_output_fingerprint:
        raise ValueError(f"golden case {case.case_id} output fingerprint mismatch")
