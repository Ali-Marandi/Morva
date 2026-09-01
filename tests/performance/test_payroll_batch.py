from decimal import Decimal

from morva.payroll.batch import BatchEmployee, PayrollBatchRunner


def test_batch_runner_handles_large_input_without_duplicate_processing():
    employees = tuple(BatchEmployee(f"E{i:06d}", "fixture") for i in range(10_000))
    result = PayrollBatchRunner().run(
        run_id="BENCH-1405-01",
        employees=employees,
        calculate=lambda _employee: (Decimal("100"), Decimal("90")),
        chunk_size=500,
    )
    assert result.processed == 10_000
    assert result.failed == 0
    assert result.gross == Decimal("1000000")
    assert result.net == Decimal("900000")
