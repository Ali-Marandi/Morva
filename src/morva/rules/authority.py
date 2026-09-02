from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class RuleActivationStatus(StrEnum):
    DRAFT = "draft"
    SOURCE_VERIFIED = "source_verified"
    LEGAL_REVIEWED = "legal_reviewed"
    FINANCE_REVIEWED = "finance_reviewed"
    REGRESSION_TESTED = "regression_tested"
    APPROVED = "approved"
    PUBLISHED = "published"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class AuthoritativeRule:
    code: str
    title: str
    issuer: str
    source_document: str
    article: str
    clause: str | None
    adoption_date: date
    effective_from: date
    effective_to: date | None
    population_scope: str
    source_hash: str
    activation_status: RuleActivationStatus
    regression_case_ids: tuple[str, ...]
    approved_by: str | None = None
    approved_at: date | None = None

    def can_calculate(self, on: date) -> bool:
        return (
            self.activation_status in {RuleActivationStatus.APPROVED, RuleActivationStatus.PUBLISHED}
            and bool(self.source_hash)
            and bool(self.issuer.strip())
            and bool(self.source_document.strip())
            and bool(self.article.strip())
            and bool(self.population_scope.strip())
            and bool(self.regression_case_ids)
            and self.effective_from <= on
            and (self.effective_to is None or on <= self.effective_to)
        )

    def assert_calculable(self, on: date) -> None:
        if not self.can_calculate(on):
            raise ValueError(f"legal rule {self.code} is not approved for calculation on {on.isoformat()}")
