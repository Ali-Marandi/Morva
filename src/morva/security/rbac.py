from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Scope(StrEnum):
    SCHOOL = "school"
    DISTRICT = "district"
    PROVINCE = "province"
    MINISTRY = "ministry"


class Role(StrEnum):
    EMPLOYEE = "employee"
    SCHOOL_FINANCE = "school_finance"
    DISTRICT_FINANCE = "district_finance"
    PROVINCE_FINANCE = "province_finance"
    MINISTRY_FINANCE = "ministry_finance"
    HR_ADMIN = "hr_admin"
    AUDITOR = "auditor"


@dataclass(frozen=True, slots=True)
class AccessContext:
    role: Role
    scope: Scope
    organization_unit_id: str


def can_access(*, context: AccessContext, employee_organization_unit_id: str, action: str) -> bool:
    if context.role == Role.AUDITOR:
        return action in {"read_audit", "read_report"}
    if context.scope == Scope.MINISTRY:
        return context.role in {Role.MINISTRY_FINANCE, Role.HR_ADMIN} 
    return context.organization_unit_id == employee_organization_unit_id
