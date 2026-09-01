from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ReconciliationFinding:
    code: str
    severity: str
    message: str
    difference: Decimal = Decimal(0)


def reconcile_totals(
    *,
    morva: Mapping[str, Decimal],
    external: Mapping[str, Decimal],
    tolerance: Decimal = Decimal("0.00"),
) -> tuple[ReconciliationFinding, ...]:
    findings: list[ReconciliationFinding] = []
    for key in sorted(set(morva) | set(external)):
        left = morva.get(key, Decimal(0))
        right = external.get(key, Decimal(0))
        difference = left - right
        if abs(difference) > tolerance:
            findings.append(
                ReconciliationFinding(
                    code=f"TOTAL_MISMATCH:{key}",
                    severity="error",
                    message=f"Reconciliation mismatch for {key}",
                    difference=difference,
                )
            )
    return tuple(findings)
