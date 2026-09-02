from __future__ import annotations

from dataclasses import dataclass

from morva.security.policy import Principal, Scope, has_permission


@dataclass(frozen=True, slots=True)
class AccessContext:
    principal: Principal
    organization_unit_id: str


def can_access(*, context: AccessContext, action: str) -> bool:
    if not has_permission(context.principal, action):
        return False
    if context.principal.scope is Scope.MINISTRY:
        return True
    return context.principal.scope_id == context.organization_unit_id
