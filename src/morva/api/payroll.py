from __future__ import annotations

from datetime import date
from decimal import Decimal

from morva.payroll.models import PayrollLine
from morva.payroll.service import PayrollService


def calculate_demo_payroll(employee_no: str, period: date, base_salary: Decimal) -> dict[str, str]:
    """Application-level helper for development; not a legal payroll policy."""
    service = PayrollService()
    lines = service.build_standard_lines(
        base_salary=base_salary,
        allowances=[],
        deductions=[],
    )
    result = service.calculate(
        employee_no=employee_no,
        period=period,
        lines=lines,
        ruleset_version="development",
    )
    return {"gross": str(result.gross), "net": str(result.net), "period": result.period}
