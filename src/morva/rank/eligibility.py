from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import TeacherRank


@dataclass(frozen=True, slots=True)
class RankThreshold:
    general_min: Decimal
    specialized_min: Decimal
    professional_min: Decimal
    experience_min: Decimal


# 1404 regulation research table. Keep separate from ministerial detail tables
# until the approved implementation instruction is imported.
THRESHOLDS: dict[TeacherRank, RankThreshold] = {
    TeacherRank.EDUCATION_ASSISTANT: RankThreshold(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")),
    TeacherRank.INSTRUCTOR: RankThreshold(Decimal("100"), Decimal("126"), Decimal("141"), Decimal("135")),
    TeacherRank.ASSISTANT_PROFESSOR: RankThreshold(Decimal("120"), Decimal("151"), Decimal("166"), Decimal("165")),
    TeacherRank.ASSOCIATE_PROFESSOR: RankThreshold(Decimal("140"), Decimal("176"), Decimal("191"), Decimal("195")),
    TeacherRank.PROFESSOR: RankThreshold(Decimal("160"), Decimal("201"), Decimal("216"), Decimal("225")),
}


def meets_thresholds(rank: TeacherRank, *, general: Decimal, specialized: Decimal, professional: Decimal, experience: Decimal) -> bool:
    threshold = THRESHOLDS[rank]
    return all(
        value >= minimum
        for value, minimum in (
            (general, threshold.general_min),
            (specialized, threshold.specialized_min),
            (professional, threshold.professional_min),
            (experience, threshold.experience_min),
        )
    )
