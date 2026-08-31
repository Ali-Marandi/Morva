from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

@dataclass(frozen=True)
class RuleContext:
    effective_date: date
    values: dict[str, Decimal]

@dataclass(frozen=True)
class RuleResult:
    code: str
    amount: Decimal
    explanation: str

class RuleEngine:
    """Version-ready payroll rule engine. Legal rules belong in configuration/data."""
    def calculate(self, code: str, context: RuleContext, formula: Callable[[dict[str, Decimal]], Decimal]) -> RuleResult:
        amount = formula(context.values)
        return RuleResult(code=code, amount=amount, explanation=f"Rule {code} applied for {context.effective_date.isoformat()}")
