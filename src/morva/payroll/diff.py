from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .snapshot import PayrollSnapshot


@dataclass(frozen=True, slots=True)
class LineDiff:
    employee_key: str
    component_code: str
    reported: Decimal
    morva: Decimal
    delta: Decimal
    classification: str
    reason: str


@dataclass(frozen=True, slots=True)
class EmployeeDiff:
    employee_key: str
    lines: tuple[LineDiff, ...]

    @property
    def delta_total(self) -> Decimal:
        return sum((line.delta for line in self.lines), Decimal("0"))


def compare_snapshots(snapshot: PayrollSnapshot, recalculated: dict[str, Decimal]) -> EmployeeDiff:
    codes = sorted(set(snapshot.components) | set(recalculated))
    lines: list[LineDiff] = []
    for code in codes:
        reported = snapshot.components.get(code, Decimal("0"))
        morva = recalculated.get(code, Decimal("0"))
        delta = morva - reported
        if delta == 0:
            classification = "MATCH"
            reason = "reported and recalculated values are identical"
        elif code not in snapshot.components:
            classification = "NEW_COMPONENT"
            reason = "Morva produced a component absent from source payroll"
        elif code not in recalculated:
            classification = "MISSING_COMPONENT"
            reason = "source payroll contains a component not produced by Morva"
        else:
            classification = "VALUE_DELTA"
            reason = "same component code, different amount"
        lines.append(LineDiff(snapshot.employee_key, code, reported, morva, delta, classification, reason))
    return EmployeeDiff(snapshot.employee_key, tuple(lines))


def population_component_totals(snapshots: Iterable[PayrollSnapshot]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for snapshot in snapshots:
        for code, amount in snapshot.components.items():
            totals[code] = totals.get(code, Decimal("0")) + amount
    return totals
