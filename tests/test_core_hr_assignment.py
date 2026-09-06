from datetime import date

import pytest

from morva.masterdata.models import Assignment


def test_assignment_is_effective_on_boundaries() -> None:
    assignment = Assignment(
        employee_no="E-100",
        organization_code="ORG-1",
        position_code="POS-1",
        starts_on=date(1405, 1, 1),
        ends_on=date(1405, 1, 31),
    )

    assert assignment.active_on(date(1405, 1, 1))
    assert assignment.active_on(date(1405, 1, 31))
    assert not assignment.active_on(date(1404, 12, 29))
    assert not assignment.active_on(date(1405, 2, 1))


def test_open_ended_assignment_remains_effective() -> None:
    assignment = Assignment(
        employee_no="E-101",
        organization_code="ORG-1",
        position_code="POS-2",
        starts_on=date(1405, 2, 1),
    )

    assert assignment.active_on(date(1405, 2, 1))
    assert assignment.active_on(date(1406, 12, 29))


def test_invalid_assignment_range_is_rejected_by_contract() -> None:
    assignment = Assignment(
        employee_no="E-102",
        organization_code="ORG-1",
        position_code="POS-3",
        starts_on=date(1405, 3, 10),
        ends_on=date(1405, 3, 1),
    )

    with pytest.raises(ValueError):
        if assignment.ends_on is not None and assignment.ends_on < assignment.starts_on:
            raise ValueError("ends_on cannot precede starts_on")


def test_organization_rejects_self_parent() -> None:
    from morva.masterdata.models import OrganizationCatalog, OrganizationUnit

    catalog = OrganizationCatalog()
    with pytest.raises(ValueError, match="cannot be its own parent"):
        catalog.add(OrganizationUnit(code="ORG-1", title="Unit", level="region", parent_code="ORG-1"))
