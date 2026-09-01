from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class Scope(StrEnum):
    SCHOOL = "school"
    DISTRICT = "district"
    PROVINCE = "province"
    MINISTRY = "ministry"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    role: str
    scope: Scope
    scope_id: str
    mfa_verified: bool = False


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "employee": frozenset({"self.read", "self.objection.create"}),
    "school_finance": frozenset({"payroll.run.create", "payroll.run.calculate", "payroll.read"}),
    "district_finance": frozenset({"payroll.run.create", "payroll.run.calculate", "payroll.read", "payroll.review"}),
    "province_finance": frozenset({"payroll.read", "payroll.review", "payroll.approve"}),
    "ministry_finance": frozenset({"payroll.read", "payroll.review", "payroll.approve"}),
    "hr_admin": frozenset({"personnel.read", "personnel.write", "payroll.read"}),
    "auditor": frozenset({"audit.read", "payroll.read"}),
    "admin": frozenset({"*"}),
}

PRIVILEGED_ROLES = frozenset({"admin", "finance_approver", "payroll_approver", "auditor", "district_finance", "province_finance", "ministry_finance"})


def has_permission(principal: Principal, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(principal.role, frozenset())
    return "*" in permissions or permission in permissions


def authorize(
    principal: Principal,
    permission: str,
    required_scope: Scope,
    *,
    resource_scope_id: str | None = None,
    privileged: bool = False,
) -> None:
    if not has_permission(principal, permission):
        raise PermissionError("required permission not granted")
    if privileged or principal.role in PRIVILEGED_ROLES:
        if not principal.mfa_verified:
            raise PermissionError("MFA is required for privileged actions")
    if principal.scope is not Scope.MINISTRY:
        if principal.scope is not required_scope:
            raise PermissionError("organization scope level violation")
        if resource_scope_id is not None and principal.scope_id != resource_scope_id:
            raise PermissionError("organization scope violation")


def require_distinct_actors(actors: Iterable[str | None]) -> None:
    values = [actor for actor in actors if actor]
    if len(values) != len(set(values)):
        raise PermissionError("separation of duties violation: actors must be distinct")
