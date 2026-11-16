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
from morva.persistence.models import RulePackRecord
from morva.rules.activation import RuleActivationBlocked, require_authoritative_pack
from morva.rules.engine import RuleDefinition
from morva.rules.regression import (
    canonical_expected_result_payload,
    fingerprint_expected_result_payload,
    fingerprint_values,
)
from morva.rules.regression_cases import (
    RegressionCase,
    load_cases,
    regression_suite_hash,
    validate_repository_against_evidence,
)
from morva.security.policy import require_distinct_actors
from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS, is_1405_rule_pack

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ALLOWED_OPS = {"const", "value", "add", "sub", "mul", "div", "min", "max"}
_TREATMENTS = {"earning", "deduction", "informational"}
_REQUIRED_TREATMENT_FLAGS = {"taxable", "pensionable", "insurable"}
_REGRESSION_COMPONENTS_1405 = ("TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER")


@dataclass(frozen=True, slots=True)
class MatrixReadiness:
    ready: bool
    blockers: tuple[str, ...]
    entry_count: int

    def as_dict(self) -> dict[str, object]:
        return {"ready": self.ready, "blockers": list(self.blockers), "entry_count": self.entry_count}


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


def _expression_value_names(node: dict[str, object]) -> set[str]:
    """Collect every value-node input name recursively from a validated expression."""
    operation = node.get("op")
    if operation == "const":
        return set()
    if operation == "value":
        name = node.get("name")
        return {name} if isinstance(name, str) else set()

    names: set[str] = set()
    args = node.get("args")
    if isinstance(args, list):
        for child in args:
            if isinstance(child, dict):
                names.update(_expression_value_names(child))
    return names


def validate_matrix_payload(*, treatment: str, effective_from: date, effective_to: date | None, regression_suite_hash: str, expression: dict[str, object], legal_article: str, population_scope: str, taxable: object | None = None, pensionable: object | None = None, insurable: object | None = None) -> None:
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
    for name, value in (("taxable", taxable), ("pensionable", pensionable), ("insurable", insurable)):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be explicitly provided as a boolean")
    _validate_expression(expression)


def approve_matrix_entry(entry: CalculationMatrixRecord, approver_id: str) -> None:
    if entry.status != "reviewed":
        raise ValueError("calculation-matrix entry must be reviewed before approval")
    if not entry.reviewed_by or entry.reviewed_at is None:
        raise ValueError("calculation-matrix entry review actor and timestamp are required")
    require_distinct_actors([entry.reviewed_by, approver_id])
    entry.status = "approved"
    entry.approved_by = approver_id
    entry.approved_at = datetime.utcnow()


