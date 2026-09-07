from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import RulePackRecord
from morva.security.policy import require_distinct_actors


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    SOURCE_REVIEW = "source_review"
    LEGAL_REVIEW = "legal_review"
    FINANCE_REVIEW = "finance_review"
    REGRESSION_TESTED = "regression_tested"
    APPROVED = "approved"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class LegalRuleMeta:
    code: str
    source_document: str
    authority: str
    effective_from: date
    effective_to: date | None
    review_status: ReviewStatus
    regression_case_ids: tuple[str, ...] = ()

    def can_activate(self) -> bool:
        return (
            self.review_status == ReviewStatus.APPROVED
            and bool(self.source_document.strip())
            and bool(self.authority.strip())
            and bool(self.regression_case_ids)
        )

    def assert_activatable(self) -> None:
        if not self.can_activate():
            raise ValueError(f"rule {self.code} is not production-activatable")


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_legal_source_payload(*, adoption_date: str, effective_from: str, effective_to: str | None, document_hash: str) -> None:
    for name, value in (("adoption_date", adoption_date), ("effective_from", effective_from)):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"{name} must use YYYY-MM-DD") from exc
    if effective_to is not None:
        try:
            datetime.strptime(effective_to, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("effective_to must use YYYY-MM-DD") from exc
        if effective_to < effective_from:
            raise ValueError("effective_to cannot precede effective_from")
    if not _HEX64.fullmatch(document_hash):
        raise ValueError("document_hash must be a 64-character hexadecimal SHA-256")


def review_legal_source(source: LegalSourceRecord) -> None:
    if source.status != "review_required":
        raise ValueError("legal source can only be reviewed from review_required state")
    source.status = "reviewed"


def approve_legal_source(source: LegalSourceRecord, approver_id: str, reviewer_id: str | None) -> None:
    if source.status != "reviewed":
        raise ValueError("legal source must be reviewed before approval")
    require_distinct_actors([reviewer_id, approver_id])
    source.status = "approved"


def validate_evidence_payload(*, article: str, population_scope: str, source_hash: str, regression_suite_hash: str) -> None:
    if not article.strip():
        raise ValueError("article is required")
    if not population_scope.strip():
        raise ValueError("population_scope is required")
    for name, value in (("source_hash", source_hash), ("regression_suite_hash", regression_suite_hash)):
        if not _HEX64.fullmatch(value):
            raise ValueError(f"{name} must be a 64-character hexadecimal SHA-256")


def review_evidence(evidence: RuleEvidenceRecord, reviewer_id: str) -> None:
    if evidence.status != "review_required":
        raise ValueError("rule evidence can only be reviewed from review_required state")
    evidence.reviewed_by = reviewer_id
    evidence.status = "reviewed"


def approve_evidence(evidence: RuleEvidenceRecord, approver_id: str) -> None:
    if evidence.status != "reviewed":
        raise ValueError("rule evidence must be reviewed before approval")
    require_distinct_actors([evidence.reviewed_by, approver_id])
    evidence.approved_by = approver_id
    evidence.approved_at = datetime.utcnow()
    evidence.status = "approved"


def review_rule_pack(pack: RulePackRecord) -> None:
    if pack.status != "draft":
        raise ValueError("rule pack can only be reviewed from draft state")
    pack.status = "reviewed"
    pack.reviewed_at = datetime.utcnow()


def approve_rule_pack(session: Session, pack: RulePackRecord, approver_id: str) -> dict[str, object]:
    if pack.status != "reviewed":
        raise ValueError("rule pack must be reviewed before approval")
    evidence = session.scalars(select(RuleEvidenceRecord).where(RuleEvidenceRecord.rule_pack_version == pack.version)).all()
    blockers: list[str] = []
    if not evidence:
        blockers.append("no rule evidence is registered for this rule pack")
    for item in evidence:
        source = session.get(LegalSourceRecord, item.legal_source_id)
        if source is None:
            blockers.append(f"missing legal source for component {item.component_code}")
            continue
        if source.status != "approved":
            blockers.append(f"legal source for component {item.component_code} is not approved")
        if item.source_hash != source.document_hash:
            blockers.append(f"source hash mismatch for component {item.component_code}")
        if item.status != "approved":
            blockers.append(f"rule evidence for component {item.component_code} is not approved")
    if blockers:
        return {"ready": False, "blockers": blockers}
    require_distinct_actors([pack.reviewed_by, approver_id])
    pack.status = "approved"
    pack.approved_by = approver_id
    pack.approved_at = datetime.utcnow()
    return {"ready": True, "blockers": []}


def pack_readiness(session: Session, pack: RulePackRecord) -> dict[str, object]:
    evidence = session.scalars(select(RuleEvidenceRecord).where(RuleEvidenceRecord.rule_pack_version == pack.version)).all()
    blockers: list[str] = []
    if pack.status != "approved":
        blockers.append("rule pack is not approved")
    if not evidence:
        blockers.append("no rule evidence is registered for this rule pack")
    for item in evidence:
        source = session.get(LegalSourceRecord, item.legal_source_id)
        if source is None:
            blockers.append(f"missing legal source for component {item.component_code}")
            continue
        if source.status != "approved":
            blockers.append(f"legal source for component {item.component_code} is not approved")
        if item.source_hash != source.document_hash:
            blockers.append(f"source hash mismatch for component {item.component_code}")
        if item.status != "approved":
            blockers.append(f"rule evidence for component {item.component_code} is not approved")
        if item.reviewed_by and item.approved_by and item.reviewed_by == item.approved_by:
            blockers.append(f"reviewer and approver must be distinct for component {item.component_code}")
    return {"ready": not blockers, "blockers": blockers, "evidence_count": len(evidence)}
