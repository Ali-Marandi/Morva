from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from morva.payroll.reconciliation_engine import reconcile_population
from morva.payroll.snapshot import EffectiveOrder, PayrollSnapshot

router = APIRouter(prefix="/payroll", tags=["payroll-reconciliation"])


class OrderPayload(BaseModel):
    order_number: str = ""
    order_type: str = ""
    effective_date: str = ""
    issue_date: str = ""
    arrears_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    benefit_total: Decimal = Decimal(0)


class SnapshotPayload(BaseModel):
    employee_key: str = Field(min_length=1)
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    employment_type: str | None = None
    org_unit: str | None = None
    service_region: str | None = None
    work_days: str | None = None
    gross: Decimal = Field(ge=0)
    deductions: Decimal = Field(ge=0)
    net: Decimal
    employer_commitments: Decimal = Field(ge=0)
    components: dict[str, Decimal] = {}
    deduction_components: dict[str, Decimal] = {}
    latest_order: OrderPayload
    loan_installment_total: Decimal = Field(default=Decimal(0), ge=0)
    loan_count: int = Field(default=0, ge=0)
    supplementary: dict[str, object] | None = None
    health: dict[str, object] | None = None
    social: dict[str, object] | None = None


class ReconciliationRequest(BaseModel):
    snapshots: list[SnapshotPayload] = Field(min_length=1)
    recalculated_components: dict[str, dict[str, Decimal]]
    recalculated_deductions: dict[str, Decimal] | None = None


def _snapshot(item: SnapshotPayload) -> PayrollSnapshot:
    order = EffectiveOrder(**item.latest_order.model_dump())
    return PayrollSnapshot(
        employee_key=item.employee_key,
        period=item.period,
        employment_type=item.employment_type,
        org_unit=item.org_unit,
        service_region=item.service_region,
        work_days=item.work_days,
        gross=item.gross,
        deductions=item.deductions,
        net=item.net,
        employer_commitments=item.employer_commitments,
        components=item.components,
        deduction_components=item.deduction_components,
        latest_order=order,
        loan_installment_total=item.loan_installment_total,
        loan_count=item.loan_count,
        supplementary=item.supplementary,
        health=item.health,
        social=item.social,
    )


@router.post("/reconcile")
def reconcile(payload: ReconciliationRequest) -> dict[str, object]:
    snapshots = [_snapshot(item) for item in payload.snapshots]
    result = reconcile_population(
        snapshots,
        payload.recalculated_components,
        payload.recalculated_deductions,
    )
    return {
        "employees": len(result.employees),
        "matched_employees": result.matched_employees,
        "non_matching_employees": result.non_matching_employees,
        "reported_gross": str(result.reported_gross),
        "recalculated_gross": str(result.recalculated_gross),
        "gross_delta": str(result.gross_delta),
        "reported_deductions": str(result.reported_deductions),
        "recalculated_deductions": str(result.recalculated_deductions),
        "deduction_delta": str(result.deduction_delta),
        "reported_net": str(result.reported_net),
        "recalculated_net": str(result.recalculated_net),
        "net_delta": str(result.net_delta),
        "classification_counts": result.by_classification(),
    }
