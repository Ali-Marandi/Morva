from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkflowStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EFFECTIVE = "effective"


class Role(StrEnum):
    HR_OPERATOR = "hr_operator"
    HR_REVIEWER = "hr_reviewer"
    FINANCE_OPERATOR = "finance_operator"
    FINANCE_APPROVER = "finance_approver"
    PAYROLL_APPROVER = "payroll_approver"
    AUDITOR = "auditor"
    EMPLOYEE = "employee"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class ApprovalAction:
    actor_id: str
    role: Role
    action: str
    status_before: WorkflowStatus
    status_after: WorkflowStatus
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SegregationPolicy:
    """Separation-of-duties rules. The same actor cannot create and approve."""

    forbid_same_actor: bool = True
    sensitive_actions: tuple[str, ...] = (
        "approve_order",
        "approve_payroll",
        "release_payment",
        "activate_rule",
        "override_validation",
    )

    def check(self, history: tuple[ApprovalAction, ...], actor_id: str, action: str) -> None:
        if not self.forbid_same_actor or action not in self.sensitive_actions:
            return
        if any(item.actor_id == actor_id and item.action in {"create", "submit", "calculate"} for item in history):
            raise PermissionError("separation of duties violation")


_ALLOWED = {
    WorkflowStatus.DRAFT: {WorkflowStatus.SUBMITTED, WorkflowStatus.CANCELLED},
    WorkflowStatus.SUBMITTED: {WorkflowStatus.REVIEWED, WorkflowStatus.REJECTED},
    WorkflowStatus.REVIEWED: {WorkflowStatus.APPROVED, WorkflowStatus.REJECTED},
    WorkflowStatus.APPROVED: {WorkflowStatus.EFFECTIVE, WorkflowStatus.CANCELLED},
    WorkflowStatus.REJECTED: {WorkflowStatus.DRAFT, WorkflowStatus.CANCELLED},
    WorkflowStatus.CANCELLED: set(),
    WorkflowStatus.EFFECTIVE: set(),
}


def transition(status: WorkflowStatus, target: WorkflowStatus) -> None:
    if target not in _ALLOWED[status]:
        raise ValueError(f"invalid workflow transition: {status} -> {target}")
