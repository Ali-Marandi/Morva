from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass(frozen=True)
class PayrollLine:
    code: str
    title: str
    amount: Decimal
    kind: str

@dataclass(frozen=True)
class PayrollResult:
    employee_no: str
    period: str
    lines: tuple[PayrollLine, ...]

    @property
    def gross(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "earning"), Decimal(0))

    @property
    def deductions(self) -> Decimal:
        return sum((x.amount for x in self.lines if x.kind == "deduction"), Decimal(0))

    @property
    def net(self) -> Decimal:
        return self.gross - self.deductions
