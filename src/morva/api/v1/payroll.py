from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from morva.payroll.models import PayrollLine
from morva.payroll.service import PayrollService

router = APIRouter(prefix="/payroll", tags=["payroll"])
service = PayrollService()


class LineIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0)
    kind: str = Field(pattern="^(earning|deduction)$")
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    rule_code: str | None = None


class CalculateIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=50)
    period: date
    ruleset_version: str = Field(default="draft", min_length=1, max_length=50)
    lines: list[LineIn]


@router.post("/calculate")
def calculate(payload: CalculateIn) -> dict[str, object]:
    result = service.calculate(
        employee_no=payload.employee_no,
        period=payload.period,
        ruleset_version=payload.ruleset_version,
        lines=tuple(PayrollLine(**item.model_dump()) for item in payload.lines),
    )
    return {
        "employee_no": result.employee_no,
        "period": result.period,
        "ruleset_version": result.ruleset_version,
        "gross": str(result.gross),
        "deductions": str(result.deductions),
        "net": str(result.net),
        "taxable_gross": str(result.taxable_gross),
        "pensionable_gross": str(result.pensionable_gross),
        "insurable_gross": str(result.insurable_gross),
    }
