from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.domain_extensions import TeacherRankCaseRecord
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True, slots=True)
class TeacherRankEvidenceResult:
    ready: bool
    blockers: tuple[str, ...]
    legal_source_id: UUID | None = None
    evidence_id: UUID | None = None


def _parse_period(value: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        return None
    year, month = (int(part) for part in value.split("-"))
    if not 1 <= month <= 12:
        return None
    return date(year, month, 1)


def check_teacher_rank_evidence(
    session: Session,
    case: TeacherRankCaseRecord,
) -> TeacherRankEvidenceResult:
    blockers: list[str] = []
    effect_period = _parse_period(case.effect_period)
    if effect_period is None:
        blockers.append("teacher rank effect_period must use YYYY-MM")

    component_code = f"teacher_rank:{case.proposed_rank.strip()}"
    candidates = session.scalars(
        select(RuleEvidenceRecord)
        .where(RuleEvidenceRecord.component_code == component_code)
        .order_by(RuleEvidenceRecord.approved_at.desc(), RuleEvidenceRecord.id)
    ).all()
    if not candidates:
        return TeacherRankEvidenceResult(
            ready=False,
            blockers=(f"no approved evidence is registered for {component_code}",),
        )

    for evidence in candidates:
        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        candidate_blockers: list[str] = []
        if source is None:
            candidate_blockers.append("legal source is missing")
        else:
            if source.status != "approved":
                candidate_blockers.append("legal source is not approved")
            if not _HEX64.fullmatch(source.document_hash):
                candidate_blockers.append("legal source document hash is invalid")
            if evidence.source_hash != source.document_hash:
                candidate_blockers.append("evidence source hash does not match legal source")
            try:
                source_from = date.fromisoformat(source.effective_from)
                source_to = date.fromisoformat(source.effective_to) if source.effective_to else None
            except ValueError:
                candidate_blockers.append("legal source has invalid effective dates")
            else:
                if source_to is not None and source_to < source_from:
                    candidate_blockers.append("legal source effective_to precedes effective_from")
                if effect_period is not None and effect_period < source_from:
                    candidate_blockers.append("teacher rank effect period predates legal source")
                if effect_period is not None and source_to is not None and effect_period > source_to:
                    candidate_blockers.append("teacher rank effect period exceeds legal source")

        if evidence.status != "approved":
            candidate_blockers.append("teacher rank evidence is not approved")
        if not evidence.article.strip():
            candidate_blockers.append("teacher rank evidence article is missing")
        if not evidence.population_scope.strip():
            candidate_blockers.append("teacher rank evidence population scope is missing")
        if not _HEX64.fullmatch(evidence.source_hash):
            candidate_blockers.append("teacher rank evidence source hash is invalid")
        if not _HEX64.fullmatch(evidence.regression_suite_hash):
            candidate_blockers.append("teacher rank evidence regression suite hash is invalid")
        if evidence.reviewed_by and evidence.approved_by and evidence.reviewed_by == evidence.approved_by:
            candidate_blockers.append("teacher rank evidence reviewer and approver must be distinct")

        if not candidate_blockers and source is not None:
            return TeacherRankEvidenceResult(
                ready=True,
                blockers=(),
                legal_source_id=source.id,
                evidence_id=evidence.id,
            )

        blockers.extend(f"{component_code}: {reason}" for reason in candidate_blockers)

    return TeacherRankEvidenceResult(ready=False, blockers=tuple(dict.fromkeys(blockers)))
