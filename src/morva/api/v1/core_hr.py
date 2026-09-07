from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select

from morva.audit.persistence import append_audit_event
from morva.persistence.core_hr_records import DependentRecord, EducationRecord, ExperienceRecord
from morva.persistence.database import SessionLocal
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import EmploymentRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord
from morva.personnel.core_hr_snapshot import persist_core_hr_snapshot
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical

router = APIRouter(prefix="/hr", tags=["core-hr"])


def _employee_or_404(session, employee_no: str) -> EmployeeRecord:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return employee


def _authorize_employee(session, principal: Principal, employee: EmployeeRecord, permission: str = "personnel.read") -> None:
    authorize_hierarchical(session, principal, permission, employee.organization_unit_id)


def _row(record, *, exclude: set[str] | None = None) -> dict[str, object]:
    excluded = exclude or set()
    return {
        key: value
        for key, value in record.__dict__.items()
        if not key.startswith("_") and key not in excluded
    }


@router.get("/employees/{employee_no}")
def get_employee(employee_no: str, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        return {
            "employee_no": employee.employee_no,
            "national_id": employee.national_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "employment_type": employee.employment_type,
            "status": employee.status,
            "organization_unit_id": employee.organization_unit_id,
            "position_id": employee.position_id,
            "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
        }


@router.get("/employees/{employee_no}/employment-history")
def get_employment_history(employee_no: str, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        records = session.scalars(
            select(EmploymentRecord)
            .where(EmploymentRecord.employee_no == employee_no)
            .order_by(EmploymentRecord.starts_on.desc())
        ).all()
        return {"employee_no": employee_no, "items": [_row(item) for item in records]}


@router.get("/employees/{employee_no}/assignment-history")
def get_assignment_history(employee_no: str, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        records = session.scalars(
            select(AssignmentRecord)
            .where(AssignmentRecord.employee_no == employee_no)
            .order_by(AssignmentRecord.starts_on.desc())
        ).all()
        return {"employee_no": employee_no, "items": [_row(item) for item in records]}


@router.get("/employees/{employee_no}/education")
def get_education(employee_no: str, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        records = session.scalars(
            select(EducationRecord)
            .where(EducationRecord.employee_no == employee_no)
            .order_by(EducationRecord.completed_on.desc().nullslast(), EducationRecord.institution)
        ).all()
        return {"employee_no": employee_no, "items": [_row(item) for item in records]}


@router.get("/employees/{employee_no}/experience")
def get_experience(
    employee_no: str,
    principal: Principal = Depends(get_current_principal),
    effective_on: date | None = Query(default=None),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        statement = select(ExperienceRecord).where(ExperienceRecord.employee_no == employee_no)
        if effective_on is not None:
            statement = statement.where(
                ExperienceRecord.starts_on <= effective_on,
                or_(ExperienceRecord.ends_on.is_(None), ExperienceRecord.ends_on >= effective_on),
            )
        records = session.scalars(statement.order_by(ExperienceRecord.starts_on.desc())).all()
        return {"employee_no": employee_no, "effective_on": effective_on.isoformat() if effective_on else None, "items": [_row(item) for item in records]}


@router.get("/employees/{employee_no}/dependents")
def get_dependents(
    employee_no: str,
    principal: Principal = Depends(get_current_principal),
    effective_on: date | None = Query(default=None),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        statement = select(DependentRecord).where(DependentRecord.employee_no == employee_no)
        if effective_on is not None:
            statement = statement.where(
                or_(DependentRecord.valid_from.is_(None), DependentRecord.valid_from <= effective_on),
                or_(DependentRecord.valid_to.is_(None), DependentRecord.valid_to >= effective_on),
            )
        records = session.scalars(statement.order_by(DependentRecord.name)).all()
        return {"employee_no": employee_no, "effective_on": effective_on.isoformat() if effective_on else None, "items": [_row(item) for item in records]}


@router.get("/employees/{employee_no}/profile")
def get_employee_profile(
    employee_no: str,
    principal: Principal = Depends(get_current_principal),
    effective_on: date | None = Query(default=None),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        employment_statement = (
            select(EmploymentRecord)
            .where(EmploymentRecord.employee_no == employee_no)
            .order_by(EmploymentRecord.starts_on.desc())
        )
        assignment_statement = (
            select(AssignmentRecord)
            .where(AssignmentRecord.employee_no == employee_no)
            .order_by(AssignmentRecord.starts_on.desc())
        )
        education_statement = select(EducationRecord).where(EducationRecord.employee_no == employee_no).order_by(EducationRecord.completed_on.desc().nullslast())
        experience_statement = select(ExperienceRecord).where(ExperienceRecord.employee_no == employee_no).order_by(ExperienceRecord.starts_on.desc())
        dependent_statement = select(DependentRecord).where(DependentRecord.employee_no == employee_no).order_by(DependentRecord.name)
        if effective_on is not None:
            employment_statement = employment_statement.where(
                EmploymentRecord.starts_on <= effective_on,
                or_(EmploymentRecord.ends_on.is_(None), EmploymentRecord.ends_on >= effective_on),
            )
            assignment_statement = assignment_statement.where(
                AssignmentRecord.starts_on <= effective_on,
                or_(AssignmentRecord.ends_on.is_(None), AssignmentRecord.ends_on >= effective_on),
            )
            experience_statement = experience_statement.where(
                ExperienceRecord.starts_on <= effective_on,
                or_(ExperienceRecord.ends_on.is_(None), ExperienceRecord.ends_on >= effective_on),
            )
            dependent_statement = dependent_statement.where(
                or_(DependentRecord.valid_from.is_(None), DependentRecord.valid_from <= effective_on),
                or_(DependentRecord.valid_to.is_(None), DependentRecord.valid_to >= effective_on),
            )
        employment = session.scalar(employment_statement)
        assignment = session.scalar(assignment_statement)
        education = session.scalars(education_statement).all()
        experience = session.scalars(experience_statement).all()
        dependents = session.scalars(dependent_statement).all()
        return {
            "employee": {
                "employee_no": employee.employee_no,
                "national_id": employee.national_id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "status": employee.status,
                "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
            },
            "effective_on": effective_on.isoformat() if effective_on else None,
            "effective_employment": _row(employment) if employment else None,
            "effective_assignment": _row(assignment) if assignment else None,
            "education": [_row(item) for item in education],
            "experience": [_row(item) for item in experience],
            "dependents": [_row(item) for item in dependents],
        }


@router.post("/employees/{employee_no}/snapshots", status_code=201)
def create_employee_snapshot(
    employee_no: str,
    effective_on: date,
    effective_period: str = Query(min_length=7, max_length=7, pattern=r"^\\d{4}-\\d{2}$"),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    if effective_period != effective_on.strftime("%Y-%m"):
        raise HTTPException(status_code=422, detail="effective_period must match effective_on year and month")
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee, "personnel.write")
        try:
            snapshot = persist_core_hr_snapshot(session, employee_no, effective_period, effective_on)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type="personnel.snapshot.created_or_verified",
            entity_type="personnel_snapshot",
            entity_id=str(snapshot.id),
            actor_id=principal.user_id,
            payload={"employee_no": employee_no, "effective_period": effective_period, "snapshot_hash": snapshot.snapshot_hash},
            reason="create or verify immutable Core HR effective snapshot",
            session=session,
        )
        session.commit()
        return {
            "id": str(snapshot.id),
            "employee_no": snapshot.employee_no,
            "effective_period": snapshot.effective_period,
            "effective_date": snapshot.effective_date.isoformat() if snapshot.effective_date else None,
            "organization_unit_id": snapshot.organization_unit_id,
            "position_id": snapshot.position_id,
            "employment_type": snapshot.employment_type,
            "employment_status": snapshot.employment_status,
            "snapshot_hash": snapshot.snapshot_hash,
        }


@router.get("/employees/{employee_no}/snapshots/{effective_period}")
def get_employee_snapshot(
    employee_no: str,
    effective_period: str,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        employee = _employee_or_404(session, employee_no)
        _authorize_employee(session, principal, employee)
        snapshot = session.scalar(
            select(PersonnelSnapshotRecord).where(
                PersonnelSnapshotRecord.employee_no == employee_no,
                PersonnelSnapshotRecord.effective_period == effective_period,
            )
        )
        if snapshot is None:
            raise HTTPException(status_code=404, detail="personnel snapshot not found")
        return {
            "id": str(snapshot.id),
            "employee_no": snapshot.employee_no,
            "effective_period": snapshot.effective_period,
            "effective_date": snapshot.effective_date.isoformat() if snapshot.effective_date else None,
            "organization_unit_id": snapshot.organization_unit_id,
            "position_id": snapshot.position_id,
            "employment_type": snapshot.employment_type,
            "employment_status": snapshot.employment_status,
            "source_hash": snapshot.source_hash,
            "snapshot_hash": snapshot.snapshot_hash,
            "order_numbers": snapshot.order_numbers,
            "components": snapshot.components,
        }