def matrix_readiness(session: Session, rule_pack_version: str) -> MatrixReadiness:
    entries = session.scalars(select(CalculationMatrixRecord).where(CalculationMatrixRecord.rule_pack_version == rule_pack_version)).all()
    blockers: list[str] = []
    component_codes = {entry.component_code for entry in entries}
    if not entries:
        blockers.append("no calculation-matrix entries are registered for this rule pack")
    if is_1405_rule_pack(rule_pack_version):
        missing = [code for code in REQUIRED_1405_COMPONENTS if code not in component_codes]
        blockers.extend(f"missing required 1405 matrix component {code}" for code in missing)
        blockers.extend(validate_repository_against_evidence(session, rule_pack_version, required_components=_REGRESSION_COMPONENTS_1405))
    for entry in entries:
        source = session.get(LegalSourceRecord, entry.legal_source_id)
        evidence = session.scalar(select(RuleEvidenceRecord).where(RuleEvidenceRecord.rule_pack_version == entry.rule_pack_version, RuleEvidenceRecord.component_code == entry.component_code))
        if source is None:
            blockers.append(f"missing legal source for component {entry.component_code}")
            continue
        if source.status not in {"approved", "published"}:
            blockers.append(f"legal source for component {entry.component_code} is not approved")
        if evidence is None:
            blockers.append(f"missing rule evidence for component {entry.component_code}")
        else:
            if evidence.status not in {"approved", "published"}:
                blockers.append(f"rule evidence for component {entry.component_code} is not approved")
            if evidence.source_hash != source.document_hash:
                blockers.append(f"source hash mismatch for component {entry.component_code}")
            if evidence.regression_suite_hash != entry.regression_suite_hash:
                blockers.append(f"regression hash mismatch for component {entry.component_code}")
            if evidence.article.strip() != entry.legal_article.strip():
                blockers.append(f"legal article mismatch for component {entry.component_code}")
            if evidence.population_scope.strip() != entry.population_scope.strip():
                blockers.append(f"population scope mismatch for component {entry.component_code}")
        if entry.status != "approved":
            blockers.append(f"calculation-matrix entry for component {entry.component_code} is not approved")
        if not entry.reviewed_by or not entry.reviewed_at:
            blockers.append(f"review provenance is incomplete for component {entry.component_code}")
        if not entry.approved_by or not entry.approved_at:
            blockers.append(f"approval provenance is incomplete for component {entry.component_code}")
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
    evidence = session.scalar(select(RuleEvidenceRecord).where(RuleEvidenceRecord.rule_pack_version == version, RuleEvidenceRecord.component_code == component))
    if evidence is None:
        raise ValueError("rule evidence must be registered before calculation-matrix entry")
    if source.status not in {"approved", "published"} or evidence.status not in {"approved", "published"}:
        raise ValueError("legal source and rule evidence must both be approved or published")
    if evidence.source_hash != source.document_hash:
        raise ValueError("rule evidence source hash does not match legal source")
    if evidence.regression_suite_hash != payload["regression_suite_hash"]:
        raise ValueError("regression_suite_hash must match rule evidence")
    if evidence.article.strip() != str(payload["legal_article"]).strip():
        raise ValueError("legal_article must match rule evidence")
    if evidence.population_scope.strip() != population.strip():
        raise ValueError("population_scope must match rule evidence")
    if not actor_id.strip():
        raise ValueError("actor_id is required")
    missing_flags = sorted(_REQUIRED_TREATMENT_FLAGS - payload.keys())
    if missing_flags:
        raise ValueError(f"explicit treatment flags are required: {missing_flags}")
    validate_matrix_payload(treatment=str(payload["treatment"]), effective_from=payload["effective_from"], effective_to=payload.get("effective_to"), regression_suite_hash=str(payload["regression_suite_hash"]), expression=payload["expression"], legal_article=str(payload["legal_article"]), population_scope=population, taxable=payload["taxable"], pensionable=payload["pensionable"], insurable=payload["insurable"])
    entry = CalculationMatrixRecord(**payload)
    session.add(entry)
    session.flush()
    append_audit_event(event_type="rule.matrix.created", entity_type="calculation_matrix", entity_id=str(entry.id), actor_id=actor_id, payload={"rule_pack_version": version, "component_code": component, "population_scope": population}, reason="register calculation matrix entry", session=session)
    return entry



class MatrixResolutionError(ValueError):
    """A Rule Pack/component/population/date mapping cannot be resolved safely."""


def _sha256_matches(left: object, right: object) -> bool:
    return (
        isinstance(left, str)
        and isinstance(right, str)
        and _HEX64.fullmatch(left) is not None
        and _HEX64.fullmatch(right) is not None
        and left.lower() != "0" * 64
        and right.lower() != "0" * 64
        and left.lower() == right.lower()
    )


def _select_active_matrix_entry(
    entries: list[CalculationMatrixRecord],
    *,
    rule_pack_version: str,
    component_code: str,
    population_scope: str,
    effective_on: date,
) -> CalculationMatrixRecord:
    """Select exactly one entry by exact keys and inclusive effective-date bounds."""
    if type(effective_on) is not date:
        raise MatrixResolutionError(
            "effective_on must be an explicit date supplied by an approved calendar adapter"
        )

    keyed = [
        entry
        for entry in entries
        if entry.rule_pack_version == rule_pack_version
        and entry.component_code == component_code
        and entry.population_scope == population_scope
    ]
    if not keyed:
        raise MatrixResolutionError(
            "no calculation-matrix mapping for the exact Rule Pack, component and population"
        )

    for entry in keyed:
        if type(entry.effective_from) is not date:
            raise MatrixResolutionError("matrix effective_from must be a date")
        if entry.effective_to is not None and type(entry.effective_to) is not date:
            raise MatrixResolutionError("matrix effective_to must be a date or null")

    active = [
        entry
        for entry in keyed
        if entry.effective_from <= effective_on
        and (entry.effective_to is None or effective_on <= entry.effective_to)
    ]
    if not active:
        raise MatrixResolutionError(
            "no calculation-matrix entry is effective on the supplied date"
        )
    if len(active) != 1:
        raise MatrixResolutionError(
            "ambiguous calculation-matrix mapping: more than one entry is effective"
        )
    return active[0]


