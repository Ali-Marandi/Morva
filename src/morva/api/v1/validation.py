from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from morva.payroll.models import PayrollLine, PayrollResult
from morva.payroll.validation import PayrollValidator

router = APIRouter(prefix="/payroll", tags=["payroll-validation"])


class ValidationLine(BaseModel):
    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    kind: str = Field(pattern="^(earning|deduction)$")
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False


class ValidationRequest(BaseModel):
    employee_no: str
    period: date
    ruleset_version: str = "draft"
    lines: list[ValidationLine] = Field(min_length=1)
    minimum_net: Decimal | None = Field(default=None, ge=0)


@router.post("/validate")
def validate(payload: ValidationRequest) -> dict[str, object]:
    result = PayrollResult(
        employee_no=payload.employee_no,
        period=f"{payload.period.year:04d}-{payload.period.month:02d}",
        ruleset_version=payload.ruleset_version,
        lines=tuple(PayrollLine(**item.model_dump()) for item in payload.lines),
    )
    findings = PayrollValidator().validate(result, minimum_net=payload.minimum_net)
    return {
        "employee_no": result.employee_no,
        "period": result.period,
        "blocking": any(item.severity == "error" for item in findings),
        "findings": [item.__dict__ for item in findings],
    }
