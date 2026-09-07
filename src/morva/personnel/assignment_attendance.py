from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.persistence.domain_extensions import AssignmentRecord, AttendanceFactRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord
from morva.security.policy import require_distinct_actors


@dataclass(frozen=True, slots=True)
class AssignmentResult:
    status: str
    assignment_id: UUID


@dataclass(frozen=True, slots=True)
class AttendanceResult:
    status: str
    attendance_id: UUID


def _employee(session: Session, employee_no: str) -> EmployeeRecord:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise ValueError("employee not found")
    return employee


def _validate_assignment_reference(
    session: Session,
    organization_code: str,
    position_code: str,
    starts_on: date,
    ends_on: date | None,
) -> None:
    if ends_on is not None and ends_on < starts_on:
        raise ValueError("assignment end date precedes start date")
    organization = session.scalar(
        select(OrganizationUnitRecord).where(OrganizationUnitRecord.code == organization_code)
    )
    if organization is None:
        raise ValueError("assignment organization not found")
    if not organization.active:
        raise ValueError("assignment organization is inactive")
    position = session.scalar(select(PositionRecord).where(PositionRecord.code == position_code))
    if position is None:
        raise ValueError("assignment position not found")
    if not position.active:
        raise ValueError("assignment position is inactive")


def register_assignment(
    session: Session,
    *,
    employee_no: str,
    organization_code: str,
    position_code: str,
    starts_on: date,
    ends_on: date | None,
    acting: bool,
    source_reference: str | None,
    source_hash: str | None,
    actor_id: str,
) -> AssignmentResult:
    _employee(session, employee_no)
    _validate_assignment_reference(session, organization_code, position_code, starts_on, ends_on)

    existing = session.scalar(
        select(AssignmentRecord).where(
            AssignmentRecord.employee_no == employee_no,
            AssignmentRecord.starts_on == starts_on,
            AssignmentRecord.position_code == position_code,
        )
    )
    if existing is not None:
        if (
            existing.organization_code != organization_code
            or existing.ends_on != ends_on
            or existing.acting != acting
            or existing.source_hash != source_hash
        ):
            raise ValueError("assignment idempotency key already exists with different content")
        return AssignmentResult(status="existing", assignment_id=existing.id)

    overlap = session.scalar(
        select(AssignmentRecord).where(
            AssignmentRecord.employee_no == employee_no,
            AssignmentRecord.starts_on <= (ends_on or date.max),
            or_(AssignmentRecord.ends_on.is_(None), AssignmentRecord.ends_on >= starts_on),
        )
    )
    if overlap is not None:
        raise ValueError("assignment interval overlaps an existing assignment")

    record = AssignmentRecord(
        employee_no=employee_no,
        organization_code=organization_code,
        position_code=position_code,
        starts_on=starts_on,
        ends_on=ends_on,
        acting=acting,
        source_reference=source_reference,
        source_hash=source_hash,
    )
    session.add(record)
    session.flush()
    append_audit_event(
        event_type="personnel.assignment.registered",
        entity_type="employee_assignment",
        entity_id=str(record.id),
        actor_id=actor_id,
        payload={
            "employee_no": employee_no,
            "organization_code": organization_code,
            "position_code": position_code,
            "starts_on": starts_on.isoformat(),
            "ends_on": ends_on.isoformat() if ends_on else None,
            "source_reference": source_reference,
            "source_hash": source_hash,
        },
        reason="register authoritative effective-dated assignment",
        session=session,
    )
    return AssignmentResult(status="created", assignment_id=record.id)


def register_attendance_fact(
    session: Session,
    *,
    employee_no: str,
    period: str,
    source_record_key: str,
    worked_units: Decimal,
    leave_units: Decimal,
    absence_units: Decimal,
    source_hash: str,
    evidence: dict[str, object] | None,
    actor_id: str,
) -> AttendanceResult:
    _employee(session, employee_no)
    if not source_record_key.strip():
        raise ValueError("source_record_key is required")
    if any(value < 0 for value in (worked_units, leave_units, absence_units)):
        raise ValueError("attendance units cannot be negative")
    if len(source_hash) != 64 or any(char not in "0123456789abcdefABCDEF" for char in source_hash):
        raise ValueError("source_hash must be a 64-character SHA-256")
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:].isdigit():
        raise ValueError("period must use YYYY-MM")

    existing = session.scalar(
        select(AttendanceFactRecord).where(
            AttendanceFactRecord.employee_no == employee_no,
            AttendanceFactRecord.period == period,
            AttendanceFactRecord.source_record_key == source_record_key,
        )
    )
    if existing is not None:
        same = (
            existing.worked_units == worked_units
            and existing.leave_units == leave_units
            and existing.absence_units == absence_units
            and existing.source_hash == source_hash
            and (existing.evidence or {}) == (evidence or {})
        )
        if not same:
            raise ValueError("attendance idempotency key already exists with different content")
        return AttendanceResult(status=existing.status, attendance_id=existing.id)

    record = AttendanceFactRecord(
        employee_no=employee_no,
        period=period,
        source_record_key=source_record_key,
        worked_units=worked_units,
        leave_units=leave_units,
        absence_units=absence_units,
        status="received",
        source_hash=source_hash,
        evidence=evidence or {},
    )
    session.add(record)
    session.flush()
    append_audit_event(
        event_type="personnel.attendance.received",
        entity_type="attendance_fact",
        entity_id=str(record.id),
        actor_id=actor_id,
        payload={
            "employee_no": employee_no,
            "period": period,
            "source_record_key": source_record_key,
            "source_hash": source_hash,
        },
        reason="register authoritative attendance fact",
        session=session,
    )
    return AttendanceResult(status=record.status, attendance_id=record.id)


def _attendance(session: Session, attendance_id: UUID | str) -> AttendanceFactRecord:
    record = session.get(AttendanceFactRecord, UUID(str(attendance_id)))
    if record is None:
        raise ValueError("attendance fact not found")
    return record


def review_attendance_fact(session: Session, attendance_id: UUID | str, reviewer_id: str) -> AttendanceFactRecord:
    record = _attendance(session, attendance_id)
    if record.status != "received":
        raise ValueError("attendance fact must be received before review")
    if not record.source_hash or len(record.source_hash) != 64:
        raise ValueError("attendance fact source hash is invalid")
    record.status = "reviewed"
    append_audit_event(
        event_type="personnel.attendance.reviewed",
        entity_type="attendance_fact",
        entity_id=str(record.id),
        actor_id=reviewer_id,
        payload={"employee_no": record.employee_no, "period": record.period, "source_record_key": record.source_record_key},
        reason="review authoritative attendance fact",
        session=session,
    )
    return record


def approve_attendance_fact(session: Session, attendance_id: UUID | str, approver_id: str, reviewer_id: str) -> AttendanceFactRecord:
    record = _attendance(session, attendance_id)
    if record.status != "reviewed":
        raise ValueError("attendance fact must be reviewed before approval")
    require_distinct_actors([reviewer_id, approver_id])
    record.status = "approved"
    append_audit_event(
        event_type="personnel.attendance.approved",
        entity_type="attendance_fact",
        entity_id=str(record.id),
        actor_id=approver_id,
        payload={"employee_no": record.employee_no, "period": record.period, "source_record_key": record.source_record_key},
        reason="approve authoritative attendance fact",
        session=session,
    )
    return record
