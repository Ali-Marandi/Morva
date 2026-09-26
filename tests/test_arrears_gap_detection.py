from datetime import date

import pytest

from morva.payroll.retro import detect_arrears_gap


def test_detect_arrears_gap_separates_effective_and_issue_dates() -> None:
    gap = detect_arrears_gap(
        employee_no="E-1405-001",
        order_no="ORD-1405-001",
        effective_from=date(2026, 1, 1),
        issue_date=date(2026, 1, 17),
    )

    assert gap.is_retroactive is True
    assert gap.gap_days == 16
    assert gap.effective_from == date(2026, 1, 1)
    assert gap.issue_date == date(2026, 1, 17)


def test_same_day_issue_has_no_retroactive_gap() -> None:
    gap = detect_arrears_gap(
        employee_no="E-1405-002",
        order_no="ORD-1405-002",
        effective_from=date(2026, 1, 17),
        issue_date=date(2026, 1, 17),
    )

    assert gap.is_retroactive is False
    assert gap.gap_days == 0


def test_issue_date_before_effective_date_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot precede"):
        detect_arrears_gap(
            employee_no="E-1405-003",
            order_no="ORD-1405-003",
            effective_from=date(2026, 2, 1),
            issue_date=date(2026, 1, 17),
        )


@pytest.mark.parametrize(
    ("employee_no", "order_no"),
    [("", "ORD-1"), ("E-1", "")],
)
def test_required_identity_fields_are_enforced(employee_no: str, order_no: str) -> None:
    with pytest.raises(ValueError):
        detect_arrears_gap(
            employee_no=employee_no,
            order_no=order_no,
            effective_from=date(2026, 1, 1),
            issue_date=date(2026, 1, 2),
        )
