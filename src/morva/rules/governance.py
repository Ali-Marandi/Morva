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
