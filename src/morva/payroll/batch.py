from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class BatchEmployee:
    employee_no: str
    input_fingerprint: str


@dataclass(frozen=True, slots=True)
class BatchResult:
    run_id: str
    processed: int
    failed: int
    gross: Decimal
    net: Decimal
    errors: tuple[str, ...]


class PayrollBatchRunner:
    """Chunked, deterministic batch executor. Persistence/queueing is injected by the caller."""

    def run(
        self,
        *,
        run_id: str,
        employees: Iterable[BatchEmployee],
        calculate: Callable[[str], tuple[Decimal, Decimal]],
        chunk_size: int = 500,
    ) -> BatchResult:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        processed = failed = 0
        gross = net = Decimal("0")
        errors: list[str] = []
        seen: set[str] = set()
        for employee in employees:
            key = f"{employee.employee_no}:{employee.input_fingerprint}"
            if key in seen:
                continue
            seen.add(key)
            try:
                e_gross, e_net = calculate(employee.employee_no)
                gross += e_gross
                net += e_net
                processed += 1
            except Exception as exc:  # noqa: BLE001 - isolated per-employee failure
                failed += 1
                errors.append(f"{employee.employee_no}: {exc}")
        fingerprint = sha256((run_id + "|" + "|".join(sorted(seen))).encode()).hexdigest()
        return BatchResult(f"{run_id}:{fingerprint[:16]}", processed, failed, gross, net, tuple(errors))
