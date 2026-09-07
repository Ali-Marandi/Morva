from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.hr.teacher_rank import approve_committee, create_rank_case, decide_case, open_appeal, resolve_appeal, submit_assessment
from morva.persistence.database import SessionLocal
from morva.persistence.domain_extensions import TeacherRankCaseRecord
from morva.persistence.models import EmployeeRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical

router = APIRouter(prefix="/hr", tags=["teacher-rank"])


class RankCaseInput(BaseModel):
    proposed_rank: str = Field(min_length=1, max_length=50)
    current_rank: str | None = Field(default=None, max_length=50)
    effect_period: str = Field(pattern=r"^\d{4}-\d{2}$")
    assessment: dict = Field(default_factory=dict)


class EvidenceInput(BaseModel):
    evidence: dict


class CommitteeInput(BaseModel):
    evidence: dict
    reviewer_id: str = Field(min_length=1)


class DecisionInput(BaseModel):
    decision_reference: str = Field(min_length=1, max_length=150)


class AppealInput(BaseModel):
    appeal: dict


class AppealResolutionInput(BaseModel):
    resolution: dict
    reviewer_id: str = Field(min_length=1)


def _employee(session, employee_no: str) -> EmployeeRecord:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return employee


def _case_payload(record: TeacherRankCaseRecord) -> dict[str, object]:
    return {
        "id": str(record.id),
        "employee_no": record.employee_no,
        "current_rank": record.current_rank,
        "proposed_rank": record.proposed_rank,
        "status": record.status,
        "effect_period": record.effect_period,
        "assessment": record.assessment_payload,
        "committee": record.committee_payload,
        "appeal": record.appeal_payload,
        "decision_reference": record.decision_reference,
    }


def _get_case(session, case_id: UUID) -> TeacherRankCaseRecord:
    record = session.get(TeacherRankCaseRecord, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="teacher rank case not found")
    return record


def _authorize(session, principal: Principal, employee: EmployeeRecord, permission: str) -> None:
    authorize_hierarchical(session, principal, permission, employee.organization_unit_id)


@router.post("/employees/{employee_no}/teacher-rank-cases", status_code=201)
def create_case(employee_no: str, payload: RankCaseInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.write")
        try:
            result = create_rank_case(session, employee_no=employee_no, proposed_rank=payload.proposed_rank, current_rank=payload.current_rank, effect_period=payload.effect_period, assessment_payload=payload.assessment, actor_id=principal.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}


@router.get("/employees/{employee_no}/teacher-rank-cases")
def list_cases(employee_no: str, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee(session, employee_no)
        _authorize(session, principal, employee, "personnel.read")
        records = session.scalars(select(TeacherRankCaseRecord).where(TeacherRankCaseRecord.employee_no == employee_no).order_by(TeacherRankCaseRecord.effect_period.desc(), TeacherRankCaseRecord.created_at.desc())).all()
        return {"employee_no": employee_no, "items": [_case_payload(record) for record in records]}


@router.get("/teacher-rank-cases/{case_id}")
def get_case(case_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.read")
        return _case_payload(record)


@router.post("/teacher-rank-cases/{case_id}/assessment")
def assess_case(case_id: UUID, payload: EvidenceInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.review")
        try:
            result = submit_assessment(session, case_id, principal.user_id, payload.evidence)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}


@router.post("/teacher-rank-cases/{case_id}/committee-approval")
def committee_approval(case_id: UUID, payload: CommitteeInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.approve")
        try:
            result = approve_committee(session, case_id, principal.user_id, payload.evidence, payload.reviewer_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}


@router.post("/teacher-rank-cases/{case_id}/decision")
def decide(case_id: UUID, payload: DecisionInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.approve")
        try:
            result = decide_case(session, case_id, principal.user_id, payload.decision_reference)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}


@router.post("/teacher-rank-cases/{case_id}/appeal")
def appeal(case_id: UUID, payload: AppealInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.write")
        try:
            result = open_appeal(session, case_id, principal.user_id, payload.appeal)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}


@router.post("/teacher-rank-cases/{case_id}/appeal-resolution")
def appeal_resolution(case_id: UUID, payload: AppealResolutionInput, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        record = _get_case(session, case_id)
        employee = _employee(session, record.employee_no)
        _authorize(session, principal, employee, "personnel.approve")
        try:
            result = resolve_appeal(session, case_id, principal.user_id, payload.resolution, payload.reviewer_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        session.commit()
        return {"status": result.status, "case_id": str(result.case_id)}
