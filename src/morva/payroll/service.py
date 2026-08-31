from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable

from morva.payroll.models import PayrollLine, PayrollResult


class PayrollService:
    def period_key(self, period: date) -> str:
        return f"{period.year:04d}-{period.month:02d}"

    def calculate(
        self,
        *,
        employee_no: str,
        period: date,
        lines: Iterable[PayrollLine],
        ruleset_version: str = "draft",
    ) -> PayrollResult:
        materialized = tuple(lines)
        return PayrollResult(
            employee_no=employee_no,
            period=self.period_key(period),
            lines=materialized,
            ruleset_version=ruleset_version,
        )

    def build_standard_lines(
        self,
        *,
        base_salary: Decimal,
        allowances: Iterable[tuple[str, str, Decimal, bool, bool, bool]],
        deductions: Iterable[tuple[str, str, Decimal, bool]],
    ) -> tuple[PayrollLine, ...]:
        if base_salary < 0:
            raise ValueError("base_salary cannot be negative")
        lines: list[PayrollLine] = [
            PayrollLine(
                code="BASE_SALARY",
                title="Base salary",
                amount=base_salary,
                kind="earning",
                taxable=True,
                pensionable=True,
                insurable=True,
            )
        ]
        lines.extend(
            PayrollLine(
                code=code,
                title=title,
                amount=amount,
                kind="earning",
                taxable=taxable,
                pensionable=pensionable,
                insurable=insurable,
            )
            for code, title, amount, taxable, pensionable, insurable in allowances
        )
        lines.extend(
            PayrollLine(code=code, title=title, amount=amount, kind="deduction", taxable=taxable)
            for code, title, amount, taxable in deductions
        )
        return tuple(lines)
