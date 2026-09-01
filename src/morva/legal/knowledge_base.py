from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


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
class LegalSource:
    source_id: str
    title: str
    authority: str
    document_type: str
    publication_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    article: str | None = None
    clause: str | None = None
    url: str | None = None
    version: str | None = None
    status: ReviewStatus = ReviewStatus.DRAFT


@dataclass(frozen=True, slots=True)
class LegalRule:
    code: str
    title: str
    source_id: str
    effective_from: date
    effective_to: date | None = None
    rule_version: str = "draft"
    review_status: ReviewStatus = ReviewStatus.DRAFT
    priority: int = 100
    formula: dict[str, object] | None = None
    eligibility: dict[str, object] | None = None
    audit_message: str = ""

    def can_activate(self) -> bool:
        return (
            self.review_status == ReviewStatus.APPROVED
            and bool(self.source_id)
            and self.effective_from is not None
            and self.formula is not None
        )


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, list[LegalRule]] = {}

    def register(self, rule: LegalRule) -> None:
        if rule.effective_to and rule.effective_to < rule.effective_from:
            raise ValueError("rule effective period is invalid")
        self._rules.setdefault(rule.code, []).append(rule)

    def active(self, code: str, on: date) -> LegalRule:
        candidates = [r for r in self._rules.get(code, ()) if r.effective_from <= on and (r.effective_to is None or on <= r.effective_to)]
        active = [r for r in candidates if r.review_status == ReviewStatus.ACTIVE]
        if not active:
            raise LookupError(f"no active reviewed rule: {code} on {on}")
        return sorted(active, key=lambda r: (r.priority, r.effective_from), reverse=True)[0]
