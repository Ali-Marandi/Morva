from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import RulePackRecord


class RuleActivationBlocked(RuntimeError):
    pass


def require_authoritative_pack(
    session: Session,
    *,
    pack: RulePackRecord,
    component_codes: set[str],
) -> None:
    if pack.status not in {"approved", "published"}:
        raise RuleActivationBlocked("Rule Pack is not approved/published")
    if not pack.rules_hash or not pack.legal_source_hash:
        raise RuleActivationBlocked("Rule Pack is missing immutable source/rules hashes")
    evidences = session.scalars(
        select(RuleEvidenceRecord).where(
            RuleEvidenceRecord.rule_pack_version == pack.version,
            RuleEvidenceRecord.component_code.in_(component_codes),
        )
    ).all()
    by_component = {
        item.component_code: item
        for item in evidences
        if item.status in {"approved", "published"}
    }
    missing = sorted(component_codes - set(by_component))
    if missing:
        raise RuleActivationBlocked(f"Rule Pack evidence is incomplete for components: {missing}")

    for evidence in by_component.values():
        if not evidence.source_hash or not evidence.article or not evidence.issuer or not evidence.population_scope:
            raise RuleActivationBlocked(f"incomplete legal evidence for component {evidence.component_code}")
        if not evidence.regression_suite_hash:
            raise RuleActivationBlocked(f"regression evidence is missing for component {evidence.component_code}")
        if not evidence.reviewed_by or not evidence.approved_by or evidence.reviewed_by == evidence.approved_by:
            raise RuleActivationBlocked(
                f"reviewer and approver must be distinct for component {evidence.component_code}"
            )
        if evidence.approved_at is None:
            raise RuleActivationBlocked(f"approval timestamp is missing for component {evidence.component_code}")

        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        if source is None:
            raise RuleActivationBlocked(f"legal source is missing for component {evidence.component_code}")
        if source.status not in {"approved", "published"}:
            raise RuleActivationBlocked(f"legal source is not approved for component {evidence.component_code}")
        if source.document_hash != evidence.source_hash:
            raise RuleActivationBlocked(f"source hash mismatch for component {evidence.component_code}")


def require_production_rule_pack(
    session: Session,
    *,
    pack: RulePackRecord,
    as_of: date,
    component_codes: set[str],
) -> None:
    """Require a fully governed Rule Pack before production payroll calculation."""
    require_authoritative_pack(session, pack=pack, component_codes=component_codes)
    if pack.effective_from is None:
        raise RuleActivationBlocked("Rule Pack effective_from is required for production activation")
    if pack.effective_to is not None and pack.effective_to < pack.effective_from:
        raise RuleActivationBlocked("Rule Pack effective_to cannot precede effective_from")
    if as_of < pack.effective_from or (pack.effective_to is not None and as_of > pack.effective_to):
        raise RuleActivationBlocked(f"Rule Pack {pack.version} is not effective for payroll date {as_of.isoformat()}")
    from morva.rules.calculation_matrix import matrix_readiness
    readiness = matrix_readiness(session, pack.version)
    if not readiness.ready:
        raise RuleActivationBlocked("Rule Pack calculation-matrix readiness is blocked: " + "; ".join(readiness.blockers))
    from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
    matrix_entries = session.scalars(
        select(CalculationMatrixRecord).where(
            CalculationMatrixRecord.rule_pack_version == pack.version,
            CalculationMatrixRecord.component_code.in_(component_codes),
        )
    ).all()
    for entry in matrix_entries:
        if as_of < entry.effective_from or (entry.effective_to is not None and as_of > entry.effective_to):
            raise RuleActivationBlocked(
                f"calculation matrix for component {entry.component_code} is not effective on {as_of.isoformat()}"
            )
    evidences = session.scalars(select(RuleEvidenceRecord).where(
        RuleEvidenceRecord.rule_pack_version == pack.version,
        RuleEvidenceRecord.component_code.in_(component_codes),
    )).all()
    for evidence in evidences:
        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        if source is None:
            raise RuleActivationBlocked(f"legal source is missing for component {evidence.component_code}")
        source_from = date.fromisoformat(source.effective_from)
        source_to = date.fromisoformat(source.effective_to) if source.effective_to else None
        if as_of < source_from or (source_to is not None and as_of > source_to):
            raise RuleActivationBlocked(f"legal source for component {evidence.component_code} is not effective on {as_of.isoformat()}")
