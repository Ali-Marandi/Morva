from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class TeacherRank(StrEnum):
    EDUCATION_ASSISTANT = "education_assistant"
    INSTRUCTOR = "instructor"
    ASSISTANT_PROFESSOR = "assistant_professor"
    ASSOCIATE_PROFESSOR = "associate_professor"
    PROFESSOR = "professor"


class RankCaseStatus(StrEnum):
    DRAFT = "draft"
    EVIDENCE_COLLECTION = "evidence_collection"
    ASSESSMENT = "assessment"
    COMMITTEE_REVIEW = "committee_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPEAL = "appeal"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class RankAssessment:
    general: Decimal
    specialized: Decimal
    professional: Decimal
    experience: Decimal

    @property
    def weighted_score(self) -> Decimal:
        return (
            self.general * Decimal("0.20")
            + self.specialized * Decimal("0.25")
            + self.professional * Decimal("0.27")
            + self.experience * Decimal("0.28")
        ).quantize(Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class RankCase:
    employee_no: str
    requested_rank: TeacherRank
    opened_on: date
    status: RankCaseStatus = RankCaseStatus.DRAFT
    assessment: RankAssessment | None = None
    evidence_ids: tuple[str, ...] = ()
    committee_level: str = "district_region"

    def approve(self) -> "RankCase":
        if self.assessment is None:
            raise ValueError("assessment is required before approval")
        return RankCase(
            employee_no=self.employee_no,
            requested_rank=self.requested_rank,
            opened_on=self.opened_on,
            status=RankCaseStatus.APPROVED,
            assessment=self.assessment,
            evidence_ids=self.evidence_ids,
            committee_level=self.committee_level,
        )
