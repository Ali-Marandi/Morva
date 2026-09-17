from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from morva.payroll import PayrollCalculator, PayrollLine


LINES = (
    PayrollLine("BASE", "Base", Decimal("100000000"), "earning", taxable=True, pensionable=True),
    PayrollLine("ALLOW", "Allowance", Decimal("25000000"), "earning", taxable=True),
    PayrollLine("NON_TAX", "Non-taxable", Decimal("5000000"), "earning"),
)


def calculate_once(employee_no: str):
    return PayrollCalculator().calculate(
        employee_no=employee_no,
        period=date(1405, 1, 1),
        ruleset_version="m3-35-concurrency",
        lines=LINES,
    )


def test_parallel_replay_is_deterministic():
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: calculate_once("E-CONCURRENT"), range(256)))

    assert len({result.fingerprint for result in results}) == 1
    assert all(result == results[0] for result in results)


def test_parallel_distinct_employees_produce_distinct_fingerprints():
    employee_numbers = [f"E-{index:05d}" for index in range(512)]
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(calculate_once, employee_numbers))

    fingerprints = {result.fingerprint for result in results}
    assert len(fingerprints) == len(employee_numbers)
