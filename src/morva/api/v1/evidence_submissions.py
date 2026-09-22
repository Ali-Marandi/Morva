from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.evidence_lifecycle_records import EvidenceLifecycleRepository
from morva.persistence.evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize
from morva.runtime.evidence_lifecycle import EvidenceLifecycleError, build_lifecycle_assessment
from morva.runtime.evidence_registry_bridge import (
    EvidenceRegistryBridgeError,
    build_registry_projection,
)
from morva.runtime.evidence_submission import (
    EvidenceSubmissionError,
    decide_evidence,
    submit_evidence,
)

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


class EvidenceLifecycleSupersedeCreate(BaseModel):
    successor_evidence_id: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=4000)


class EvidenceLifecycleEventResponse(BaseModel):
    predecessor_evidence_id: str
    successor_evidence_id: str
    linked_by: str
    linked_at: datetime
    reason: str
    fingerprint: str

    @classmethod
    def from_record(cls, record) -> "EvidenceLifecycleEventResponse":
        return cls(
            predecessor_evidence_id=record.predecessor_evidence_id,
            successor_evidence_id=record.successor_evidence_id,
            linked_by=record.linked_by,
            linked_at=record.linked_at,
            reason=record.reason,
            fingerprint=record.fingerprint,
        )


class EvidenceLifecycleResponse(BaseModel):
    events: list[EvidenceLifecycleEventResponse]
    assessment: dict[str, object]


class EvidenceRegistryResponse(BaseModel):
    registry_version: int
    items: list[dict[str, object]]
    registered_at: datetime
    fingerprint: str
    projection: dict[str, object]


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
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="evidence_id already submitted") from exc
        return EvidenceSubmissionResponse.from_record(record)


@router.get("", response_model=list[EvidenceSubmissionResponse])
def list_submissions(
    status_filter: str | None = None,
    principal: Principal = Depends(get_current_principal),
) -> list[EvidenceSubmissionResponse]:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        query = select(AuthoritativeEvidenceSubmissionRecord)
        if principal.scope is not Scope.MINISTRY:
            query = query.where(
                AuthoritativeEvidenceSubmissionRecord.submission_scope == principal.scope.value,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id == principal.scope_id,
            )
        if status_filter:
            query = query.where(AuthoritativeEvidenceSubmissionRecord.status == status_filter)
        records = session.scalars(
            query.order_by(AuthoritativeEvidenceSubmissionRecord.submitted_at.desc())
        ).all()
        return [EvidenceSubmissionResponse.from_record(record) for record in records]


@router.get("/registry", response_model=EvidenceRegistryResponse)
def get_registry(
    principal: Principal = Depends(get_current_principal),
) -> EvidenceRegistryResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        query = select(AuthoritativeEvidenceSubmissionRecord).where(
            AuthoritativeEvidenceSubmissionRecord.status == "accepted"
        )
        if principal.scope is not Scope.MINISTRY:
            query = query.where(
                AuthoritativeEvidenceSubmissionRecord.submission_scope == principal.scope.value,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id == principal.scope_id,
            )
        records = session.scalars(
            query.order_by(AuthoritativeEvidenceSubmissionRecord.evidence_id.asc())
        ).all()
        try:
            registry, projection = build_registry_projection(
                records,
                projected_at=datetime.now().astimezone(),
            )
        except EvidenceRegistryBridgeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        payload = registry.to_payload()
        return EvidenceRegistryResponse(
            registry_version=registry.registry_version,
            items=list(payload["items"]),
            registered_at=registry.registered_at,
            fingerprint=registry.fingerprint,
            projection=projection.to_payload(),
        )


