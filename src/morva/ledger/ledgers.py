from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Installment:
    due_period: str
    principal: Decimal
    fee: Decimal = Decimal("0.00")

    @property
    def total(self) -> Decimal:
        return self.principal + self.fee


@dataclass(frozen=True, slots=True)
class LoanAccount:
    loan_id: str
    employee_no: str
    principal: Decimal
    installments: tuple[Installment, ...]
    active_from: date
    active_to: date | None = None

    @property
    def outstanding(self) -> Decimal:
        return sum((item.principal for item in self.installments), Decimal("0.00"))


def deduction_for_period(accounts: tuple[LoanAccount, ...], period: str) -> Decimal:
    return sum(
        (item.total for account in accounts for item in account.installments if item.due_period == period),
        Decimal("0.00"),
    )


@dataclass(frozen=True, slots=True)
class DebtLedgerEntry:
    employee_no: str
    code: str
    period: str
    amount: Decimal
    source: str
    reference: str


@dataclass(frozen=True, slots=True)
class DeductionLedger:
    entries: tuple[DebtLedgerEntry, ...]

    def total(self, employee_no: str, period: str) -> Decimal:
        return sum(
            (entry.amount for entry in self.entries if entry.employee_no == employee_no and entry.period == period),
            Decimal("0.00"),
        )
