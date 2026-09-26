from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from morva.integrations.statutory_funds import StatutoryFund


class StatutoryReconciliationMismatch(RuntimeError):
    """Raised when a statutory-fund settlement cannot be proven to match Morva."""


@dataclass(frozen=True, slots=True)
class StatutoryFundSettlementSnapshot:
    fund: StatutoryFund
    batch_id: str
    employee_count: int
    expected_total: Decimal
    settled_total: Decimal

    @property
    def matched(self) -> bool:
        return (
            self.batch_id.strip() != ""
            and self.employee_count >= 0
            and self.expected_total == self.settled_total
        )

    def assert_reconciled(self) -> None:
        # تطبیق صندوق باید بر مبنای شناسه بچ، جمع مبلغ و تعداد افراد بدون هیچ نرخ استنباطی انجام شود.
        if not self.batch_id.strip():
            raise StatutoryReconciliationMismatch("statutory reconciliation requires batch_id")
        if self.employee_count < 0:
            raise StatutoryReconciliationMismatch("statutory reconciliation employee_count is invalid")
        if self.expected_total != self.settled_total:
            raise StatutoryReconciliationMismatch(
                f"{self.fund.value} settlement mismatch: "
                f"expected={self.expected_total} settled={self.settled_total}"
            )


def assert_all_statutory_funds_reconciled(
    snapshots: tuple[StatutoryFundSettlementSnapshot, ...],
) -> None:
    seen: set[StatutoryFund] = set()
    for snapshot in snapshots:
        if snapshot.fund in seen:
            raise StatutoryReconciliationMismatch(
                f"duplicate statutory fund reconciliation: {snapshot.fund.value}"
            )
        seen.add(snapshot.fund)
        snapshot.assert_reconciled()
