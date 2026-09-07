from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.approval_records import PersonnelOrderDecisionRecord
from morva.persistence.models import EmployeeRecord, PersonnelOrderRecord
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


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
    return [record for record in records if record_to_personnel_order(record).is_effective_on(effective_on)]
