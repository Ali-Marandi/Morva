from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.security.policy import Principal, Scope


_SCOPE_KIND = {
    Scope.SCHOOL: "school",
    Scope.DISTRICT: "district",
    Scope.PROVINCE: "province",
    Scope.MINISTRY: "ministry",
}


def is_within_scope(session: Session, principal: Principal, resource_unit_id: str) -> bool:
    if principal.scope is Scope.MINISTRY:
        return True
    try:
        current_id = UUID(resource_unit_id)
        principal_id = UUID(principal.scope_id)
    except ValueError:
        return principal.scope_id == resource_unit_id
    visited: set[UUID] = set()
    while current_id not in visited:
        visited.add(current_id)
        unit = session.scalar(select(OrganizationUnitRecord).where(OrganizationUnitRecord.id == current_id))
        if unit is None:
            return False
        if current_id == principal_id and unit.kind == _SCOPE_KIND[principal.scope]:
            return True
        if unit.parent_id is None:
            return False
        current_id = unit.parent_id
    return False


def authorize_hierarchical(session: Session, principal: Principal, permission: str, resource_unit_id: str) -> None:
    from morva.security.policy import has_permission, PRIVILEGED_ROLES
    if not has_permission(principal, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="required permission not granted")
    if principal.role in PRIVILEGED_ROLES and not principal.mfa_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="MFA is required for privileged actions")
    if not is_within_scope(session, principal, resource_unit_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="organization hierarchy scope violation")
