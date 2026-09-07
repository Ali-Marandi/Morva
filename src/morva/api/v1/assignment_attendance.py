from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.persistence.database import SessionLocal
from morva.persistence.domain_extensions import AssignmentRecord, AttendanceFactRecord
from morva.personnel.assignment_attendance import (
    approve_attendance_fact,
    register_assignment,
    register_attendance_fact,
    review_attendance_fact,
)
from morva.persistence.models import EmployeeRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical

router = APIRouter(prefix="/hr", tags=["assignment-attendance"])


class AssignmentInput(BaseModel):
    organization_code: str = Field(min_length=1, max_length=50)
    position_code: str = Field(min_length=1, max_length=50)
    starts_on: date
    ends_on: date | None = None
    acting: bool = False
    source_reference: str | None = Field(default=None, max_length=150)
    source_hash: str | None = Field(default=None, min_length=64, max_length=64)


class AttendanceInput(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    source_record_key: str = Field(min_length=1, max_length=150)
    worked_units: Decimal = Field(ge=0)
    leave_units: Decimal = Field(ge=0)
    absence_units: Decimal = Field(ge=0)
    source_hash: str = Field(min_length=64, max_length=64)
    evidence: dict[str, object] = Field(default_factory=dict)


def _employee(session, employee_no: str) -> EmployeeRecord:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return employee


def _authorize(session, principal: Principal, employee: EmployeeRecord, permission: str) -> None:
    authorize_hierarchical(session, principal, permission, employee.organization_unit_id)


def _assignment(record: AssignmentRecord) -> dict[str, object]:
    return {key: value for key, value in record.__dict__.items() if not key.startswith("_")}


def _attendance(record: AttendanceFactRecord) -> dict[str, object]:
    return {key: value for key, value in record.__dict__.items() if not key.startswith("_")}


@router.post("/employees/{employee_no}/assignments", status_code=201)
def create_assignment(
    employee_no: str,
    payload: AssignmentInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.write")
        try:
            result = register_assignment(
                session,
                employee_no=employee_no,
                organization_code=payload.organization_code,
                position_code=payload.position_code,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                acting=payload.acting,
                source_reference=payload.source_reference,
                source_hash=payload.source_hash,
                actor_id=principal.user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        record = session.get(AssignmentRecord, result.assignment_id)
        session.commit()
        assert record is not None
        return {"status": result.status, "item": _assignment(record)}


@router.get("/employees/{employee_no}/assignments")
def list_assignments(
    employee_no: str,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.read")
        records = session.scalars(
            select(AssignmentRecord)
            .where(AssignmentRecord.employee_no == employee_no)
            .order_by(AssignmentRecord.starts_on.desc())
        ).all()
        return {"employee_no": employee_no, "items": [_assignment(item) for item in records]}


@router.post("/employees/{employee_no}/attendance", status_code=201)
def create_attendance(
    employee_no: str,
    payload: AttendanceInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.write")
        try:
            result = register_attendance_fact(
                session,
                employee_no=employee_no,
                period=payload.period,
                source_record_key=payload.source_record_key,
                worked_units=payload.worked_units,
                leave_units=payload.leave_units,
                absence_units=payload.absence_units,
                source_hash=payload.source_hash,
                evidence=payload.evidence,
                actor_id=principal.user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        record = session.get(AttendanceFactRecord, result.attendance_id)
        session.commit()
        assert record is not None
        return {"status": result.status, "item": _attendance(record)}


@router.get("/employees/{employee_no}/attendance")
def list_attendance(
    employee_no: str,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.read")
        records = session.scalars(
            select(AttendanceFactRecord)
            .where(AttendanceFactRecord.employee_no == employee_no)
            .order_by(AttendanceFactRecord.period.desc(), AttendanceFactRecord.source_record_key)
        ).all()
        return {"employee_no": employee_no, "items": [_attendance(item) for item in records]}


@router.post("/attendance/{attendance_id}/review")
def review_attendance(attendance_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        try:
            record = session.get(AttendanceFactRecord, attendance_id)
            if record is None:
                raise ValueError("attendance fact not found")
            employee = _employee(session, record.employee_no)
            _authorize(session, principal, employee, "personnel.review")
            record = review_attendance_fact(session, attendance_id, principal.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": record.status, "item": _attendance(record)}


@router.post("/attendance/{attendance_id}/approve")
def approve_attendance(
    attendance_id: UUID,
    reviewer_id: str = Query(min_length=1),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        try:
            record = session.get(AttendanceFactRecord, attendance_id)
            if record is None:
                raise ValueError("attendance fact not found")
            employee = _employee(session, record.employee_no)
            _authorize(session, principal, employee, "personnel.approve")
            record = approve_attendance_fact(session, attendance_id, principal.user_id, reviewer_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": record.status, "item": _attendance(record)}
