from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord

from .regression import fingerprint_rule_result, fingerprint_values
from .rule_pack_1405 import REQUIRED_1405_COMPONENTS

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3] / "docs" / "legal" / "golden-cases"
_ALLOWED_STATUSES = {"review_required", "approved", "published"}
_HEX64 = set("0123456789abcdefABCDEF")


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


def load_cases(rule_pack_version: str) -> tuple[RegressionCase, ...]:
    path = _REPOSITORY_ROOT / rule_pack_version / "cases.json"
    if not path.is_file():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("golden case repository must contain a JSON list")
    cases: list[RegressionCase] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("golden regression cases must be JSON objects")
        values = item.get("input_values", {})
        if not isinstance(values, dict):
            raise ValueError("input_values must be an object")
        cases.append(
            RegressionCase(
                case_id=str(item["case_id"]),
                rule_pack_version=str(item["rule_pack_version"]),
                component_code=str(item["component_code"]),
                population_scope=str(item["population_scope"]),
                effective_date=str(item["effective_date"]),
                status=str(item["status"]),
                input_values={key: Decimal(str(value)) for key, value in values.items()},
                expected_output=item.get("expected_output"),
                input_fingerprint=item.get("input_fingerprint"),
                expected_output_fingerprint=item.get("expected_output_fingerprint"),
                legal_source_hash=item.get("legal_source_hash"),
                legal_article=item.get("legal_article"),
                legal_clause=item.get("legal_clause"),
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
    by_component = {case.component_code: case for case in cases}
    for component in required:
        case = by_component.get(component)
        if case is None:
            blockers.append(f"missing golden regression case for component {component}")
            continue
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
        elif fingerprint_values(case.input_values) != case.input_fingerprint:
            blockers.append(f"golden case {case.case_id} input fingerprint mismatch")
        if case.expected_output is None:
            blockers.append(f"golden case {case.case_id} is missing expected output")
        if not case.expected_output_fingerprint:
            blockers.append(f"golden case {case.case_id} is missing expected output fingerprint")
        if not case.legal_source_hash:
            blockers.append(f"golden case {case.case_id} is missing legal_source_hash")
        elif len(case.legal_source_hash) != 64 or not set(case.legal_source_hash) <= _HEX64:
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
    required = required_components or REQUIRED_1405_COMPONENTS
    cases = {case.component_code: case for case in load_cases(rule_pack_version)}
    for component in required:
        case = cases.get(component)
        if case is None:
            continue
        evidence = session.scalar(
            select(RuleEvidenceRecord).where(
                RuleEvidenceRecord.rule_pack_version == rule_pack_version,
                RuleEvidenceRecord.component_code == component,
            )
        )
        if evidence is None:
            blockers.append(f"missing rule evidence for golden case {case.case_id}")
            continue
        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        if source is None:
            blockers.append(f"missing legal source for golden case {case.case_id}")
            continue
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
    if case.expected_output_fingerprint is None:
        raise ValueError(f"golden case {case.case_id} has no expected output fingerprint")
    actual = fingerprint_rule_result(actual_result)
    if actual != case.expected_output_fingerprint:
        raise ValueError(f"golden case {case.case_id} output fingerprint mismatch")
