from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import Header, HTTPException, status

from morva.runtime.config import settings


class Permission(StrEnum):
    CALCULATE_PAYROLL = "payroll:calculate"
    REVIEW_PAYROLL = "payroll:review"
    APPROVE_PAYROLL = "payroll:approve"
    FREEZE_PAYROLL = "payroll:freeze"
    EXPORT_PAYROLL = "payroll:export"
    READ_PAYSLIP = "payslip:read"
    READ_AUDIT = "audit:read"


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: str
    organization_unit_id: str
    mfa_verified: bool
    permissions: frozenset[str]

    def require(self, permission: Permission) -> None:
        if permission.value not in self.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        if self.role in {"ministry_finance", "province_finance", "district_finance", "hr_admin"} and not self.mfa_verified:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA verification required")


def principal_from_headers(
    x_morva_subject: str | None = Header(default=None),
    x_morva_role: str | None = Header(default=None),
    x_morva_org_unit: str | None = Header(default=None),
    x_morva_mfa: str | None = Header(default=None),
    x_morva_permissions: str | None = Header(default=None),
) -> Principal:
    """Resolve a principal for non-production tests/dev only.

    Production deliberately refuses header-based identity. A verified OIDC/SSO
    middleware must provide the trusted principal before privileged routes are enabled.
    """
    if settings.production:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="production authentication requires verified OIDC/SSO middleware",
        )
    if not all((x_morva_subject, x_morva_role, x_morva_org_unit)):
        return Principal(
            subject="dev-user",
            role="ministry_finance",
            organization_unit_id="dev",
            mfa_verified=True,
            permissions=frozenset(permission.value for permission in Permission),
        )
    permissions = frozenset(p.strip() for p in (x_morva_permissions or "").split(",") if p.strip())
    return Principal(
        subject=x_morva_subject or "",
        role=x_morva_role or "",
        organization_unit_id=x_morva_org_unit or "",
        mfa_verified=(x_morva_mfa or "false").lower() == "true",
        permissions=permissions,
    )
