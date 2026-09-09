from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


_PERIOD_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _require_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_period(value: str, field: str) -> str:
    value = _require_text(value, field)
    if not _PERIOD_RE.fullmatch(value):
        raise ValueError(f"{field} must use YYYY-MM format")
    return value


@dataclass(frozen=True, slots=True)
class Installment:
    number: int
    due_period: str
    principal: Decimal
    fee: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        if self.number <= 0:
            raise ValueError("installment number must be positive")
        _require_period(self.due_period, "due_period")
        if self.principal <= 0:
            raise ValueError("installment principal must be positive")
        if self.fee < 0:
            raise ValueError("installment fee cannot be negative")

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

    def __post_init__(self) -> None:
        _require_text(self.loan_id, "loan_id")
        _require_text(self.employee_no, "employee_no")
        _require_text(self.lender_code, "lender_code")
        if self.principal <= 0:
            raise ValueError("loan principal must be positive")
        _require_period(self.start_period, "start_period")
        if self.installment_count <= 0:
            raise ValueError("installment_count must be positive")
        if self.installment_amount <= 0:
            raise ValueError("installment_amount must be positive")
        _require_text(self.status, "status")

    def schedule(self) -> tuple[Installment, ...]:
        year, month = map(int, self.start_period.split("-"))
        items: list[Installment] = []
        remaining = self.principal
        for idx in range(1, self.installment_count + 1):
            amount = min(self.installment_amount, remaining)
            items.append(Installment(idx, f"{year:04d}-{month:02d}", amount))
            remaining -= amount
            if remaining <= 0:
                break
            month += 1
            if month == 13:
                month, year = 1, year + 1
        return tuple(items)


@dataclass(frozen=True, slots=True)
class Debt:
    debt_id: str
    employee_no: str
    code: str
    balance: Decimal
    reason: str

    def __post_init__(self) -> None:
        _require_text(self.debt_id, "debt_id")
        _require_text(self.employee_no, "employee_no")
        _require_text(self.code, "code")
        if self.balance < 0:
            raise ValueError("debt balance cannot be negative")
        _require_text(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class DeductionEntry:
    employee_no: str
    period: str
    code: str
    amount: Decimal
    source: str
    priority: int = 100
    mandatory: bool = False

    def __post_init__(self) -> None:
        _require_text(self.employee_no, "employee_no")
        _require_period(self.period, "period")
        _require_text(self.code, "code")
        _require_text(self.source, "source")
        if self.amount < 0:
            raise ValueError("deduction amount cannot be negative")
        if self.priority < 0:
            raise ValueError("deduction priority cannot be negative")


class DeductionLedger:
    def __init__(self, entries: tuple[DeductionEntry, ...] = ()) -> None:
        self._entries: list[DeductionEntry] = []
        for entry in entries:
            self.add(entry)

    def add(self, entry: DeductionEntry) -> None:
        if not isinstance(entry, DeductionEntry):
            raise TypeError("ledger entries must be DeductionEntry instances")
        self._entries.append(entry)

    def for_period(self, employee_no: str, period: str) -> tuple[DeductionEntry, ...]:
        _require_text(employee_no, "employee_no")
        _require_period(period, "period")
        return tuple(
            sorted(
                (x for x in self._entries if x.employee_no == employee_no and x.period == period),
                key=lambda x: (not x.mandatory, x.priority, x.code, x.source, x.amount),
            )
        )

    def total(self, employee_no: str, period: str) -> Decimal:
        return sum((x.amount for x in self.for_period(employee_no, period)), Decimal(0))
