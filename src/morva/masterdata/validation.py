from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord


Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class MasterDataFinding:
    code: str
    severity: Severity
    entity_type: str
    entity_id: str
    message: str


@dataclass(frozen=True, slots=True)
class MasterDataValidationResult:
    blocking: bool
    organization_count: int
    position_count: int
    employee_count: int
    assignment_count: int
    snapshot_count: int
    findings: tuple[MasterDataFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "blocking": self.blocking,
            "counts": {
                "organizations": self.organization_count,
                "positions": self.position_count,
                "employees": self.employee_count,
                "assignments": self.assignment_count,
                "snapshots": self.snapshot_count,
            },
            "findings": [asdict(item) for item in self.findings],
        }


def _resolve_position(position_ref: str, positions_by_code: dict[str, PositionRecord], positions_by_id: dict[str, PositionRecord]) -> PositionRecord | None:
    row = positions_by_id.get(position_ref)
    return row if row is not None else positions_by_code.get(position_ref)


def _resolve_organization(ref: str, organizations_by_code: dict[str, OrganizationUnitRecord], organizations_by_id: dict[str, OrganizationUnitRecord]) -> OrganizationUnitRecord | None:
    row = organizations_by_id.get(ref)
    return row if row is not None else organizations_by_code.get(ref)


def validate_master_data(session: Session) -> MasterDataValidationResult:
    organizations = session.scalars(select(OrganizationUnitRecord).order_by(OrganizationUnitRecord.code)).all()
    positions = session.scalars(select(PositionRecord).order_by(PositionRecord.code)).all()
    employees = session.scalars(select(EmployeeRecord).order_by(EmployeeRecord.employee_no)).all()
    assignments = session.scalars(select(AssignmentRecord).order_by(AssignmentRecord.employee_no, AssignmentRecord.starts_on)).all()
    snapshots = session.scalars(select(PersonnelSnapshotRecord).order_by(PersonnelSnapshotRecord.employee_no, PersonnelSnapshotRecord.effective_period)).all()

    organizations_by_id = {str(row.id): row for row in organizations}
    organizations_by_code = {row.code: row for row in organizations}
    positions_by_id = {str(row.id): row for row in positions}
    positions_by_code = {row.code: row for row in positions}
    employees_by_no = {row.employee_no: row for row in employees}
    findings: list[MasterDataFinding] = []

    for row in organizations:
        if row.parent_id is None:
            continue
        parent = organizations_by_id.get(str(row.parent_id))
        if parent is None:
            findings.append(
                MasterDataFinding(
                    code="ORG_PARENT_MISSING",
                    severity="error",
                    entity_type="organization_unit",
                    entity_id=row.code,
                    message="organization parent reference does not resolve",
                )
            )
            continue
        visited: set[UUID] = set()
        current = row
        while current.parent_id is not None:
            if current.id in visited:
                findings.append(
                    MasterDataFinding(
                        code="ORG_PARENT_CYCLE",
                        severity="error",
                        entity_type="organization_unit",
                        entity_id=row.code,
                        message="organization hierarchy contains a parent cycle",
                    )
                )
                break
            visited.add(current.id)
            current = organizations_by_id.get(str(current.parent_id))
            if current is None:
                break

    for row in employees:
        org = _resolve_organization(row.organization_unit_id, organizations_by_code, organizations_by_id)
        if org is None:
            findings.append(
                MasterDataFinding(
                    code="EMPLOYEE_ORG_MISSING",
                    severity="error",
                    entity_type="employee",
                    entity_id=row.employee_no,
                    message="employee organization reference does not resolve",
                )
            )
        elif not org.active:
            findings.append(
                MasterDataFinding(
                    code="EMPLOYEE_ORG_INACTIVE",
                    severity="warning",
                    entity_type="employee",
                    entity_id=row.employee_no,
                    message="employee points to an inactive organization",
                )
            )

        position = _resolve_position(row.position_id, positions_by_code, positions_by_id)
        if position is None:
            findings.append(
                MasterDataFinding(
                    code="EMPLOYEE_POSITION_MISSING",
                    severity="error",
                    entity_type="employee",
                    entity_id=row.employee_no,
                    message="employee position reference does not resolve",
                )
            )
        elif not position.active:
            findings.append(
                MasterDataFinding(
                    code="EMPLOYEE_POSITION_INACTIVE",
                    severity="warning",
                    entity_type="employee",
                    entity_id=row.employee_no,
                    message="employee points to an inactive position",
                )
            )

    for row in assignments:
        if row.employee_no not in employees_by_no:
            findings.append(
                MasterDataFinding(
                    code="ASSIGNMENT_EMPLOYEE_MISSING",
                    severity="error",
                    entity_type="assignment",
                    entity_id=str(row.id),
                    message="assignment employee reference does not resolve",
                )
            )
        if row.organization_code not in organizations_by_code:
            findings.append(
                MasterDataFinding(
                    code="ASSIGNMENT_ORG_MISSING",
                    severity="error",
                    entity_type="assignment",
                    entity_id=str(row.id),
                    message="assignment organization code does not resolve",
                )
            )
        if row.position_code not in positions_by_code:
            findings.append(
                MasterDataFinding(
                    code="ASSIGNMENT_POSITION_MISSING",
                    severity="error",
                    entity_type="assignment",
                    entity_id=str(row.id),
                    message="assignment position code does not resolve",
                )
            )
        if row.ends_on is not None and row.ends_on < row.starts_on:
            findings.append(
                MasterDataFinding(
                    code="ASSIGNMENT_INVALID_RANGE",
                    severity="error",
                    entity_type="assignment",
                    entity_id=str(row.id),
                    message="assignment end date precedes start date",
                )
            )

    for row in snapshots:
        if _resolve_organization(row.organization_unit_id, organizations_by_code, organizations_by_id) is None:
            findings.append(
                MasterDataFinding(
                    code="SNAPSHOT_ORG_MISSING",
                    severity="error",
                    entity_type="personnel_snapshot",
                    entity_id=str(row.id),
                    message="snapshot organization reference does not resolve",
                )
            )
        if _resolve_position(row.position_id, positions_by_code, positions_by_id) is None:
            findings.append(
                MasterDataFinding(
                    code="SNAPSHOT_POSITION_MISSING",
                    severity="error",
                    entity_type="personnel_snapshot",
                    entity_id=str(row.id),
                    message="snapshot position reference does not resolve",
                )
            )

    return MasterDataValidationResult(
        blocking=any(item.severity == "error" for item in findings),
        organization_count=len(organizations),
        position_count=len(positions),
        employee_count=len(employees),
        assignment_count=len(assignments),
        snapshot_count=len(snapshots),
        findings=tuple(findings),
    )
