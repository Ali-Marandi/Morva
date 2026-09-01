from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class JalaliMonth:
    year: int
    month: int

    def __post_init__(self) -> None:
        if self.year < 1 or not 1 <= self.month <= 12:
            raise ValueError("invalid Jalali year/month")

    @property
    def key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def next(self) -> "JalaliMonth":
        return JalaliMonth(self.year + (self.month == 12), 1 if self.month == 12 else self.month + 1)


def jalali_month_range(start: JalaliMonth, end: JalaliMonth) -> tuple[JalaliMonth, ...]:
    if (end.year, end.month) < (start.year, start.month):
        raise ValueError("end month precedes start month")
    out: list[JalaliMonth] = []
    cur = start
    while (cur.year, cur.month) <= (end.year, end.month):
        out.append(cur)
        cur = cur.next()
    return tuple(out)


def effective_on(effective_from: date, effective_to: date | None, day: date) -> bool:
    return effective_from <= day and (effective_to is None or day <= effective_to)
