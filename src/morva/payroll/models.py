from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PayrollLine:
    code: str
    title: str
    amount: Decimal
    kind: str
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    rule_code: str | None = None
    explanation: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"earning", "deduction"}:
            raise ValueError("kind must be earning or deduction")
        if self.amount < 0:
            raise ValueError("amount cannot be negative")


@dataclass(frozen=True, slots=True)
class PayrollResult:
    employee_no: str
    period: str
    lines: tuple[PayrollLine, ...]
    ruleset_version: str = "draft"

    @property
    def gross(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "earning"), Decimal(0))

    @property
    def deductions(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "deduction"), Decimal(0))

    @property
    def net(self) -> Decimal:
        return self.gross - self.deductions

    @property
    def taxable_gross(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "earning" and x.taxable), Decimal(0))

    @property
    def pensionable_gross(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "earning" and x.pensionable), Decimal(0))

    @property
    def insurable_gross(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "earning" and x.insurable), Decimal(0))
