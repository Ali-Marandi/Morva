from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.approval_records import PersonnelOrderDecisionRecord
from morva.persistence.database import SessionLocal
from morva.persistence.models import AuditEventRecord, EmployeeRecord, PersonnelOrderRecord
from morva.personnel.order_approval import decide_order, get_approval, status_name
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical

router = APIRouter(prefix="/hr", tags=["personnel-order-approval"])


class ApprovalInput(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)


def _load_order(session, employee_no: str, order_no: str) -> tuple[EmployeeRecord, PersonnelOrderRecord]:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    order = session.scalar(
        select(PersonnelOrderRecord).where(
            PersonnelOrderRecord.employee_no == employee_no,
            PersonnelOrderRecord.order_no == order_no,
        )
    )
    if order is None:
        raise HTTPException(status_code=404, detail="personnel order not found")
    return employee, order


def _ensure_submission_from_audit(session, order: PersonnelOrderRecord):
    submission, decision = get_approval(session, order)
    if submission is not None:
        return submission, decision
    audit = session.scalar(
        select(AuditEventRecord)
        .where(
            AuditEventRecord.event_type == "personnel.order.registered",
            AuditEventRecord.entity_id == str(order.id),
        )
        .order_by(AuditEventRecord.sequence_no.asc())
    )
    if audit is None or not audit.actor_id:
        raise HTTPException(status_code=409, detail="personnel order has no immutable submission provenance")
    from morva.personnel.order_approval import ensure_submission

    submission = ensure_submission(session, order, audit.actor_id)
    return submission, decision


@router.get("/employees/{employee_no}/orders/{order_no}/approval")
def get_order_approval(
    employee_no: str,
    order_no: str,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee, order = _load_order(session, employee_no, order_no)
        authorize_hierarchical(session, principal, "personnel.read", employee.organization_unit_id)
        submission, decision = get_approval(session, order)
        audit = session.scalar(
            select(AuditEventRecord)
            .where(AuditEventRecord.event_type == "personnel.order.registered", AuditEventRecord.entity_id == str(order.id))
            .order_by(AuditEventRecord.sequence_no.asc())
        )
        submitted_by = submission.submitted_by if submission else (audit.actor_id if audit else None)
        return {
            "order_no": order.order_no,
            "status": status_name(decision),
            "submitted_by": submitted_by,
            "submitted_at": submission.submitted_at.isoformat() if submission else (audit.created_at.isoformat() if audit else None),
            "decided_by": decision.decided_by if decision else None,
            "decided_at": decision.decided_at.isoformat() if decision else None,
            "reason": decision.reason if decision else None,
        }


@router.post("/employees/{employee_no}/orders/{order_no}/approval", status_code=200)
def decide_order_approval(
    employee_no: str,
    order_no: str,
    payload: ApprovalInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee, order = _load_order(session, employee_no, order_no)
        authorize_hierarchical(session, principal, "personnel.order.approve", employee.organization_unit_id)
        _ensure_submission_from_audit(session, order)
        try:
            decision: PersonnelOrderDecisionRecord = decide_order(
                session,
                order,
                decided_by=principal.user_id,
                decision=payload.decision,
                reason=payload.reason,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type=f"personnel.order.{payload.decision}",
            entity_type="personnel_order",
            entity_id=str(order.id),
            actor_id=principal.user_id,
            payload={"order_no": order.order_no, "employee_no": employee_no, "reason": payload.reason},
            reason=f"personnel order final decision: {payload.decision}",
            session=session,
        )
        session.commit()
        return {
            "order_no": order.order_no,
            "status": decision.decision,
            "decided_by": decision.decided_by,
            "decided_at": decision.decided_at.isoformat(),
            "reason": decision.reason,
        }
