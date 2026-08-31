from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class OrderType(StrEnum):
    APPOINTMENT = "appointment"
    PROMOTION = "promotion"
    POSITION_CHANGE = "position_change"
    EDUCATION_CHANGE = "education_change"
    RANK_CHANGE = "rank_change"
    LOCATION_CHANGE = "location_change"
    CORRECTION = "correction"
    CANCELLATION = "cancellation"
    RETIREMENT = "retirement"


@dataclass(frozen=True, slots=True)
class OrderLine:
    code: str
    amount: Decimal
    rule_code: str | None = None


@dataclass(frozen=True, slots=True)
class PersonnelOrder:
    number: str
    employee_no: str
    order_type: OrderType
    issue_date: date
    effective_from: date
    effective_to: date | None = None
    reference: str | None = None
    lines: tuple[OrderLine, ...] = ()

    def is_effective_on(self, day: date) -> bool:
        return self.effective_from <= day and (self.effective_to is None or day <= self.effective_to)

    def validate(self) -> None:
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        if not self.number.strip():
            raise ValueError("order number is required")
        if not self.employee_no.strip():
            raise ValueError("employee_no is required")
