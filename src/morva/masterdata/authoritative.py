from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord
from morva.masterdata.validation import MasterDataFinding, validate_master_data


@dataclass(frozen=True, slots=True)
class AuthoritativeMasterDataResult:
    blocking: bool
    findings: tuple[MasterDataFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "blocking": self.blocking,
            "findings": [finding.__dict__ for finding in self.findings],
        }


def validate_authoritative_master_data(session: Session) -> AuthoritativeMasterDataResult:
    base = validate_master_data(session)
    findings = list(base.findings)

    positions = session.scalars(select(PositionRecord).order_by(PositionRecord.code)).all()
    for row in positions:
        if row.effective_to is not None and row.effective_from is not None and row.effective_to < row.effective_from:
            findings.append(
                MasterDataFinding(
                    code="POSITION_INVALID_RANGE",
                    severity="error",
                    entity_type="position",
                    entity_id=row.code,
                    message="position effective_to precedes effective_from",
                )
            )

    assignments = session.scalars(
        select(AssignmentRecord).order_by(AssignmentRecord.employee_no, AssignmentRecord.starts_on, AssignmentRecord.id)
    ).all()
    by_employee: dict[str, list[AssignmentRecord]] = defaultdict(list)
    for row in assignments:
        by_employee[row.employee_no].append(row)

    for employee_no, rows in by_employee.items():
        previous: AssignmentRecord | None = None
        for current in rows:
            if previous is not None:
                previous_end = previous.ends_on
                if previous_end is None or current.starts_on <= previous_end:
                    findings.append(
                        MasterDataFinding(
                            code="ASSIGNMENT_OVERLAP",
                            severity="error",
                            entity_type="assignment",
                            entity_id=str(current.id),
                            message=(
                                f"assignment interval overlaps previous assignment for employee {employee_no}"
                            ),
                        )
                    )
            previous = current

    active_employees = session.scalars(
        select(EmployeeRecord).where(EmployeeRecord.status == "active").order_by(EmployeeRecord.employee_no)
    ).all()
    assigned_employees = set(by_employee)
    for employee in active_employees:
        if employee.employee_no not in assigned_employees:
            findings.append(
                MasterDataFinding(
                    code="ACTIVE_EMPLOYEE_NO_ASSIGNMENT",
                    severity="error",
                    entity_type="employee",
                    entity_id=employee.employee_no,
                    message="active employee has no personnel assignment",
                )
            )

    return AuthoritativeMasterDataResult(
        blocking=base.blocking or any(item.severity == "error" for item in findings if item not in base.findings),
        findings=tuple(findings),
    )
