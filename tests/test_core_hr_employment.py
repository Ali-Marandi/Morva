from datetime import date

import pytest

from morva.domain import EmployeeStatus, Employment, EmploymentType


def employment(start: date, end: date | None = None, employee_no: str = "E-1") -> Employment:
    return Employment(
        employee_no=employee_no,
        employment_type=EmploymentType.PERMANENT,
        organization_unit_id="ORG-1",
        position_id="POS-1",
        starts_on=start,
        ends_on=end,
        status=EmployeeStatus.ACTIVE,
    )


def test_employment_is_active_on_boundary_dates() -> None:
    record = employment(date(1405, 1, 1), date(1405, 6, 30))
    assert record.active_on(date(1405, 1, 1))
    assert record.active_on(date(1405, 6, 30))
    assert not record.active_on(date(1405, 7, 1))


def test_employment_rejects_overlapping_intervals() -> None:
    records = (
        employment(date(1405, 1, 1), date(1405, 6, 30)),
        employment(date(1405, 6, 30), None),
    )
    with pytest.raises(ValueError, match="employment intervals overlap"):
        Employment.ensure_non_overlapping(records)


def test_employment_allows_adjacent_intervals_without_overlap() -> None:
    records = (
        employment(date(1405, 1, 1), date(1405, 6, 30)),
        employment(date(1405, 7, 1), None),
    )
    Employment.ensure_non_overlapping(records)
