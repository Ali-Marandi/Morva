from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.hr.teacher_rank_evidence import check_teacher_rank_evidence
from morva.persistence.domain_extensions import TeacherRankCaseRecord
from morva.persistence.models import EmployeeRecord
from morva.security.policy import require_distinct_actors

_ALLOWED_TRANSITIONS = {"draft": {"assessed"}, "assessed": {"committee_approved"}, "committee_approved": {"decided"}, "decided": {"appeal_opened"}, "appeal_opened": {"appeal_resolved"}, "appeal_resolved": set()}

@dataclass(frozen=True, slots=True)
class RankCaseResult:
    case_id: UUID
    status: str

def _case(session: Session, case_id: UUID) -> TeacherRankCaseRecord:
    record = session.get(TeacherRankCaseRecord, case_id)
    if record is None:
        raise ValueError("teacher rank case not found")
    return record

def _employee(session: Session, employee_no: str) -> EmployeeRecord:
    employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
    if employee is None:
        raise ValueError("employee not found")
    return employee

def _transition(session: Session, record: TeacherRankCaseRecord, *, target: str, actor_id: str, reason: str, reviewer_id: str | None = None) -> RankCaseResult:
    if target not in _ALLOWED_TRANSITIONS.get(record.status, set()):
        raise ValueError(f"invalid teacher rank transition: {record.status} -> {target}")
    if reviewer_id is not None:
        require_distinct_actors(actor_id, reviewer_id)
    record.status = target
    append_audit_event(event_type=f"hr.teacher_rank.{target}", entity_type="teacher_rank_case", entity_id=str(record.id), actor_id=actor_id, payload={"employee_no": record.employee_no, "proposed_rank": record.proposed_rank}, reason=reason, session=session)
    return RankCaseResult(case_id=record.id, status=record.status)

def create_rank_case(session: Session, *, employee_no: str, proposed_rank: str, effect_period: str, actor_id: str, current_rank: str | None = None, assessment_payload: dict | None = None) -> RankCaseResult:
    _employee(session, employee_no)
    if not proposed_rank.strip():
        raise ValueError("proposed_rank is required")
    if len(effect_period) != 7 or effect_period[4] != "-":
        raise ValueError("effect_period must use YYYY-MM")
    duplicate = session.scalar(select(TeacherRankCaseRecord).where(TeacherRankCaseRecord.employee_no == employee_no, TeacherRankCaseRecord.effect_period == effect_period, TeacherRankCaseRecord.proposed_rank == proposed_rank))
    if duplicate is not None:
        return RankCaseResult(case_id=duplicate.id, status=duplicate.status)
    record = TeacherRankCaseRecord(employee_no=employee_no, current_rank=current_rank, proposed_rank=proposed_rank, status="draft", effect_period=effect_period, assessment_payload=assessment_payload or {}, committee_payload={}, appeal_payload={})
    session.add(record)
    session.flush()
    append_audit_event(event_type="hr.teacher_rank.created", entity_type="teacher_rank_case", entity_id=str(record.id), actor_id=actor_id, payload={"employee_no": employee_no, "effect_period": effect_period, "proposed_rank": proposed_rank}, reason="register teacher rank case", session=session)
    return RankCaseResult(case_id=record.id, status=record.status)

def submit_assessment(session: Session, case_id: UUID, actor_id: str, assessment: dict) -> RankCaseResult:
    if not assessment:
        raise ValueError("assessment evidence is required")
    record = _case(session, case_id)
    record.assessment_payload = assessment
    return _transition(session, record, target="assessed", actor_id=actor_id, reason="submit rank assessment evidence")

def approve_committee(session: Session, case_id: UUID, actor_id: str, committee: dict, reviewer_id: str) -> RankCaseResult:
    if not committee:
        raise ValueError("committee evidence is required")
    record = _case(session, case_id)
    record.committee_payload = committee
    return _transition(session, record, target="committee_approved", actor_id=actor_id, reviewer_id=reviewer_id, reason="approve rank committee evidence")

def decide_case(session: Session, case_id: UUID, actor_id: str, decision_reference: str) -> RankCaseResult:
    if not decision_reference.strip():
        raise ValueError("decision_reference is required")
    record = _case(session, case_id)
    evidence_gate = check_teacher_rank_evidence(session, record)
    if not evidence_gate.ready:
        raise ValueError("teacher rank decision blocked by authoritative evidence gate: " + "; ".join(evidence_gate.blockers))
    record.decision_reference = decision_reference
    return _transition(session, record, target="decided", actor_id=actor_id, reason="record authoritative rank decision")

def open_appeal(session: Session, case_id: UUID, actor_id: str, appeal: dict) -> RankCaseResult:
    if not appeal:
        raise ValueError("appeal payload is required")
    record = _case(session, case_id)
    record.appeal_payload = {**record.appeal_payload, "opened": appeal}
    return _transition(session, record, target="appeal_opened", actor_id=actor_id, reason="open teacher rank appeal")

def resolve_appeal(session: Session, case_id: UUID, actor_id: str, resolution: dict, reviewer_id: str) -> RankCaseResult:
    if not resolution:
        raise ValueError("appeal resolution is required")
    record = _case(session, case_id)
    record.appeal_payload = {**record.appeal_payload, "resolution": resolution}
    return _transition(session, record, target="appeal_resolved", actor_id=actor_id, reviewer_id=reviewer_id, reason="resolve teacher rank appeal")
