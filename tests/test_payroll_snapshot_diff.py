from decimal import Decimal

from morva.payroll.diff import compare_snapshots
from morva.payroll.snapshot import EffectiveOrder, PayrollSnapshot


def snapshot() -> PayrollSnapshot:
    return PayrollSnapshot(
        employee_key="EMP-test",
        period="1405-05",
        employment_type="رسمی",
        org_unit="unit",
        service_region="region",
        work_days="31",
        gross=Decimal("300"),
        deductions=Decimal("50"),
        net=Decimal("250"),
        employer_commitments=Decimal("10"),
        components={"حق شغل-1": Decimal("100"), "حق شاغل-2": Decimal("200")},
        deduction_components={"مالیات-965": Decimal("20")},
        latest_order=EffectiveOrder("1", "تغییر حقوق", "1405/01/01", "1405/01/02", None, None, "فعال", Decimal("300")),
        loan_installment_total=Decimal("30"),
        loan_count=1,
        supplementary=None,
        health=None,
        social=None,
    )


def test_snapshot_totals_and_unexplained_deduction() -> None:
    s = snapshot()
    assert s.component_total == Decimal("300")
    assert s.net == s.gross - s.deductions
    assert s.unexplained_deduction_total == Decimal("0")


def test_line_diff_classifies_missing_and_delta() -> None:
    result = compare_snapshots(snapshot(), {"حق شغل-1": Decimal("110"), "جدید": Decimal("5")})
    by_code = {line.component_code: line for line in result.lines}
    assert by_code["حق شغل-1"].classification == "VALUE_DELTA"
    assert by_code["حق شاغل-2"].classification == "MISSING_COMPONENT"
    assert by_code["جدید"].classification == "NEW_COMPONENT"
