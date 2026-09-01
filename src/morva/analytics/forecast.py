from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ForecastResult:
    baseline: Decimal
    projected: Decimal
    delta: Decimal
    assumptions: dict[str, Decimal]
    advisory: bool = True


def project_payroll(current_total: Decimal, coefficient_change: Decimal = Decimal("0"), headcount_change: int = 0, average_unit_change: Decimal = Decimal("0")) -> ForecastResult:
    projected = current_total * (Decimal("1") + coefficient_change) + Decimal(headcount_change) * average_unit_change
    return ForecastResult(current_total, projected, projected - current_total, {
        "coefficient_change": coefficient_change,
        "headcount_change": Decimal(headcount_change),
        "average_unit_change": average_unit_change,
    })


def ai_policy_note() -> str:
    return "Forecast and anomaly outputs are advisory. Legal payroll truth remains in approved Rule Packs."
