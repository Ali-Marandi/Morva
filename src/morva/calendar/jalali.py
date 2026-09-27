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


def jalali_month_start(period: str) -> date:
    """Return the Gregorian first day for a Jalali YYYY-MM payroll period."""
    try:
        year_text, month_text = period.split("-", 1)
        year, month = int(year_text), int(month_text)
    except (AttributeError, ValueError) as exc:
        raise ValueError("Jalali period must be YYYY-MM") from exc
    if year < 1 or not 1 <= month <= 12:
        raise ValueError("invalid Jalali period")
    jy = year + 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + 1
    if month < 7:
        days += (month - 1) * 31
    else:
        days += ((month - 7) * 30) + 186

    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    month_days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 1
    while gd > month_days[gm - 1]:
        gd -= month_days[gm - 1]
        gm += 1
    return date(gy, gm, gd)
