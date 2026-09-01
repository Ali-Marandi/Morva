from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrganizationUnit:
    code: str
    title: str
    level: str
    parent_code: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None

    def active_on(self, day: date) -> bool:
        return (self.effective_from is None or self.effective_from <= day) and (
            self.effective_to is None or day <= self.effective_to
        )


@dataclass(frozen=True, slots=True)
class Position:
    code: str
    title: str
    occupational_group: str
    grade: int | None = None
    job_points: Decimal = Decimal("0")
    full_time_educational: bool = False


@dataclass(frozen=True, slots=True)
class Assignment:
    employee_no: str
    organization_code: str
    position_code: str
    starts_on: date
    ends_on: date | None = None
    acting: bool = False

    def active_on(self, day: date) -> bool:
        return self.starts_on <= day and (self.ends_on is None or day <= self.ends_on)


class OrganizationCatalog:
    def __init__(self, units: tuple[OrganizationUnit, ...] = ()) -> None:
        self._units = {u.code: u for u in units}

    def add(self, unit: OrganizationUnit) -> None:
        if unit.code in self._units:
            raise ValueError(f"organization code already exists: {unit.code}")
        if unit.parent_code == unit.code:
            raise ValueError("organization unit cannot be its own parent")
        self._units[unit.code] = unit

    def get(self, code: str) -> OrganizationUnit:
        return self._units[code]
