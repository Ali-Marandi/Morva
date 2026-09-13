from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select

from morva.persistence.models import EmployeeRecord


@dataclass(frozen=True, slots=True)
class IdentityDirectoryResolution:
    lookup_value: str
    employee: EmployeeRecord | None
    match_type: str | None
    candidate_employee_nos: tuple[str, ...]
    reason: str

    @property
    def resolved(self) -> bool:
        return self.employee is not None

    @property
    def ambiguous(self) -> bool:
        return self.employee is None and len(self.candidate_employee_nos) > 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "lookup_value": self.lookup_value,
            "resolved": self.resolved,
            "ambiguous": self.ambiguous,
            "employee_no": self.employee.employee_no if self.employee else None,
            "match_type": self.match_type,
            "candidate_employee_nos": list(self.candidate_employee_nos),
            "reason": self.reason,
        }


def reconcile_employee_identity(session, external_identity: str) -> IdentityDirectoryResolution:
    """Resolve an authenticated subject to exactly one canonical employee record.

    Matching may use the canonical employee number or the immutable source-system
    employee key. Zero matches remain unmapped and multiple distinct matches fail
    closed as ambiguous; no heuristic matching or automatic directory mutation is
    performed here.
    """
    lookup_value = external_identity.strip()
    if not lookup_value:
        return IdentityDirectoryResolution(
            lookup_value="",
            employee=None,
            match_type=None,
            candidate_employee_nos=(),
            reason="empty external identity",
        )

    rows = session.scalars(
        select(EmployeeRecord)
        .where(
            or_(
                EmployeeRecord.employee_no == lookup_value,
                EmployeeRecord.source_employee_key == lookup_value,
            )
        )
        .order_by(EmployeeRecord.employee_no.asc())
    ).all()

    candidate_employee_nos = tuple(sorted({row.employee_no for row in rows}))
    if not rows:
        return IdentityDirectoryResolution(
            lookup_value=lookup_value,
            employee=None,
            match_type=None,
            candidate_employee_nos=(),
            reason="identity is not mapped to the employee directory",
        )
    if len(candidate_employee_nos) != 1:
        return IdentityDirectoryResolution(
            lookup_value=lookup_value,
            employee=None,
            match_type=None,
            candidate_employee_nos=candidate_employee_nos,
            reason="identity maps to multiple employee records",
        )

    employee = rows[0]
    matched_employee_no = employee.employee_no == lookup_value
    matched_source_key = employee.source_employee_key == lookup_value
    if matched_employee_no and matched_source_key:
        match_type = "employee_no_and_source_employee_key"
    elif matched_employee_no:
        match_type = "employee_no"
    else:
        match_type = "source_employee_key"

    return IdentityDirectoryResolution(
        lookup_value=lookup_value,
        employee=employee,
        match_type=match_type,
        candidate_employee_nos=candidate_employee_nos,
        reason="identity resolved to exactly one employee record",
    )
