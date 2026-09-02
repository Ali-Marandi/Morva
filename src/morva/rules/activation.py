from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import RuleEvidenceRecord
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
    by_component = {item.component_code: item for item in evidences if item.status in {"approved", "published"}}
    missing = sorted(component_codes - set(by_component))
    if missing:
        raise RuleActivationBlocked(f"Rule Pack evidence is incomplete for components: {missing}")
    for evidence in by_component.values():
        if not evidence.source_hash or not evidence.article or not evidence.issuer or not evidence.population_scope:
            raise RuleActivationBlocked(f"incomplete legal evidence for component {evidence.component_code}")
        if not evidence.regression_suite_hash:
            raise RuleActivationBlocked(f"regression evidence is missing for component {evidence.component_code}")
