from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Installment:
    number: int
    due_period: str
    principal: Decimal
    fee: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.principal + self.fee


@dataclass(frozen=True, slots=True)
class Loan:
    loan_id: str
    employee_no: str
    lender_code: str
    principal: Decimal
    start_period: str
    installment_count: int
    installment_amount: Decimal
    status: str = "active"

    def schedule(self) -> tuple[Installment, ...]:
        if self.installment_count <= 0 or self.installment_amount <= 0:
            return ()
        year, month = map(int, self.start_period.split("-"))
        items: list[Installment] = []
        remaining = self.principal
        for idx in range(1, self.installment_count + 1):
            amount = min(self.installment_amount, remaining)
            items.append(Installment(idx, f"{year:04d}-{month:02d}", amount))
            remaining -= amount
            month += 1
            if month == 13:
                month, year = 1, year + 1
            if remaining <= 0:
                break
        return tuple(items)


@dataclass(frozen=True, slots=True)
class Debt:
    debt_id: str
    employee_no: str
    code: str
    balance: Decimal
    reason: str


@dataclass(frozen=True, slots=True)
class DeductionEntry:
    employee_no: str
    period: str
    code: str
    amount: Decimal
    source: str
    priority: int = 100
    mandatory: bool = False


class DeductionLedger:
    def __init__(self, entries: tuple[DeductionEntry, ...] = ()) -> None:
        self._entries = list(entries)

    def add(self, entry: DeductionEntry) -> None:
        if entry.amount < 0:
            raise ValueError("deduction amount cannot be negative")
        self._entries.append(entry)

    def for_period(self, employee_no: str, period: str) -> tuple[DeductionEntry, ...]:
        return tuple(sorted((x for x in self._entries if x.employee_no == employee_no and x.period == period), key=lambda x: (not x.mandatory, x.priority)))

    def total(self, employee_no: str, period: str) -> Decimal:
        return sum((x.amount for x in self.for_period(employee_no, period)), Decimal("0"))