def resolve_rule_definition_for_case(
    session: Session,
    case: RegressionCase,
    *,
    effective_on: date,
) -> RuleDefinition:
    """Resolve one approved matrix row into a RuleDefinition for a loaded Golden Case.

    This function deliberately does not parse or convert case.effective_date. The caller
    must preserve that original source string and supply effective_on from an independently
    approved calendar adapter. No Jalali/Gregorian conversion is performed here.
    """
    if not isinstance(case, RegressionCase):
        raise MatrixResolutionError("case must be a loaded RegressionCase")
    if type(effective_on) is not date:
        raise MatrixResolutionError(
            "effective_on must be an explicit date supplied by an approved calendar adapter"
        )
    if case.status not in {"approved", "published"}:
        raise MatrixResolutionError("golden case is not approved/published")
    if (
        not isinstance(case.case_id, str)
        or not case.case_id.strip()
        or not isinstance(case.effective_date, str)
        or not case.effective_date.strip()
    ):
        raise MatrixResolutionError("golden case identity and source effective date are required")
    try:
        canonical_cases = load_cases(case.rule_pack_version)
    except (OSError, ValueError) as exc:
        raise MatrixResolutionError("canonical golden case repository cannot be loaded") from exc
    matching_cases = [item for item in canonical_cases if item.case_id == case.case_id]
    if len(matching_cases) != 1:
        raise MatrixResolutionError(
            "golden case must occur exactly once in the canonical repository"
        )
    if matching_cases[0] != case:
        raise MatrixResolutionError(
            "golden case payload does not match its canonical repository entry"
        )
    case = matching_cases[0]
    if not case.input_values:
        raise MatrixResolutionError("golden case has no governed input values")
    if not _sha256_matches(fingerprint_values(case.input_values), case.input_fingerprint):
        raise MatrixResolutionError("golden case input fingerprint is invalid or mismatched")
    if case.expected_output is None:
        raise MatrixResolutionError("golden case expected output is missing")
    try:
        expected_payload = canonical_expected_result_payload(case.expected_output)
    except ValueError as exc:
        raise MatrixResolutionError(f"golden case expected output is invalid: {exc}") from exc
    expected_fingerprint = fingerprint_expected_result_payload(expected_payload)
    if not _sha256_matches(expected_fingerprint, case.expected_output_fingerprint):
        raise MatrixResolutionError("golden case expected-output fingerprint is invalid or mismatched")

    pack = session.scalar(
        select(RulePackRecord).where(RulePackRecord.version == case.rule_pack_version)
    )
    if pack is None:
        raise MatrixResolutionError("Rule Pack is not registered")
    entries = session.scalars(
        select(CalculationMatrixRecord).where(
            CalculationMatrixRecord.rule_pack_version == case.rule_pack_version,
        )
    ).all()
    entry = _select_active_matrix_entry(
        list(entries),
        rule_pack_version=case.rule_pack_version,
        component_code=case.component_code,
        population_scope=case.population_scope,
        effective_on=effective_on,
    )
    if entry.status != "approved":
        raise MatrixResolutionError("calculation-matrix entry is not approved")
    if (
        not entry.reviewed_by
        or entry.reviewed_at is None
        or not entry.approved_by
        or entry.approved_at is None
        or entry.reviewed_by == entry.approved_by
    ):
        raise MatrixResolutionError("calculation-matrix review/approval provenance is incomplete")

    try:
        require_authoritative_pack(
            session,
            pack=pack,
            component_codes={case.component_code},
        )
    except RuleActivationBlocked as exc:
        raise MatrixResolutionError(f"Rule Pack evidence is not activation-ready: {exc}") from exc

    evidence = session.scalar(
        select(RuleEvidenceRecord).where(
            RuleEvidenceRecord.rule_pack_version == case.rule_pack_version,
            RuleEvidenceRecord.component_code == case.component_code,
        )
    )
    if evidence is None:
        raise MatrixResolutionError("registered rule evidence is missing")
    source = session.get(LegalSourceRecord, entry.legal_source_id)
    if source is None or evidence.legal_source_id != entry.legal_source_id:
        raise MatrixResolutionError("matrix and rule evidence do not reference the same legal source")
    if not _sha256_matches(source.document_hash, evidence.source_hash):
        raise MatrixResolutionError("legal-source and rule-evidence hashes do not match")
    if not _sha256_matches(case.legal_source_hash, source.document_hash):
        raise MatrixResolutionError("golden case legal-source hash does not match the approved source")
    if not _sha256_matches(entry.regression_suite_hash, evidence.regression_suite_hash):
        raise MatrixResolutionError("matrix and rule-evidence suite hashes do not match")
    try:
        current_suite_hash = regression_suite_hash(case.rule_pack_version)
    except (OSError, ValueError) as exc:
        raise MatrixResolutionError("canonical golden case suite cannot be fingerprinted") from exc
    if not _sha256_matches(current_suite_hash, evidence.regression_suite_hash):
        raise MatrixResolutionError(
            "rule evidence regression suite hash does not match the canonical repository"
        )
    if not _sha256_matches(entry.regression_suite_hash, current_suite_hash):
        raise MatrixResolutionError(
            "calculation-matrix suite hash does not match the canonical repository"
        )
    if (
        entry.legal_article.strip() != evidence.article.strip()
        or (entry.legal_clause or "").strip() != (evidence.clause or "").strip()
        or entry.population_scope.strip() != evidence.population_scope.strip()
    ):
        raise MatrixResolutionError("matrix metadata does not match registered rule evidence")
    if (
        not case.legal_article
        or case.legal_article.strip() != evidence.article.strip()
        or (case.legal_clause or "").strip() != (evidence.clause or "").strip()
        or case.population_scope.strip() != evidence.population_scope.strip()
    ):
        raise MatrixResolutionError("golden case legal metadata does not match registered evidence")
    if not source.citation or not source.citation.strip():
        raise MatrixResolutionError("legal source citation is missing")
    if expected_payload["code"] != case.component_code:
        raise MatrixResolutionError("expected output code does not match the golden component")
    if expected_payload["rule_version"] != case.rule_pack_version:
        raise MatrixResolutionError("expected output rule version does not match the Rule Pack")
    if expected_payload["legal_reference"] != source.citation:
        raise MatrixResolutionError("expected output legal reference does not match the source citation")
    if (
        expected_payload["taxable"] != entry.taxable
        or expected_payload["pensionable"] != entry.pensionable
        or expected_payload["insurable"] != entry.insurable
    ):
        raise MatrixResolutionError("expected output classifications do not match the approved matrix")

    readiness = matrix_readiness(session, case.rule_pack_version)
    if not readiness.ready:
        details = "; ".join(readiness.blockers)
        raise MatrixResolutionError(f"calculation matrix is not ready: {details}")

    validate_matrix_payload(
        treatment=entry.treatment,
        effective_from=entry.effective_from,
        effective_to=entry.effective_to,
        regression_suite_hash=entry.regression_suite_hash,
        expression=entry.expression,
        legal_article=entry.legal_article,
        population_scope=entry.population_scope,
        taxable=entry.taxable,
        pensionable=entry.pensionable,
        insurable=entry.insurable,
    )
    required_inputs = _expression_value_names(entry.expression)
    missing_inputs = sorted(required_inputs - set(case.input_values))
    if missing_inputs:
        raise MatrixResolutionError(
            f"golden case is missing required rule inputs: {missing_inputs}"
        )
    if pack.effective_from is not None and effective_on < pack.effective_from:
        raise MatrixResolutionError("supplied date precedes the Rule Pack effective period")
    if pack.effective_to is not None and effective_on > pack.effective_to:
        raise MatrixResolutionError("supplied date follows the Rule Pack effective period")

    return RuleDefinition(
        code=entry.component_code,
        title=entry.component_code,
        effective_from=entry.effective_from,
        effective_to=entry.effective_to,
        taxable=entry.taxable,
        pensionable=entry.pensionable,
        insurable=entry.insurable,
        expression=dict(entry.expression),
        legal_reference=source.citation,
        rule_version=entry.rule_pack_version,
        review_status=entry.status,
        regression_case_ids=(case.case_id,),
    )
