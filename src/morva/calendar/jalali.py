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


def jalali_month_start(period: str) -> date:
    """Return the Gregorian date corresponding to the first day of a Jalali period.

    Payroll period keys are canonical Jalali values ("YYYY-MM"). This conversion is
    intentionally isolated at the calendar boundary so callers never construct a
    Gregorian date directly from Jalali year/month digits.
    """
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:].isdigit():
        raise ValueError(f"invalid Jalali period: {period!r}")

    jy = int(period[:4])
    jm = int(period[5:])
    if jy < 1 or not 1 <= jm <= 12:
        raise ValueError(f"invalid Jalali period: {period!r}")

    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + 1
    days += (jm - 1) * 31 if jm < 7 else ((jm - 1) * 30) + 6

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1

    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    month_lengths = (
        31,
        29 if (gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    gm = 1
    for month_length in month_lengths:
        if gd <= month_length:
            return date(gy, gm, gd)
        gd -= month_length
        gm += 1
    raise AssertionError("Gregorian conversion produced an invalid day")


def effective_on(effective_from: date, effective_to: date | None, day: date) -> bool:
    return effective_from <= day and (effective_to is None or day <= effective_to)
