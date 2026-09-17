import os
import time
from decimal import Decimal

from morva.payroll.batch import BatchEmployee, PayrollBatchRunner


def test_target_scale_batch_preserves_totals_and_deduplicates():
    target = int(os.getenv("MORVA_M3_35_EMPLOYEES", "10000"))
    assert target >= 10_000

    employees = [BatchEmployee(f"E{i:08d}", "m3-35") for i in range(target)]
    # Add deterministic replay duplicates; the runner must not process them twice.
    employees.extend(employees[::997])

    started = time.perf_counter()
    result = PayrollBatchRunner().run(
        run_id="M3-35-SCALE",
        employees=employees,
        calculate=lambda _employee: (Decimal("100"), Decimal("90")),
        chunk_size=500,
    )
    elapsed = time.perf_counter() - started

    assert result.processed == target
    assert result.failed == 0
    assert result.gross == Decimal(target * 100)
    assert result.net == Decimal(target * 90)
    assert result.gross - result.net == Decimal(target * 10)
    assert elapsed >= 0

    print(
        f"M3.35 scale evidence: employees={target} "
        f"elapsed_seconds={elapsed:.6f} "
        f"throughput_per_second={target / elapsed if elapsed else float('inf'):.2f}"
    )
