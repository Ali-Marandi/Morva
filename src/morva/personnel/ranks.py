from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TeacherRank(StrEnum):
    TEACHER_ASSISTANT = "آموزشیار معلم"
    TEACHER = "مربی معلم"
    ASSISTANT_PROFESSOR = "استادیار معلم"
    ASSOCIATE_PROFESSOR = "دانشیار معلم"
    PROFESSOR = "استاد معلم"


@dataclass(frozen=True, slots=True)
class RankCase:
    employee_no: str
    requested_rank: TeacherRank
    status: str = "draft"
    score: int | None = None
    decision_reference: str | None = None

    def approve(self, *, score: int, reference: str) -> "RankCase":
        if score < 0:
            raise ValueError("score cannot be negative")
        if not reference.strip():
            raise ValueError("decision reference is required")
        return RankCase(self.employee_no, self.requested_rank, "approved", score, reference)
