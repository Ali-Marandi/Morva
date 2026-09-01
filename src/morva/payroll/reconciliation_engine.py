from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from .diff import EmployeeDiff, LineDiff, compare_snapshots
from .snapshot import PayrollSnapshot


@dataclass(frozen=True, slots=True)
class PopulationReconciliation:
    employees: tuple[EmployeeDiff, ...]
    reported_gross: Decimal
    recalculated_gross: Decimal
    reported_deductions: Decimal
    recalculated_deductions: Decimal
    reported_net: Decimal
    recalculated_net: Decimal

    @property
    def gross_delta(self) -> Decimal:
        return self.recalculated_gross - self.reported_gross

    @property
    def deduction_delta(self) -> Decimal:
        return self.recalculated_deductions - self.reported_deductions

    @property
    def net_delta(self) -> Decimal:
        return self.recalculated_net - self.reported_net

    @property
    def matched_employees(self) -> int:
        return sum(1 for item in self.employees if all(line.delta == 0 for line in item.lines))

    @property
    def non_matching_employees(self) -> int:
        return len(self.employees) - self.matched_employees

    def by_classification(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for employee in self.employees:
            for line in employee.lines:
                counts[line.classification] = counts.get(line.classification, 0) + 1
        return counts


def reconcile_population(
    snapshots: Iterable[PayrollSnapshot],
    recalculated_components: Mapping[str, Mapping[str, Decimal]],
    recalculated_deductions: Mapping[str, Mapping[str, Decimal]] | None = None,
) -> PopulationReconciliation:
    """Compare source snapshots against approved recalculation outputs.

    Both earnings and deductions are reconciled line-by-line. The caller is
    responsible for producing these values from an approved Morva calculation
    profile; this engine does not infer legal semantics.
    """
    employees: list[EmployeeDiff] = []
    reported_gross = Decimal(0)
    reported_deductions = Decimal(0)
    reported_net = Decimal(0)
    recalculated_gross = Decimal(0)
    recalculated_deduction_total = Decimal(0)
    recalculated_net = Decimal(0)

    for snapshot in snapshots:
        calculated_earnings = recalculated_components.get(snapshot.employee_key, {})
        calculated_deduction_lines = (
            recalculated_deductions.get(snapshot.employee_key, {})
            if recalculated_deductions is not None
            else {}
        )
        employee_diff = compare_snapshots(
            snapshot,
            calculated_earnings,
            calculated_deduction_lines,
        )
        employees.append(employee_diff)
        reported_gross += snapshot.gross
        reported_deductions += snapshot.deductions
        reported_net += snapshot.net
        calc_gross = sum(calculated_earnings.values(), Decimal(0))
        calc_deduction = sum(calculated_deduction_lines.values(), Decimal(0))
        recalculated_gross += calc_gross
        recalculated_deduction_total += calc_deduction
        recalculated_net += calc_gross - calc_deduction

    return PopulationReconciliation(
        employees=tuple(employees),
        reported_gross=reported_gross,
        recalculated_gross=recalculated_gross,
        reported_deductions=reported_deductions,
        recalculated_deductions=recalculated_deduction_total,
        reported_net=reported_net,
        recalculated_net=recalculated_net,
    )


def flatten_diffs(result: PopulationReconciliation) -> tuple[LineDiff, ...]:
    return tuple(line for employee in result.employees for line in employee.lines)
