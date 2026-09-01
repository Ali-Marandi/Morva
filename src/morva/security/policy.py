from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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


PRIVILEGED_ROLES = {"admin", "finance_approver", "payroll_approver", "auditor"}


def authorize(principal: Principal, required_role: str, required_scope: Scope) -> None:
    if principal.role != required_role:
        raise PermissionError("required role not granted")
    if principal.scope.value not in {required_scope.value, Scope.MINISTRY.value}:
        raise PermissionError("organization scope violation")
    if principal.role in PRIVILEGED_ROLES and not principal.mfa_verified:
        raise PermissionError("MFA is required for privileged actions")
