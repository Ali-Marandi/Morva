from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.persistence.approval_records import PersonnelOrderDecisionRecord, PersonnelOrderSubmissionRecord
from morva.persistence.models import PersonnelOrderRecord
from morva.personnel.order_approval_policy import require_approved_policy
from morva.personnel.order_registry import _fingerprint_for_order
from morva.security.policy import require_distinct_actors

Decision = Literal["approved", "rejected"]
_FINAL_DECISIONS = {"approved", "rejected"}


def ensure_submission(
    session: Session,
    order: PersonnelOrderRecord,
    submitted_by: str,
    *,
    policy_code: str,
    submitted_role: str,
) -> PersonnelOrderSubmissionRecord:
    if not submitted_by.strip():
        raise ValueError("submitted_by is required")
    if not submitted_role.strip():
        raise ValueError("submitted_role is required")
    order_fingerprint = order.content_hash or _fingerprint_for_order(order)
    if order.content_hash is None:
        raise ValueError("personnel order has no persisted integrity fingerprint")
    policy = require_approved_policy(
        session,
        policy_code=policy_code,
        order_type=order.order_type,
        submitted_role=submitted_role,
    )
    existing = session.scalar(
        select(PersonnelOrderSubmissionRecord).where(PersonnelOrderSubmissionRecord.order_id == order.id)
    )
    if existing is not None:
        if existing.order_no != order.order_no:
            raise ValueError("personnel order submission provenance is inconsistent")
        if existing.order_fingerprint != order_fingerprint:
            raise ValueError("personnel order submission fingerprint mismatch")
        if existing.approval_policy_code != policy.policy_code or existing.approval_policy_hash != policy.policy_hash:
            raise ValueError("personnel order submission approval policy mismatch")
        return existing
    submission = PersonnelOrderSubmissionRecord(
        order_id=order.id,
        order_no=order.order_no,
        submitted_by=submitted_by,
        submitted_role=submitted_role.strip(),
        submitted_at=datetime.utcnow(),
        order_fingerprint=order_fingerprint,
        approval_policy_code=policy.policy_code,
        approval_policy_hash=policy.policy_hash,
    )
    session.add(submission)
    session.flush()
    append_audit_event(
        event_type="personnel.order.submitted",
        entity_type="personnel_order",
        entity_id=str(order.id),
        actor_id=submitted_by,
        payload={
            "order_no": order.order_no,
            "employee_no": order.employee_no,
            "order_fingerprint": order_fingerprint,
            "approval_policy_code": policy.policy_code,
            "approval_policy_hash": policy.policy_hash,
            "submitted_role": submitted_role.strip(),
        },
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
    decided_role: str,
    decision: Decision,
    reason: str | None = None,
) -> PersonnelOrderDecisionRecord:
    if decision not in _FINAL_DECISIONS:
        raise ValueError("invalid personnel order decision")
    if not decided_by.strip():
        raise ValueError("decided_by is required")
    if not decided_role.strip():
        raise ValueError("decided_role is required")
    if decision == "rejected" and not (reason and reason.strip()):
        raise ValueError("rejection reason is required")

    submission, existing = get_approval(session, order)
    if submission is None:
        raise ValueError("personnel order has no submission provenance")
    if order.content_hash is None or _fingerprint_for_order(order) != order.content_hash:
        raise ValueError("personnel order integrity fingerprint mismatch")
    if submission.order_fingerprint != order.content_hash:
        raise ValueError("personnel order submission fingerprint mismatch")
    if not submission.approval_policy_code or not submission.approval_policy_hash:
        raise ValueError("personnel order has no persisted approval policy provenance")
    policy = require_approved_policy(
        session,
        policy_code=submission.approval_policy_code,
        order_type=order.order_type,
        submitted_role=submission.submitted_role or "",
        decided_role=decided_role,
    )
    if submission.approval_policy_hash != policy.policy_hash:
        raise ValueError("personnel order submission approval policy fingerprint mismatch")
    if existing is not None:
        raise ValueError("personnel order already has an immutable final decision")
    try:
        require_distinct_actors([submission.submitted_by, decided_by])
    except HTTPException as exc:
        if exc.status_code == 409:
            raise ValueError("separation of duties violation: actors must be distinct") from exc
        raise
    result = PersonnelOrderDecisionRecord(
        order_id=order.id,
        order_no=order.order_no,
        decision=decision,
        decided_by=decided_by,
        decided_role=decided_role.strip(),
        reason=reason.strip() if reason else None,
        decided_at=datetime.utcnow(),
        order_fingerprint=order.content_hash,
        approval_policy_code=policy.policy_code,
        approval_policy_hash=policy.policy_hash,
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
            "order_fingerprint": order.content_hash,
            "approval_policy_code": policy.policy_code,
            "approval_policy_hash": policy.policy_hash,
            "decided_role": decided_role.strip(),
        },
        reason="record final personnel order decision",
        session=session,
    )
    return result


def status_name(decision: PersonnelOrderDecisionRecord | None) -> str:
    return decision.decision if decision is not None else "pending"
