from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from morva.payroll import PayrollCalculator, PayrollLine, demo_iranian_policy_pack

router = APIRouter(prefix="/payroll", tags=["payroll"])
calculator = PayrollCalculator()


class LineIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0)
    kind: str = Field(pattern="^(earning|deduction)$")
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    rule_code: str | None = None
    explanation: str | None = None


class CalculateIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=50)
    period: date
    ruleset_version: str = Field(default="draft", min_length=1, max_length=50)
    lines: list[LineIn] = Field(min_length=1)
    apply_demo_policy: bool = False


@router.post("/calculate")
def calculate(payload: CalculateIn) -> dict[str, object]:
    tax_policy = None
    contribution_policies = ()
    if payload.apply_demo_policy:
        tax_policy, contribution_policies = demo_iranian_policy_pack()
    calculation = calculator.calculate(
        employee_no=payload.employee_no,
        period=payload.period,
        ruleset_version=payload.ruleset_version,
        lines=tuple(PayrollLine(**item.model_dump()) for item in payload.lines),
        tax_policy=tax_policy,
        contribution_policies=contribution_policies,
    )
    result = calculation.result
    return {
        "employee_no": result.employee_no,
        "period": result.period,
        "ruleset_version": result.ruleset_version,
        "gross": str(result.gross),
        "deductions": str(result.deductions),
        "net": str(result.net),
        "taxable_gross": str(calculation.taxable_income),
        "tax": str(calculation.tax),
        "contributions": str(calculation.contributions),
        "fingerprint": calculation.fingerprint,
        "explanations": calculation.explanations,
        "lines": [line.model_dump(mode="json") for line in result.lines],
    }
