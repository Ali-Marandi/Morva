from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.security.policy import require_distinct_actors

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_OPS = {"const", "value", "add", "sub", "mul", "div", "min", "max"}
_TREATMENTS = {"earning", "deduction", "informational"}


@dataclass(frozen=True, slots=True)
class MatrixReadiness:
    ready: bool
    blockers: tuple[str, ...]
    entry_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "ready": self.ready,
            "blockers": list(self.blockers),
            "entry_count": self.entry_count,
        }


def _validate_expression(node: object) -> None:
    if not isinstance(node, dict):
        raise ValueError("expression nodes must be objects")
    op = node.get("op")
    if op not in _ALLOWED_OPS:
        raise ValueError(f"unsupported calculation-matrix expression operation: {op}")
    if op == "const":
        if "value" not in node:
            raise ValueError("const expression requires value")
        return
    if op == "value":
        if not isinstance(node.get("name"), str) or not node["name"].strip():
            raise ValueError("value expression requires a non-empty name")
        return
    args = node.get("args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"{op} expression requires a non-empty args list")
    if op in {"sub", "div"} and len(args) != 2:
        raise ValueError(f"{op} expression requires exactly two arguments")
    for child in args:
        _validate_expression(child)


def validate_matrix_payload(
    *,
    treatment: str,
    effective_from: date,
    effective_to: date | None,
    regression_suite_hash: str,
    expression: dict[str, object],
    legal_article: str,
    population_scope: str,
) -> None:
    if treatment not in _TREATMENTS:
        raise ValueError("treatment must be earning, deduction or informational")
    if effective_to is not None and effective_to < effective_from:
        raise ValueError("effective_to cannot precede effective_from")
    if not _HEX64.fullmatch(regression_suite_hash):
        raise ValueError("regression_suite_hash must be a 64-character hexadecimal SHA-256")
    if not legal_article.strip():
        raise ValueError("legal_article is required")
    if not population_scope.strip():
        raise ValueError("population_scope is required")
    _validate_expression(expression)


def approve_matrix_entry(entry: CalculationMatrixRecord, approver_id: str) -> None:
    if entry.status != "reviewed":
        raise ValueError("calculation-matrix entry must be reviewed before approval")
    require_distinct_actors([entry.reviewed_by, approver_id])
    entry.status = "approved"
    entry.approved_by = approver_id
    entry.approved_at = datetime.utcnow()


def matrix_readiness(session: Session, rule_pack_version: str) -> MatrixReadiness:
    entries = session.scalars(
        select(CalculationMatrixRecord).where(
            CalculationMatrixRecord.rule_pack_version == rule_pack_version
        )
    ).all()
    blockers: list[str] = []
    if not entries:
        blockers.append("no calculation-matrix entries are registered for this rule pack")
    for entry in entries:
        source = session.get(LegalSourceRecord, entry.legal_source_id)
        evidence = session.scalar(
            select(RuleEvidenceRecord).where(
                RuleEvidenceRecord.rule_pack_version == entry.rule_pack_version,
                RuleEvidenceRecord.component_code == entry.component_code,
            )
        )
        if source is None:
            blockers.append(f"missing legal source for component {entry.component_code}")
            continue
        if source.status != "approved":
            blockers.append(f"legal source for component {entry.component_code} is not approved")
        if evidence is None:
            blockers.append(f"missing rule evidence for component {entry.component_code}")
        else:
            if evidence.status != "approved":
                blockers.append(f"rule evidence for component {entry.component_code} is not approved")
            if evidence.source_hash != source.document_hash:
                blockers.append(f"source hash mismatch for component {entry.component_code}")
            if evidence.regression_suite_hash != entry.regression_suite_hash:
                blockers.append(f"regression hash mismatch for component {entry.component_code}")
        if entry.status != "approved":
            blockers.append(f"calculation-matrix entry for component {entry.component_code} is not approved")
        if entry.reviewed_by and entry.approved_by and entry.reviewed_by == entry.approved_by:
            blockers.append(f"reviewer and approver must be distinct for component {entry.component_code}")
    return MatrixReadiness(not blockers, tuple(blockers), len(entries))


def create_matrix_entry(session: Session, payload: dict[str, object], actor_id: str) -> CalculationMatrixRecord:
    version = str(payload["rule_pack_version"])
    component = str(payload["component_code"])
    population = str(payload["population_scope"])
    legal_source_id = UUID(str(payload["legal_source_id"]))
    source = session.get(LegalSourceRecord, legal_source_id)
    if source is None:
        raise ValueError("legal source not found")
    evidence = session.scalar(
        select(RuleEvidenceRecord).where(
            RuleEvidenceRecord.rule_pack_version == version,
            RuleEvidenceRecord.component_code == component,
        )
    )
    if evidence is None:
        raise ValueError("rule evidence must be registered before calculation-matrix entry")
    if source.status != "approved" or evidence.status != "approved":
        raise ValueError("legal source and rule evidence must both be approved")
    if evidence.source_hash != source.document_hash:
        raise ValueError("rule evidence source hash does not match legal source")
    if evidence.regression_suite_hash != payload["regression_suite_hash"]:
        raise ValueError("regression_suite_hash must match rule evidence")
    entry = CalculationMatrixRecord(**payload)
    session.add(entry)
    session.flush()
    append_audit_event(
        event_type="rule.matrix.created",
        entity_type="calculation_matrix",
        entity_id=str(entry.id),
        actor_id=actor_id,
        payload={"rule_pack_version": version, "component_code": component, "population_scope": population},
        reason="register calculation matrix entry",
        session=session,
    )
    return entry
