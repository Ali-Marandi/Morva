from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from fastapi import Header, HTTPException, status


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
    """Controlled dev/test principal. A real OIDC/SSO verifier replaces this adapter in deployment.

    Production must not trust caller-provided identity headers; set MORVA_AUTH_MODE=oidc
    and provide a verified identity middleware before enabling sensitive routes.
    """
    if not all((x_morva_subject, x_morva_role, x_morva_org_unit)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    permissions = frozenset(p.strip() for p in (x_morva_permissions or "").split(",") if p.strip())
    return Principal(
        subject=x_morva_subject or "",
        role=x_morva_role or "",
        organization_unit_id=x_morva_org_unit or "",
        mfa_verified=(x_morva_mfa or "false").lower() == "true",
        permissions=permissions,
    )
