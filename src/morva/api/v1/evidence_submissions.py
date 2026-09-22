from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize
from morva.runtime.authoritative_evidence_intake import ALLOWED_SOURCE_TYPES
from morva.runtime.evidence_submission import EvidenceSubmissionError, decide_evidence, submit_evidence

router = APIRouter(prefix="/evidence-submissions", tags=["evidence"])


class EvidenceSubmissionCreate(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=50)
    source_uri: str = Field(min_length=1, max_length=500)
    source_sha256: str = Field(min_length=64, max_length=64)
    issuer: str = Field(min_length=1, max_length=200)
    population_scope: str = Field(min_length=1, max_length=300)
    effective_from: datetime
    effective_to: datetime | None = None
    expires_at: datetime | None = None


class EvidenceDecision(BaseModel):
    decision: str = Field(pattern="^(accepted|rejected)$")
    rejection_reason: str | None = Field(default=None, max_length=4000)


class EvidenceSubmissionResponse(BaseModel):
    evidence_id: str
    source_type: str
    source_uri: str
    source_sha256: str
    issuer: str
    population_scope: str
    submission_scope: str
    submission_scope_id: str
    effective_from: datetime
    effective_to: datetime | None
    expires_at: datetime | None
    status: str
    submitted_by: str
    submitted_at: datetime
    decided_by: str | None
    decided_at: datetime | None
    rejection_reason: str | None
    fingerprint: str

    @classmethod
    def from_record(cls, record: AuthoritativeEvidenceSubmissionRecord) -> "EvidenceSubmissionResponse":
        return cls(
            evidence_id=record.evidence_id,
            source_type=record.source_type,
            source_uri=record.source_uri,
            source_sha256=record.source_sha256,
            issuer=record.issuer,
            population_scope=record.population_scope,
            submission_scope=record.submission_scope,
            submission_scope_id=record.submission_scope_id,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            expires_at=record.expires_at,
            status=record.status,
            submitted_by=record.submitted_by,
            submitted_at=record.submitted_at,
            decided_by=record.decided_by,
            decided_at=record.decided_at,
            rejection_reason=record.rejection_reason,
            fingerprint=record.fingerprint,
        )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EvidenceSubmissionResponse)
def create_submission(
    payload: EvidenceSubmissionCreate,
    principal: Principal = Depends(get_current_principal),
) -> EvidenceSubmissionResponse:
    authorize(principal, "evidence.submit", principal.scope, privileged=True)
    with SessionLocal() as session:
        try:
            record = submit_evidence(
                session,
                evidence_id=payload.evidence_id,
                source_type=payload.source_type,
                source_uri=payload.source_uri,
                source_sha256=payload.source_sha256,
                issuer=payload.issuer,
                population_scope=payload.population_scope,
                submission_scope=principal.scope,
                submission_scope_id=principal.scope_id,
                effective_from=payload.effective_from,
                effective_to=payload.effective_to,
                expires_at=payload.expires_at,
                submitted_by=principal.user_id,
                submitted_at=datetime.now().astimezone(),
            )
        except EvidenceSubmissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type="evidence.submitted",
            entity_type="authoritative_evidence_submission",
            entity_id=record.evidence_id,
            actor_id=principal.user_id,
            payload={"source_type": record.source_type, "fingerprint": record.fingerprint},
            reason="authoritative evidence submitted for controlled approval",
            session=session,
        )
        session.commit()
        return EvidenceSubmissionResponse.from_record(record)


@router.get("", response_model=list[EvidenceSubmissionResponse])
def list_submissions(
    status_filter: str | None = None,
    principal: Principal = Depends(get_current_principal),
) -> list[EvidenceSubmissionResponse]:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        query = select(AuthoritativeEvidenceSubmissionRecord)
        if status_filter:
            query = query.where(AuthoritativeEvidenceSubmissionRecord.status == status_filter)
        records = session.scalars(
            query.order_by(AuthoritativeEvidenceSubmissionRecord.submitted_at.desc())
        ).all()
        return [EvidenceSubmissionResponse.from_record(record) for record in records]


@router.get("/{evidence_id}", response_model=EvidenceSubmissionResponse)
def get_submission(
    evidence_id: str,
    principal: Principal = Depends(get_current_principal),
) -> EvidenceSubmissionResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        record = session.scalar(
            select(AuthoritativeEvidenceSubmissionRecord).where(
                AuthoritativeEvidenceSubmissionRecord.evidence_id == evidence_id.strip()
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="evidence submission not found")
        return EvidenceSubmissionResponse.from_record(record)


@router.post("/{evidence_id}/decision", response_model=EvidenceSubmissionResponse)
def decide_submission(
    evidence_id: str,
    payload: EvidenceDecision,
    principal: Principal = Depends(get_current_principal),
) -> EvidenceSubmissionResponse:
    authorize(principal, "evidence.approve", principal.scope, privileged=True)
    with SessionLocal() as session:
        try:
            record = decide_evidence(
                session,
                evidence_id=evidence_id,
                approver_id=principal.user_id,
                decision=payload.decision,
                decided_at=datetime.now().astimezone(),
                rejection_reason=payload.rejection_reason,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except EvidenceSubmissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type=f"evidence.{payload.decision}",
            entity_type="authoritative_evidence_submission",
            entity_id=record.evidence_id,
            actor_id=principal.user_id,
            payload={
                "fingerprint": record.fingerprint,
                "status": record.status,
                "rejection_reason": record.rejection_reason,
            },
            reason=f"authoritative evidence decision: {payload.decision}",
            session=session,
        )
        session.commit()
        return EvidenceSubmissionResponse.from_record(record)
