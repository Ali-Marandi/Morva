from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.models import PayrollRunEventRecord, PayrollRunRecord
from morva.security.auth import Permission, Principal


ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"data_received"}),
    "data_received": frozenset({"calculated"}),
    "calculated": frozenset({"validated"}),
    "validated": frozenset({"reviewed"}),
    "reviewed": frozenset({"approved"}),
    "approved": frozenset({"frozen"}),
    "frozen": frozenset({"exported"}),
    "exported": frozenset({"submitted"}),
    "submitted": frozenset({"payment_confirmed"}),
    "payment_confirmed": frozenset({"reconciled"}),
    "reconciled": frozenset(),
}

REQUIRED_PERMISSIONS = {
    "data_received": Permission.CALCULATE_PAYROLL,
    "calculated": Permission.CALCULATE_PAYROLL,
    "validated": Permission.REVIEW_PAYROLL,
    "reviewed": Permission.REVIEW_PAYROLL,
    "approved": Permission.APPROVE_PAYROLL,
    "frozen": Permission.FREEZE_PAYROLL,
    "exported": Permission.EXPORT_PAYROLL,
    "submitted": Permission.EXPORT_PAYROLL,
    "payment_confirmed": Permission.EXPORT_PAYROLL,
    "reconciled": Permission.REVIEW_PAYROLL,
}


@dataclass(frozen=True, slots=True)
class TransitionResult:
    run_id: UUID
    from_status: str
    to_status: str
    version: int


def create_run(
    session: Session,
    *,
    period: str,
    ruleset_version: str,
    principal: Principal,
    organization_scope: str,
) -> PayrollRunRecord:
    principal.require(Permission.CALCULATE_PAYROLL)
    run = PayrollRunRecord(
        period=period,
        ruleset_version=ruleset_version,
        organization_scope=organization_scope,
        created_by=principal.subject,
        status="draft",
    )
    session.add(run)
    session.flush()
    return run


def transition(
    session: Session,
    *,
    run_id: UUID,
    target_status: str,
    principal: Principal,
    reason: str | None,
    correlation_id: str | None,
) -> TransitionResult:
    run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one()
    allowed = ALLOWED_TRANSITIONS.get(run.status, frozenset())
    if target_status not in allowed:
        raise ValueError(f"invalid payroll run transition: {run.status} -> {target_status}")
    permission = REQUIRED_PERMISSIONS[target_status]
    principal.require(permission)
    if target_status == "approved" and principal.subject == run.created_by:
        raise PermissionError("separation of duties: creator cannot approve the same payroll run")
    old_status = run.status
    run.status = target_status
    run.version += 1
    now = datetime.utcnow()
    if target_status == "frozen":
        run.frozen_at = now
    elif target_status == "exported":
        run.exported_at = now
    elif target_status == "payment_confirmed":
        run.paid_at = now
    elif target_status == "reconciled":
        run.reconciled_at = now
    session.add(
        PayrollRunEventRecord(
            payroll_run_id=run.id,
            from_status=old_status,
            to_status=target_status,
            actor_id=principal.subject,
            actor_role=principal.role,
            reason=reason,
            correlation_id=correlation_id,
        )
    )
    session.flush()
    return TransitionResult(run.id, old_status, target_status, run.version)
