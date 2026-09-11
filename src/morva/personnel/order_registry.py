from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.approval_records import PersonnelOrderDecisionRecord, PersonnelOrderSubmissionRecord
from morva.persistence.models import EmployeeRecord, PersonnelOrderRecord
from morva.personnel.order_approval_policy import require_approved_policy
from morva.personnel.order_integrity import canonical_personnel_order_payload, personnel_order_fingerprint
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


@dataclass(frozen=True, slots=True)
class PersonnelOrderReconciliation:
    employee_no: str
    effective_on: date
    status: str
    orders: tuple[PersonnelOrderRecord, ...]
    blockers: tuple[str, ...]

    @property
    def blocking(self) -> bool:
        return self.status == "blocked"


def _fingerprint_for_order(record: PersonnelOrderRecord) -> str:
    return personnel_order_fingerprint(
        canonical_personnel_order_payload(
            order_no=record.order_no,
            employee_no=record.employee_no,
            order_type=record.order_type,
            issue_date=record.issue_date,
            effective_from=record.effective_date,
            effective_to=date.fromisoformat(record.payload["effective_to"]) if record.payload.get("effective_to") else None,
            legal_reference=record.legal_reference,
            reason=record.reason,
            payload=record.payload or {},
        )
    )


def persist_personnel_order(session: Session, order: PersonnelOrder) -> PersonnelOrderRecord:
    order.validate()
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == order.employee_no))
    if employee is None:
        raise ValueError("employee not found")
    existing = session.scalar(select(PersonnelOrderRecord).where(PersonnelOrderRecord.order_no == order.number))
    payload = {
        "effective_from": order.effective_from.isoformat(),
        "effective_to": order.effective_to.isoformat() if order.effective_to else None,
        "reference": order.reference,
        "lines": [
            {"code": line.code, "amount": str(line.amount), "rule_code": line.rule_code}
            for line in order.lines
        ],
    }
    expected_hash = personnel_order_fingerprint(
        canonical_personnel_order_payload(
            order_no=order.number,
            employee_no=order.employee_no,
            order_type=order.order_type.value,
            issue_date=order.issue_date,
            effective_from=order.effective_from,
            effective_to=order.effective_to,
            legal_reference=order.reference,
            reason=None,
            payload=payload,
        )
    )
    if existing is not None:
        if (
            existing.employee_no != order.employee_no
            or existing.order_type != order.order_type.value
            or existing.issue_date != order.issue_date
            or existing.effective_date != order.effective_from
            or existing.legal_reference != order.reference
            or existing.payload != payload
        ):
            raise ValueError("personnel order already exists with different content")
        if existing.content_hash != expected_hash:
            raise ValueError("personnel order integrity fingerprint mismatch")
        return existing
    record = PersonnelOrderRecord(
        order_no=order.number,
        employee_no=order.employee_no,
        order_type=order.order_type.value,
        issue_date=order.issue_date,
        effective_date=order.effective_from,
        legal_reference=order.reference,
        reason=None,
        payload=payload,
        content_hash=expected_hash,
    )
    session.add(record)
    session.flush()
    return record


def record_to_personnel_order(record: PersonnelOrderRecord) -> PersonnelOrder:
    payload = record.payload or {}
    lines = tuple(
        OrderLine(code=item["code"], amount=Decimal(str(item["amount"])), rule_code=item.get("rule_code"))
        for item in payload.get("lines", [])
    )
    return PersonnelOrder(
        number=record.order_no,
        employee_no=record.employee_no,
        order_type=OrderType(record.order_type),
        issue_date=record.issue_date,
        effective_from=record.effective_date,
        effective_to=date.fromisoformat(payload["effective_to"]) if payload.get("effective_to") else None,
        reference=payload.get("reference") or record.legal_reference,
        lines=lines,
    )


def reconcile_personnel_order_effective_state(
    session: Session,
    employee_no: str,
    effective_on: date,
) -> PersonnelOrderReconciliation:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        return PersonnelOrderReconciliation(
            employee_no=employee_no,
            effective_on=effective_on,
            status="blocked",
            orders=(),
            blockers=("employee not found",),
        )

    decisions = session.scalars(
        select(PersonnelOrderDecisionRecord)
        .join(PersonnelOrderRecord, PersonnelOrderRecord.id == PersonnelOrderDecisionRecord.order_id)
        .where(
            PersonnelOrderRecord.employee_no == employee_no,
            PersonnelOrderRecord.effective_date <= effective_on,
            PersonnelOrderDecisionRecord.decision == "approved",
        )
        .order_by(PersonnelOrderRecord.effective_date.desc(), PersonnelOrderRecord.order_no.desc())
    ).all()

    reconciled: list[PersonnelOrderRecord] = []
    blockers: list[str] = []
    for decision in decisions:
        record = session.get(PersonnelOrderRecord, decision.order_id)
        if record is None:
            blockers.append(f"order-missing:{decision.order_no}")
            continue
        submission = session.scalar(
            select(PersonnelOrderSubmissionRecord).where(PersonnelOrderSubmissionRecord.order_id == record.id)
        )
        if submission is None:
            blockers.append(f"submission-missing:{record.order_no}")
            continue
        if record.content_hash is None:
            blockers.append(f"order-fingerprint-missing:{record.order_no}")
            continue
        try:
            recomputed_hash = _fingerprint_for_order(record)
        except (KeyError, TypeError, ValueError) as exc:
            blockers.append(f"order-payload-invalid:{record.order_no}:{type(exc).__name__}")
            continue
        if recomputed_hash != record.content_hash:
            blockers.append(f"order-fingerprint-mismatch:{record.order_no}")
            continue
        if decision.order_fingerprint != record.content_hash:
            blockers.append(f"decision-fingerprint-mismatch:{record.order_no}")
            continue
        if submission.order_fingerprint != record.content_hash:
            blockers.append(f"submission-fingerprint-mismatch:{record.order_no}")
            continue
        if not submission.approval_policy_code or not submission.approval_policy_hash:
            blockers.append(f"approval-policy-provenance-missing:{record.order_no}")
            continue
        try:
            require_approved_policy(
                session,
                policy_code=submission.approval_policy_code,
                order_type=record.order_type,
                submitted_role=submission.submitted_role or "",
                decided_role=decision.decided_role or "",
                expected_policy_hash=submission.approval_policy_hash,
            )
        except ValueError as exc:
            blockers.append(f"approval-policy-invalid:{record.order_no}:{str(exc)}")
            continue
        try:
            order = record_to_personnel_order(record)
        except (KeyError, TypeError, ValueError) as exc:
            blockers.append(f"order-schema-invalid:{record.order_no}:{type(exc).__name__}")
            continue
        if order.employee_no != employee.employee_no:
            blockers.append(f"employee-mismatch:{record.order_no}")
            continue
        if not order.is_effective_on(effective_on):
            continue
        reconciled.append(record)

    status = "blocked" if blockers else "reconciled"
    return PersonnelOrderReconciliation(
        employee_no=employee_no,
        effective_on=effective_on,
        status=status,
        orders=tuple(reconciled),
        blockers=tuple(blockers),
    )


def effective_personnel_orders(session: Session, employee_no: str, effective_on: date) -> list[PersonnelOrderRecord]:
    result = reconcile_personnel_order_effective_state(session, employee_no, effective_on)
    if result.blocking:
        raise ValueError("personnel order effective-state reconciliation is blocked: " + "; ".join(result.blockers))
    return list(result.orders)
