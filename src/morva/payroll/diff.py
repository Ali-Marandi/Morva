from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from .snapshot import PayrollSnapshot


@dataclass(frozen=True, slots=True)
class LineDiff:
    employee_key: str
    kind: str
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


def _compare_components(
    *,
    employee_key: str,
    kind: str,
    reported: Mapping[str, Decimal],
    recalculated: Mapping[str, Decimal],
) -> list[LineDiff]:
    codes = sorted(set(reported) | set(recalculated))
    lines: list[LineDiff] = []
    for code in codes:
        reported_amount = reported.get(code, Decimal("0"))
        morva_amount = recalculated.get(code, Decimal("0"))
        delta = morva_amount - reported_amount
        if delta == 0:
            classification = "MATCH"
            reason = "reported and recalculated values are identical"
        elif code not in reported:
            classification = "NEW_COMPONENT"
            reason = "Morva produced a component absent from source payroll"
        elif code not in recalculated:
            classification = "MISSING_COMPONENT"
            reason = "source payroll contains a component not produced by Morva"
        else:
            classification = "VALUE_DELTA"
            reason = "same component code, different amount"
        lines.append(
            LineDiff(
                employee_key,
                kind,
                code,
                reported_amount,
                morva_amount,
                delta,
                classification,
                reason,
            )
        )
    return lines


def compare_snapshots(
    snapshot: PayrollSnapshot,
    recalculated_earnings: Mapping[str, Decimal],
    recalculated_deductions: Mapping[str, Decimal] | None = None,
) -> EmployeeDiff:
    deduction_values = recalculated_deductions or {}
    lines = _compare_components(
        employee_key=snapshot.employee_key,
        kind="earning",
        reported=snapshot.components,
        recalculated=recalculated_earnings,
    )
    lines.extend(
        _compare_components(
            employee_key=snapshot.employee_key,
            kind="deduction",
            reported=snapshot.deduction_components,
            recalculated=deduction_values,
        )
    )
    return EmployeeDiff(snapshot.employee_key, tuple(lines))


def population_component_totals(
    snapshots: Iterable[PayrollSnapshot],
    *,
    kind: str = "earning",
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for snapshot in snapshots:
        components = snapshot.components if kind == "earning" else snapshot.deduction_components
        for code, amount in components.items():
            totals[code] = totals.get(code, Decimal("0")) + amount
    return totals
