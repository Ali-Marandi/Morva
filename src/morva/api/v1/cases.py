from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.models import EmployeeRecord
from morva.persistence.self_service_models import EmployeeCaseRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical
from morva.security.policy import authorize

router = APIRouter(prefix="/cases", tags=["objection-case-management"])


class CaseCreate(BaseModel):
    category: Literal["payroll", "personnel_order", "attendance", "deduction", "other"]
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class CaseStatusUpdate(BaseModel):
    status: Literal["under_review", "resolved", "rejected", "closed"]
    resolution: str | None = Field(default=None, max_length=5000)


def _self_employee(session, principal: Principal) -> EmployeeRecord:
    authorize(principal, "self.read", principal.scope)
    employee = session.scalar(
        select(EmployeeRecord).where(
            (EmployeeRecord.employee_no == principal.user_id)
            | (EmployeeRecord.source_employee_key == principal.user_id)
        )
    )
    if employee is None:
        raise HTTPException(status_code=404, detail="employee identity is not mapped to a personnel record")
    return employee


def _serialize(case: EmployeeCaseRecord) -> dict[str, object]:
    return {
        "id": str(case.id),
        "employee_no": case.employee_no,
        "category": case.category,
        "title": case.title,
        "description": case.description,
        "priority": case.priority,
        "status": case.status,
        "resolution": case.resolution,
        "submitted_by": case.submitted_by,
        "submitted_at": case.submitted_at.isoformat(),
        "updated_at": case.updated_at.isoformat(),
        "resolved_by": case.resolved_by,
        "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
    }


@router.post("/self", status_code=201)
def create_self_case(payload: CaseCreate, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _self_employee(session, principal)
        authorize(principal, "self.objection.create", principal.scope)
        now = datetime.utcnow()
        case = EmployeeCaseRecord(
            id=uuid4(),
            employee_no=employee.employee_no,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            priority=payload.priority,
            status="open",
            submitted_by=principal.user_id,
            submitted_at=now,
            updated_at=now,
        )
        session.add(case)
        session.flush()
        append_audit_event(
            event_type="employee.case.created",
            entity_type="employee_case",
            entity_id=str(case.id),
            actor_id=principal.user_id,
            payload={"employee_no": employee.employee_no, "category": case.category, "priority": case.priority},
            reason="employee self-service objection/case submission",
            session=session,
        )
        session.commit()
        return _serialize(case)


@router.get("/self")
def list_self_cases(
    status: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> list[dict[str, object]]:
    with SessionLocal() as session:
        employee = _self_employee(session, principal)
        stmt = select(EmployeeCaseRecord).where(EmployeeCaseRecord.employee_no == employee.employee_no).order_by(EmployeeCaseRecord.submitted_at.desc())
        if status:
            stmt = stmt.where(EmployeeCaseRecord.status == status)
        return [_serialize(case) for case in session.scalars(stmt).all()]


@router.get("/self/{case_id}")
def get_self_case(case_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _self_employee(session, principal)
        case = session.get(EmployeeCaseRecord, case_id)
        if case is None or case.employee_no != employee.employee_no:
            raise HTTPException(status_code=404, detail="case not found")
        return _serialize(case)


@router.get("")
def list_cases(status: str | None = Query(default=None), principal: Principal = Depends(get_current_principal)) -> list[dict[str, object]]:
    with SessionLocal() as session:
        stmt = select(EmployeeCaseRecord).order_by(EmployeeCaseRecord.submitted_at.desc())
        if status:
            stmt = stmt.where(EmployeeCaseRecord.status == status)
        cases = session.scalars(stmt).all()
        result: list[dict[str, object]] = []
        for case in cases:
            employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == case.employee_no))
            if employee is None:
                continue
            authorize_hierarchical(session, principal, "personnel.read", employee.organization_unit_id)
            result.append(_serialize(case))
        return result


@router.post("/{case_id}/status")
def update_case_status(case_id: UUID, payload: CaseStatusUpdate, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        case = session.get(EmployeeCaseRecord, case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="case not found")
        employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == case.employee_no))
        if employee is None:
            raise HTTPException(status_code=409, detail="case employee record is missing")
        authorize_hierarchical(session, principal, "personnel.write", employee.organization_unit_id)
        if case.status in {"resolved", "rejected", "closed"}:
            raise HTTPException(status_code=409, detail="closed case cannot be transitioned")
        if payload.status in {"resolved", "rejected", "closed"} and not payload.resolution:
            raise HTTPException(status_code=422, detail="resolution is required for final case status")
        case.status = payload.status
        case.resolution = payload.resolution
        case.updated_at = datetime.utcnow()
        if payload.status in {"resolved", "rejected", "closed"}:
            case.resolved_by = principal.user_id
            case.resolved_at = case.updated_at
        append_audit_event(
            event_type="employee.case.status_changed",
            entity_type="employee_case",
            entity_id=str(case.id),
            actor_id=principal.user_id,
            payload={"status": case.status, "resolution": case.resolution},
            reason="case management status transition",
            session=session,
        )
        session.commit()
        return _serialize(case)
