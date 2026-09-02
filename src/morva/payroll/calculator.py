from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Iterable

from .models import PayrollLine, PayrollResult
from .policies import ContributionPolicy, TaxPolicy


@dataclass(frozen=True, slots=True)
class PayrollCalculation:
    result: PayrollResult
    taxable_income: Decimal
    tax: Decimal
    contributions: Decimal
    fingerprint: str
    explanations: tuple[str, ...]


class PayrollCalculator:
    def calculate(
        self,
        *,
        employee_no: str,
        period: date | str,
        ruleset_version: str,
        lines: Iterable[PayrollLine],
        tax_policy: TaxPolicy | None = None,
        contribution_policies: Iterable[ContributionPolicy] = (),
    ) -> PayrollCalculation:
        materialized = tuple(lines)
        taxable = sum((line.amount for line in materialized if line.kind == "earning" and line.taxable), Decimal(0))
        tax = Decimal(0)
        explanations: list[str] = []
        if tax_policy:
            tax, tax_explanations = tax_policy.calculate(taxable)
            explanations.extend(tax_explanations)
            materialized = materialized + (
                PayrollLine(
                    code="TAX",
                    title="Income tax",
                    amount=tax,
                    kind="deduction",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    rule_code=f"TAX:{tax_policy.version}",
                    explanation="; ".join(tax_explanations),
                ),
            )
        contributions = Decimal(0)
        for policy in contribution_policies:
            amount = policy.calculate(
                sum((line.amount for line in materialized if line.kind == "earning" and line.pensionable), Decimal(0))
            )
            contributions += amount
            materialized += (
                PayrollLine(
                    code=policy.code,
                    title=policy.code.replace("_", " ").title(),
                    amount=amount,
                    kind="deduction",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    rule_code=policy.code,
                    explanation=f"rate={policy.rate}; ceiling={policy.ceiling}",
                ),
            )
        period_key = period if isinstance(period, str) else f"{period.year:04d}-{period.month:02d}"
        result = PayrollResult(
            employee_no=employee_no,
            period=period_key,
            lines=materialized,
            ruleset_version=ruleset_version,
        )
        canonical = "|".join(
            f"{line.code}:{line.kind}:{line.amount}:{line.rule_code or ''}" for line in result.lines
        )
        fingerprint = sha256(f"{employee_no}|{result.period}|{ruleset_version}|{canonical}".encode()).hexdigest()
        return PayrollCalculation(result, taxable, tax, contributions, fingerprint, tuple(explanations))
