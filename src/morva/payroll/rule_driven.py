from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from morva.rules.engine import RuleContext, RuleEngine
from morva.rules.pack_manifest import RulePackManifest

from .models import PayrollLine, PayrollResult


@dataclass(frozen=True, slots=True)
class RuleDrivenComponent:
    code: str
    title: str
    kind: str
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False


class RuleDrivenPayroll:
    """Build payroll results directly from effective-dated RuleEngine definitions."""

    def __init__(self, engine: RuleEngine, manifest: RulePackManifest) -> None:
        self.engine = engine
        self.manifest = manifest

    def calculate(
        self,
        *,
        employee_no: str,
        period: str,
        effective_date: date,
        values: Mapping[str, Decimal],
        components: Sequence[RuleDrivenComponent],
        production: bool = True,
    ) -> PayrollResult:
        if production:
            self.manifest.assert_production_ready()

        working = dict(values)
        lines: list[PayrollLine] = []
        for component in components:
            rule = self.engine.resolve(component.code, effective_date)
            result = self.engine.calculate(component.code, RuleContext(effective_date, working))
            amount = result.amount.quantize(Decimal("0.01"))
            lines.append(
                PayrollLine(
                    code=component.code,
                    title=component.title,
                    amount=amount,
                    kind=component.kind,
                    taxable=component.taxable,
                    pensionable=component.pensionable,
                    insurable=component.insurable,
                    rule_code=rule.code,
                    explanation=f"{result.explanation}; legal_reference={result.legal_reference or 'unregistered'}",
                )
            )
            working[component.code] = amount

        return PayrollResult(employee_no=employee_no, period=period, lines=tuple(lines), ruleset_version=self.manifest.version)
