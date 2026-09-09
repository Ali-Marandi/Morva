from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.approval_records import PersonnelOrderDecisionRecord
from morva.persistence.models import EmployeeRecord, PersonnelOrderRecord
from morva.personnel.order_integrity import canonical_personnel_order_payload, personnel_order_fingerprint
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


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


def effective_personnel_orders(session: Session, employee_no: str, effective_on: date) -> list[PersonnelOrderRecord]:
    records = session.scalars(
        select(PersonnelOrderRecord)
        .join(PersonnelOrderDecisionRecord, PersonnelOrderDecisionRecord.order_id == PersonnelOrderRecord.id)
        .where(
            PersonnelOrderRecord.employee_no == employee_no,
            PersonnelOrderRecord.effective_date <= effective_on,
            PersonnelOrderDecisionRecord.decision == "approved",
        )
        .order_by(PersonnelOrderRecord.effective_date.desc(), PersonnelOrderRecord.order_no.desc())
    ).all()
    effective: list[PersonnelOrderRecord] = []
    for record in records:
        decision = session.scalar(
            select(PersonnelOrderDecisionRecord).where(PersonnelOrderDecisionRecord.order_id == record.id)
        )
        if record.content_hash is None or decision is None or decision.order_fingerprint != record.content_hash:
            continue
        if _fingerprint_for_order(record) != record.content_hash:
            continue
        if record_to_personnel_order(record).is_effective_on(effective_on):
            effective.append(record)
    return effective
