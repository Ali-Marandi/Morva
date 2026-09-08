from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.persistence.approval_records import PersonnelOrderDecisionRecord, PersonnelOrderSubmissionRecord
from morva.persistence.models import PersonnelOrderRecord
from morva.security.policy import require_distinct_actors

Decision = Literal["approved", "rejected"]
_FINAL_DECISIONS = {"approved", "rejected"}


def ensure_submission(session: Session, order: PersonnelOrderRecord, submitted_by: str) -> PersonnelOrderSubmissionRecord:
    if not submitted_by.strip():
        raise ValueError("submitted_by is required")
    existing = session.scalar(
        select(PersonnelOrderSubmissionRecord).where(PersonnelOrderSubmissionRecord.order_id == order.id)
    )
    if existing is not None:
        if existing.order_no != order.order_no:
            raise ValueError("personnel order submission provenance is inconsistent")
        return existing
    submission = PersonnelOrderSubmissionRecord(
        order_id=order.id,
        order_no=order.order_no,
        submitted_by=submitted_by,
        submitted_at=datetime.utcnow(),
    )
    session.add(submission)
    session.flush()
    append_audit_event(
        event_type="personnel.order.submitted",
        entity_type="personnel_order",
        entity_id=str(order.id),
        actor_id=submitted_by,
        payload={"order_no": order.order_no, "employee_no": order.employee_no},
        reason="submit personnel order for approval",
        session=session,
    )
    return submission


def get_approval(session: Session, order: PersonnelOrderRecord) -> tuple[PersonnelOrderSubmissionRecord | None, PersonnelOrderDecisionRecord | None]:
    submission = session.scalar(
        select(PersonnelOrderSubmissionRecord).where(PersonnelOrderSubmissionRecord.order_id == order.id)
    )
    decision = session.scalar(
        select(PersonnelOrderDecisionRecord).where(PersonnelOrderDecisionRecord.order_id == order.id)
    )
    return submission, decision


def decide_order(
    session: Session,
    order: PersonnelOrderRecord,
    *,
    decided_by: str,
    decision: Decision,
    reason: str | None = None,
) -> PersonnelOrderDecisionRecord:
    if decision not in _FINAL_DECISIONS:
        raise ValueError("invalid personnel order decision")
    if not decided_by.strip():
        raise ValueError("decided_by is required")
    if decision == "rejected" and not (reason and reason.strip()):
        raise ValueError("rejection reason is required")

    submission, existing = get_approval(session, order)
    if submission is None:
        raise ValueError("personnel order has no submission provenance")
    if existing is not None:
        raise ValueError("personnel order already has an immutable final decision")
    require_distinct_actors([submission.submitted_by, decided_by])
    result = PersonnelOrderDecisionRecord(
        order_id=order.id,
        order_no=order.order_no,
        decision=decision,
        decided_by=decided_by,
        reason=reason.strip() if reason else None,
        decided_at=datetime.utcnow(),
    )
    session.add(result)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("personnel order decision already exists") from exc
    append_audit_event(
        event_type=f"personnel.order.{decision}",
        entity_type="personnel_order",
        entity_id=str(order.id),
        actor_id=decided_by,
        payload={
            "order_no": order.order_no,
            "employee_no": order.employee_no,
            "decision": decision,
            "reason": result.reason,
        },
        reason="record final personnel order decision",
        session=session,
    )
    return result


def status_name(decision: PersonnelOrderDecisionRecord | None) -> str:
    return decision.decision if decision is not None else "pending"
