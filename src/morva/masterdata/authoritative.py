from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.hr.teacher_rank_decision_integrity import verify_persisted_teacher_rank_decision_provenance
from morva.masterdata.validation import MasterDataFinding, validate_master_data
from morva.persistence.domain_extensions import AssignmentRecord, AttendanceFactRecord, TeacherRankCaseRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord


_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_RANK_CASE_STATUSES = {"draft", "assessed", "committee_approved", "decided", "appeal_opened", "appeal_resolved"}
_PERSISTED_DECISION_STATUSES = {"decided", "appeal_opened", "appeal_resolved"}
_ATTENDANCE_STATUSES = {"received", "reviewed", "approved"}


@dataclass(frozen=True, slots=True)
class AuthoritativeMasterDataResult:
    blocking: bool
    findings: tuple[MasterDataFinding, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "blocking": self.blocking,
            "findings": [asdict(finding) for finding in self.findings],
        }


def _add_finding(
    findings: list[MasterDataFinding],
    *,
    code: str,
    entity_type: str,
    entity_id: str,
    message: str,
) -> None:
    findings.append(
        MasterDataFinding(
            code=code,
            severity="error",
            entity_type=entity_type,
            entity_id=entity_id,
            message=message,
        )
    )


def validate_authoritative_master_data(session: Session) -> AuthoritativeMasterDataResult:
    base = validate_master_data(session)
    findings = list(base.findings)
    additional_blocking = False

    employees = session.scalars(select(EmployeeRecord).order_by(EmployeeRecord.employee_no)).all()
    employees_by_no = {row.employee_no: row for row in employees}

    positions = session.scalars(select(PositionRecord).order_by(PositionRecord.code)).all()
    for row in positions:
        if row.effective_to is not None and row.effective_from is not None and row.effective_to < row.effective_from:
            _add_finding(
                findings,
                code="POSITION_INVALID_RANGE",
                entity_type="position",
                entity_id=row.code,
                message="position effective_to precedes effective_from",
            )
            additional_blocking = True

    assignments = session.scalars(
        select(AssignmentRecord).order_by(
            AssignmentRecord.employee_no,
            AssignmentRecord.starts_on,
            AssignmentRecord.id,
        )
    ).all()
    by_employee: dict[str, list[AssignmentRecord]] = defaultdict(list)
    for row in assignments:
        by_employee[row.employee_no].append(row)

    for employee_no, rows in by_employee.items():
        previous: AssignmentRecord | None = None
        for current in rows:
            if previous is not None and (previous.ends_on is None or current.starts_on <= previous.ends_on):
                _add_finding(
                    findings,
                    code="ASSIGNMENT_OVERLAP",
                    entity_type="assignment",
                    entity_id=str(current.id),
                    message=f"assignment interval overlaps previous assignment for employee {employee_no}",
                )
                additional_blocking = True
            previous = current

    for employee in employees:
        if employee.status != "active":
            continue
        current_assignments = by_employee.get(employee.employee_no, [])
        if not any(row.ends_on is None for row in current_assignments):
            _add_finding(
                findings,
                code="ACTIVE_EMPLOYEE_NO_CURRENT_ASSIGNMENT",
                entity_type="employee",
                entity_id=employee.employee_no,
                message="active employee has no open-ended personnel assignment",
            )
            additional_blocking = True

    attendance = session.scalars(
        select(AttendanceFactRecord).order_by(
            AttendanceFactRecord.employee_no,
            AttendanceFactRecord.period,
            AttendanceFactRecord.id,
        )
    ).all()
    for row in attendance:
        entity_id = str(row.id)
        if row.employee_no not in employees_by_no:
            _add_finding(
                findings,
                code="ATTENDANCE_EMPLOYEE_MISSING",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="attendance employee reference does not resolve",
            )
            additional_blocking = True
        if not _PERIOD_RE.fullmatch(row.period):
            _add_finding(
                findings,
                code="ATTENDANCE_INVALID_PERIOD",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="attendance period must use YYYY-MM",
            )
            additional_blocking = True
        if row.status not in _ATTENDANCE_STATUSES:
            _add_finding(
                findings,
                code="ATTENDANCE_INVALID_STATUS",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="attendance status is not an allowed workflow state",
            )
            additional_blocking = True
        if any(value < 0 for value in (row.worked_units, row.leave_units, row.absence_units)):
            _add_finding(
                findings,
                code="ATTENDANCE_NEGATIVE_UNITS",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="attendance units cannot be negative",
            )
            additional_blocking = True
        if not isinstance(row.source_hash, str) or not _SHA256_RE.fullmatch(row.source_hash):
            _add_finding(
                findings,
                code="ATTENDANCE_SOURCE_HASH_INVALID",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="attendance source_hash must be a 64-character SHA-256",
            )
            additional_blocking = True
        if row.status == "approved" and not row.evidence:
            _add_finding(
                findings,
                code="ATTENDANCE_APPROVAL_EVIDENCE_MISSING",
                entity_type="attendance_fact",
                entity_id=entity_id,
                message="approved attendance requires persisted approval evidence",
            )
            additional_blocking = True

    rank_cases = session.scalars(
        select(TeacherRankCaseRecord).order_by(
            TeacherRankCaseRecord.employee_no,
            TeacherRankCaseRecord.effect_period,
            TeacherRankCaseRecord.id,
        )
    ).all()
    for row in rank_cases:
        entity_id = str(row.id)
        if row.employee_no not in employees_by_no:
            _add_finding(
                findings,
                code="RANK_CASE_EMPLOYEE_MISSING",
                entity_type="teacher_rank_case",
                entity_id=entity_id,
                message="teacher rank case employee reference does not resolve",
            )
            additional_blocking = True
        if not _PERIOD_RE.fullmatch(row.effect_period):
            _add_finding(
                findings,
                code="RANK_CASE_INVALID_PERIOD",
                entity_type="teacher_rank_case",
                entity_id=entity_id,
                message="teacher rank effect_period must use YYYY-MM",
            )
            additional_blocking = True
        if row.status not in _RANK_CASE_STATUSES:
            _add_finding(
                findings,
                code="RANK_CASE_INVALID_STATUS",
                entity_type="teacher_rank_case",
                entity_id=entity_id,
                message="teacher rank case status is not an allowed workflow state",
            )
            additional_blocking = True
        if row.status in _PERSISTED_DECISION_STATUSES:
            provenance_ok = bool(
                row.decision_reference
                and verify_persisted_teacher_rank_decision_provenance(
                    case_id=entity_id,
                    employee_no=row.employee_no,
                    proposed_rank=row.proposed_rank,
                    effect_period=row.effect_period,
                    decision_reference=row.decision_reference,
                    committee_payload=row.committee_payload,
                )
            )
            if not provenance_ok:
                _add_finding(
                    findings,
                    code="RANK_DECISION_PROVENANCE_INVALID",
                    entity_type="teacher_rank_case",
                    entity_id=entity_id,
                    message="persisted teacher rank decision provenance is missing or invalid",
                )
                additional_blocking = True

    return AuthoritativeMasterDataResult(
        blocking=base.blocking or additional_blocking,
        findings=tuple(findings),
    )
