from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PayrollScenario:
    name: str
    coefficient_change: Decimal = Decimal(0)
    fixed_adjustment: Decimal = Decimal(0)

    def project_employee(self, current_gross: Decimal) -> Decimal:
        if current_gross < 0:
            raise ValueError("current_gross cannot be negative")
        return (current_gross * (Decimal(1) + self.coefficient_change) + self.fixed_adjustment).quantize(Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    employee_count: int
    current_total: Decimal
    projected_total: Decimal
    delta: Decimal


def summarize(scenario: PayrollScenario, gross_values: Iterable[Decimal]) -> ScenarioSummary:
    values = tuple(gross_values)
    projected = tuple(scenario.project_employee(value) for value in values)
    current_total = sum(values, Decimal(0))
    projected_total = sum(projected, Decimal(0))
    return ScenarioSummary(len(values), current_total, projected_total, projected_total - current_total)
