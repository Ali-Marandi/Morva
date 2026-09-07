from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


class ReconciliationMismatchError(RuntimeError):
    """Raised when a payroll batch cannot be released for payment."""


@dataclass(frozen=True, slots=True)
class ReconciliationSnapshot:
    batch_id: str
    employee_count: int
    gross: Decimal
    deductions: Decimal
    net: Decimal


@dataclass(frozen=True, slots=True)
class ThreeWayReconciliation:
    payroll: ReconciliationSnapshot
    accounting: ReconciliationSnapshot
    payment: ReconciliationSnapshot

    @property
    def matched(self) -> bool:
        return self._mismatches() == ()

    def _mismatches(self) -> tuple[str, ...]:
        mismatches: list[str] = []
        snapshots = (("accounting", self.accounting), ("payment", self.payment))
        for label, snapshot in snapshots:
            if snapshot.batch_id != self.payroll.batch_id:
                mismatches.append(f"{label}.batch_id does not match payroll batch")
            if snapshot.employee_count != self.payroll.employee_count:
                mismatches.append(f"{label}.employee_count does not match payroll batch")
            for field in ("gross", "deductions", "net"):
                left = getattr(self.payroll, field)
                right = getattr(snapshot, field)
                if left != right:
                    mismatches.append(f"{label}.{field}={right} differs from payroll.{field}={left}")
        return tuple(mismatches)

    def assert_releaseable(self) -> None:
        mismatches = self._mismatches()
        if mismatches:
            raise ReconciliationMismatchError("three-way reconciliation failed: " + "; ".join(mismatches))
