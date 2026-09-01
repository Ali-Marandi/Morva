from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class LegalStatus(StrEnum):
    CANDIDATE = "candidate"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class LegalSource:
    code: str
    title: str
    authority: str
    publication_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    reference: str | None = None
    status: LegalStatus = LegalStatus.REVIEW_REQUIRED

    def usable_for_production(self) -> bool:
        return self.status == LegalStatus.APPROVED and self.effective_date is not None
