from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .models import PayrollLine, PayrollResult
from .snapshot import PayrollSnapshot


@dataclass(frozen=True, slots=True)
class SourceReplay:
    """A deterministic replay of an observed source payroll snapshot.

    This is intentionally *not* a legal calculation profile. It proves that
    Morva can faithfully reconstruct the source result before legal rules are
    introduced and compared against it.
    """

    result: PayrollResult
    reported_gross: Decimal
    reported_deductions: Decimal
    reported_net: Decimal
    component_gross: Decimal
    component_deductions: Decimal


class SourceReplayCalculator:
    def replay(self, snapshot: PayrollSnapshot) -> SourceReplay:
        lines: list[PayrollLine] = []
        for code, amount in sorted(snapshot.components.items()):
            lines.append(
                PayrollLine(
                    code=code,
                    title=code,
                    amount=Decimal(amount),
                    kind="earning",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    explanation="Observed source payroll component; legal treatment not inferred.",
                )
            )
        for code, amount in sorted(snapshot.deduction_components.items()):
            lines.append(
                PayrollLine(
                    code=code,
                    title=code,
                    amount=Decimal(amount),
                    kind="deduction",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    explanation="Observed source payroll deduction component; legal treatment not inferred.",
                )
            )

        result = PayrollResult(
            employee_no=snapshot.employee_key,
            period=snapshot.period,
            lines=tuple(lines),
            ruleset_version="SOURCE_REPLAY:1405-05",
        )
        component_gross = sum(
            (line.amount for line in lines if line.kind == "earning"), Decimal("0")
        )
        component_deductions = sum(
            (line.amount for line in lines if line.kind == "deduction"), Decimal("0")
        )
        return SourceReplay(
            result=result,
            reported_gross=Decimal(snapshot.gross),
            reported_deductions=Decimal(snapshot.deductions),
            reported_net=Decimal(snapshot.net),
            component_gross=component_gross,
            component_deductions=component_deductions,
        )


def replay_many(snapshots: Iterable[PayrollSnapshot]) -> list[SourceReplay]:
    calculator = SourceReplayCalculator()
    return [calculator.replay(snapshot) for snapshot in snapshots]
