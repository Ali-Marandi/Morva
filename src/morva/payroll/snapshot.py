from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class EffectiveOrder:
    order_number: str
    order_type: str
    effective_date: str
    issue_date: str
    arrears_date: str | None
    end_date: str | None
    status: str | None
    benefit_total: Decimal


@dataclass(frozen=True, slots=True)
class PayrollSnapshot:
    employee_key: str
    period: str
    employment_type: str | None
    org_unit: str | None
    service_region: str | None
    work_days: str | None
    gross: Decimal
    deductions: Decimal
    net: Decimal
    employer_commitments: Decimal
    components: Mapping[str, Decimal]
    deduction_components: Mapping[str, Decimal]
    latest_order: EffectiveOrder
    loan_installment_total: Decimal
    loan_count: int
    supplementary: Mapping[str, Any] | None
    health: Mapping[str, Any] | None
    social: Mapping[str, Any] | None

    @property
    def component_total(self) -> Decimal:
        return sum(self.components.values(), Decimal("0"))

    @property
    def deduction_component_total(self) -> Decimal:
        return sum(self.deduction_components.values(), Decimal("0"))

    @property
    def unexplained_deduction_total(self) -> Decimal:
        return self.deductions - self.deduction_component_total - self.loan_installment_total


def _date_key(value: str | None) -> tuple[int, str]:
    normalized = (value or "").replace("/", "")
    return (int(normalized), normalized) if normalized.isdigit() else (-1, normalized)


def latest_effective_order(rows: list[dict[str, Any]]) -> EffectiveOrder:
    if not rows:
        raise ValueError("employee has no personnel order")
    row = max(rows, key=lambda r: (_date_key(r.get("effective_date")), _date_key(r.get("issue_date"))))
    return EffectiveOrder(
        order_number=str(row.get("order_number") or ""),
        order_type=str(row.get("order_type") or ""),
        effective_date=str(row.get("effective_date") or ""),
        issue_date=str(row.get("issue_date") or ""),
        arrears_date=str(row.get("arrears_date")) if row.get("arrears_date") else None,
        end_date=str(row.get("end_date")) if row.get("end_date") else None,
        status=str(row.get("status")) if row.get("status") else None,
        benefit_total=Decimal(str(row.get("benefit_total") or "0")),
    )
