from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from morva.persistence.core_hr_records import DependentRecord, EducationRecord, ExperienceRecord
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import EmploymentRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord


def _canonical_value(value):
    if isinstance(value, (date, UUID)):
        return str(value)
    return value


def _record_payload(record) -> dict[str, object]:
    return {
        key: _canonical_value(value)
        for key, value in record.__dict__.items()
        if not key.startswith("_")
    }


def build_core_hr_snapshot(session: Session, employee_no: str, effective_on: date) -> dict[str, object]:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise ValueError("employee not found")

    employment = session.scalar(
        select(EmploymentRecord)
        .where(
            EmploymentRecord.employee_no == employee_no,
            EmploymentRecord.starts_on <= effective_on,
            or_(EmploymentRecord.ends_on.is_(None), EmploymentRecord.ends_on >= effective_on),
        )
        .order_by(EmploymentRecord.starts_on.desc())
    )
    assignment = session.scalar(
        select(AssignmentRecord)
        .where(
            AssignmentRecord.employee_no == employee_no,
            AssignmentRecord.starts_on <= effective_on,
            or_(AssignmentRecord.ends_on.is_(None), AssignmentRecord.ends_on >= effective_on),
        )
        .order_by(AssignmentRecord.starts_on.desc())
    )
    education = session.scalars(
        select(EducationRecord)
        .where(EducationRecord.employee_no == employee_no)
        .order_by(EducationRecord.completed_on.desc().nullslast(), EducationRecord.institution)
    ).all()
    experience = session.scalars(
        select(ExperienceRecord)
        .where(
            ExperienceRecord.employee_no == employee_no,
            ExperienceRecord.starts_on <= effective_on,
            or_(ExperienceRecord.ends_on.is_(None), ExperienceRecord.ends_on >= effective_on),
        )
        .order_by(ExperienceRecord.starts_on.desc(), ExperienceRecord.organization_name)
    ).all()
    dependents = session.scalars(
        select(DependentRecord)
        .where(
            DependentRecord.employee_no == employee_no,
            or_(DependentRecord.valid_from.is_(None), DependentRecord.valid_from <= effective_on),
            or_(DependentRecord.valid_to.is_(None), DependentRecord.valid_to >= effective_on),
        )
        .order_by(DependentRecord.name, DependentRecord.relationship)
    ).all()

    effective_position = employment.position_id if employment else employee.position_id
    effective_org = employment.organization_unit_id if employment else employee.organization_unit_id
    effective_type = employment.employment_type if employment else employee.employment_type

    return {
        "employee": {
            "employee_no": employee.employee_no,
            "national_id": employee.national_id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "status": employee.status,
            "hire_date": _canonical_value(employee.hire_date),
        },
        "effective_on": effective_on.isoformat(),
        "employment": _record_payload(employment) if employment else None,
        "assignment": _record_payload(assignment) if assignment else None,
        "education": [_record_payload(item) for item in education],
        "experience": [_record_payload(item) for item in experience],
        "dependents": [_record_payload(item) for item in dependents],
        "resolved": {
            "organization_unit_id": effective_org,
            "position_id": effective_position,
            "employment_type": effective_type,
        },
    }


def persist_core_hr_snapshot(session: Session, employee_no: str, effective_period: str, effective_on: date) -> PersonnelSnapshotRecord:
    payload = build_core_hr_snapshot(session, employee_no, effective_on)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    snapshot_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    source_hash = hashlib.sha256(
        json.dumps(payload["employee"], ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    existing = session.scalar(
        select(PersonnelSnapshotRecord).where(
            PersonnelSnapshotRecord.employee_no == employee_no,
            PersonnelSnapshotRecord.effective_period == effective_period,
        )
    )
    if existing is not None:
        if existing.effective_date != effective_on or existing.snapshot_hash != snapshot_hash:
            raise ValueError("immutable snapshot already exists with different effective content")
        return existing

    resolved = payload["resolved"]
    snapshot = PersonnelSnapshotRecord(
        employee_no=employee_no,
        effective_period=effective_period,
        effective_date=effective_on,
        organization_unit_id=str(resolved["organization_unit_id"]),
        position_id=str(resolved["position_id"]),
        employment_type=str(resolved["employment_type"]),
        employment_status=str(payload["employee"]["status"]),
        source_import_batch_id=None,
        source_hash=source_hash,
        snapshot_hash=snapshot_hash,
        order_numbers=[],
        components={"core_hr": payload},
    )
    session.add(snapshot)
    session.flush()
    return snapshot