@router.post("/{evidence_id}/supersede", response_model=EvidenceLifecycleEventResponse)
def supersede_evidence(
    evidence_id: str,
    payload: EvidenceLifecycleSupersedeCreate,
    principal: Principal = Depends(get_current_principal),
) -> EvidenceLifecycleEventResponse:
    authorize(
        principal,
        "evidence.lifecycle.write",
        principal.scope,
        privileged=True,
    )
    with SessionLocal() as session:
        repository = EvidenceLifecycleRepository(session)
        try:
            record = repository.create_link(
                predecessor_evidence_id=evidence_id,
                successor_evidence_id=payload.successor_evidence_id,
                linked_by=principal.user_id,
                linked_at=datetime.now().astimezone(),
                reason=payload.reason,
                principal_scope=principal.scope,
                principal_scope_id=principal.scope_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except EvidenceLifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="lifecycle relationship already exists") from exc

        append_audit_event(
            event_type="evidence.lifecycle.superseded",
            entity_type="authoritative_evidence_lifecycle_event",
            entity_id=record.fingerprint,
            actor_id=principal.user_id,
            payload={
                "predecessor_evidence_id": record.predecessor_evidence_id,
                "successor_evidence_id": record.successor_evidence_id,
                "fingerprint": record.fingerprint,
            },
            reason=record.reason,
            session=session,
        )
        session.commit()
        return EvidenceLifecycleEventResponse.from_record(record)


@router.get("/lifecycle", response_model=EvidenceLifecycleResponse)
def list_evidence_lifecycle(
    principal: Principal = Depends(get_current_principal),
) -> EvidenceLifecycleResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        accepted_query = select(AuthoritativeEvidenceSubmissionRecord).where(
            AuthoritativeEvidenceSubmissionRecord.status == "accepted"
        )
        if principal.scope is not Scope.MINISTRY:
            accepted_query = accepted_query.where(
                AuthoritativeEvidenceSubmissionRecord.submission_scope == principal.scope.value,
                AuthoritativeEvidenceSubmissionRecord.submission_scope_id == principal.scope_id,
            )
        accepted_records = session.scalars(
            accepted_query.order_by(AuthoritativeEvidenceSubmissionRecord.evidence_id.asc())
        ).all()
        try:
            registry, _ = build_registry_projection(
                accepted_records,
                projected_at=datetime.now().astimezone(),
            )
        except EvidenceRegistryBridgeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        lifecycle_repository = EvidenceLifecycleRepository(session)
        lifecycle_records = (
            lifecycle_repository.list_all()
            if principal.scope is Scope.MINISTRY
            else lifecycle_repository.list_for_scope(
                scope=principal.scope,
                scope_id=principal.scope_id,
            )
        )
        checked_at = datetime.now().astimezone()
        try:
            assessment = build_lifecycle_assessment(
                registry,
                repository="Ali-Marandi/Morva",
                checked_at=checked_at,
                links=tuple(record.to_link() for record in lifecycle_records),
            )
        except EvidenceLifecycleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return EvidenceLifecycleResponse(
            events=[EvidenceLifecycleEventResponse.from_record(record) for record in lifecycle_records],
            assessment=assessment.to_payload(),
        )


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
        if (
            principal.scope is not Scope.MINISTRY
            and (
                record.submission_scope != principal.scope.value
                or record.submission_scope_id != principal.scope_id
            )
        ):
            raise HTTPException(status_code=403, detail="organization scope violation")
        return EvidenceSubmissionResponse.from_record(record)


@router.post("/{evidence_id}/decision", response_model=EvidenceSubmissionResponse)
def decide_submission(
    evidence_id: str,
    payload: EvidenceDecision,
    principal: Principal = Depends(get_current_principal),
) -> EvidenceSubmissionResponse:
    authorize(principal, "evidence.approve", principal.scope, privileged=True)
    with SessionLocal() as session:
        existing = session.scalar(
            select(AuthoritativeEvidenceSubmissionRecord).where(
                AuthoritativeEvidenceSubmissionRecord.evidence_id == evidence_id.strip()
            )
        )
        if existing is None:
            raise HTTPException(status_code=404, detail="evidence submission not found")
        if (
            principal.scope is not Scope.MINISTRY
            and (
                existing.submission_scope != principal.scope.value
                or existing.submission_scope_id != principal.scope_id
            )
        ):
            raise HTTPException(status_code=403, detail="organization scope violation")
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
