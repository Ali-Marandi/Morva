from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ImportRecord:
    employee_key: str
    source: str
    period: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReconciliationException:
    employee_key: str
    code: str
    expected: Decimal
    actual: Decimal
    delta: Decimal
    source: str
    severity: str = "warning"
    details: str = ""


@dataclass(slots=True)
class ImportReport:
    source_period: str
    source_rows: dict[str, int] = field(default_factory=dict)
    unique_employees: int = 0
    join_counts: dict[str, int] = field(default_factory=dict)
    aggregate_controls: dict[str, Decimal] = field(default_factory=dict)
    exceptions: list[ReconciliationException] = field(default_factory=list)

    @property
    def critical_exception_count(self) -> int:
        return sum(1 for item in self.exceptions if item.severity == "critical")
