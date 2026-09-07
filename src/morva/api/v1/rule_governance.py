from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import LegalSourceRecord, RuleEvidenceRecord
from morva.persistence.models import RulePackRecord
from morva.rules.governance import (
    approve_evidence,
    approve_legal_source,
    approve_rule_pack,
    pack_readiness,
    review_evidence,
    review_legal_source,
    review_rule_pack,
    validate_evidence_payload,
    validate_legal_source_payload,
)
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize

router = APIRouter(prefix="/rule-governance", tags=["rule-governance"])


class LegalSourceInput(BaseModel):
    citation: str = Field(min_length=1, max_length=300)
    issuer: str = Field(min_length=1, max_length=200)
    adoption_date: str = Field(min_length=10, max_length=10)
    effective_from: str = Field(min_length=10, max_length=10)
    effective_to: str | None = Field(default=None, min_length=10, max_length=10)
    document_hash: str = Field(min_length=64, max_length=64)
    source_uri: str | None = None


class RulePackInput(BaseModel):
    version: str = Field(min_length=1, max_length=80)
    legal_source_hash: str | None = Field(default=None, min_length=64, max_length=64)
    rules_hash: str | None = Field(default=None, min_length=64, max_length=64)
    effective_from: date | None = None
    effective_to: date | None = None


class EvidenceInput(BaseModel):
    rule_pack_version: str = Field(min_length=1, max_length=80)
    component_code: str = Field(min_length=1, max_length=80)
    legal_source_id: UUID
    issuer: str = Field(min_length=1, max_length=200)
    article: str = Field(min_length=1, max_length=100)
    clause: str | None = Field(default=None, max_length=100)
    population_scope: str = Field(min_length=1, max_length=200)
    source_hash: str = Field(min_length=64, max_length=64)
    regression_suite_hash: str = Field(min_length=64, max_length=64)


def _write(principal: Principal) -> None:
    authorize(principal, "admin", Scope.MINISTRY, privileged=True)


def _read(principal: Principal) -> None:
    authorize(principal, "admin", Scope.MINISTRY, privileged=True)


@router.post("/legal-sources", status_code=201)
def create_legal_source(payload: LegalSourceInput, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    try:
        validate_legal_source_payload(
            adoption_date=payload.adoption_date,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            document_hash=payload.document_hash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with SessionLocal() as session:
        source = LegalSourceRecord(**payload.model_dump())
        session.add(source)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail="legal source could not be registered") from exc
        append_audit_event(event_type="legal.source.created", entity_type="legal_source", entity_id=str(source.id), actor_id=principal.user_id, payload={"citation": source.citation, "document_hash": source.document_hash}, reason="register legal source for rule governance", session=session)
        session.commit()
        return {"id": str(source.id), "status": source.status, "citation": source.citation, "document_hash": source.document_hash}


@router.post("/legal-sources/{source_id}/review")
def review_source(source_id: UUID, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        source = session.get(LegalSourceRecord, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="legal source not found")
        try:
            review_legal_source(source)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(event_type="legal.source.reviewed", entity_type="legal_source", entity_id=str(source.id), actor_id=principal.user_id, payload={"document_hash": source.document_hash}, reason="review legal source", session=session)
        session.commit()
        return {"id": str(source.id), "status": source.status, "reviewed_by": principal.user_id}


@router.post("/legal-sources/{source_id}/approve")
def approve_source(source_id: UUID, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        source = session.get(LegalSourceRecord, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="legal source not found")
        review = session.scalar(select(__import__("morva.persistence.models", fromlist=["AuditEventRecord"]).AuditEventRecord).where(__import__("morva.persistence.models", fromlist=["AuditEventRecord"]).AuditEventRecord.event_type == "legal.source.reviewed", __import__("morva.persistence.models", fromlist=["AuditEventRecord"]).AuditEventRecord.entity_id == str(source.id)).order_by(__import__("morva.persistence.models", fromlist=["AuditEventRecord"]).AuditEventRecord.sequence_no.desc()))
        try:
            approve_legal_source(source, principal.user_id, review.actor_id if review else None)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(event_type="legal.source.approved", entity_type="legal_source", entity_id=str(source.id), actor_id=principal.user_id, payload={"document_hash": source.document_hash}, reason="approve legal source", session=session)
        session.commit()
        return {"id": str(source.id), "status": source.status, "approved_by": principal.user_id}


@router.post("/packs", status_code=201)
def create_rule_pack(payload: RulePackInput, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    if payload.effective_from and payload.effective_to and payload.effective_to < payload.effective_from:
        raise HTTPException(status_code=422, detail="effective_to cannot precede effective_from")
    with SessionLocal() as session:
        if session.scalar(select(RulePackRecord).where(RulePackRecord.version == payload.version)) is not None:
            raise HTTPException(status_code=409, detail="rule pack version already exists")
        pack = RulePackRecord(**payload.model_dump())
        session.add(pack)
        session.flush()
        append_audit_event(event_type="rule.pack.created", entity_type="rule_pack", entity_id=str(pack.id), actor_id=principal.user_id, payload={"version": pack.version}, reason="register rule pack", session=session)
        session.commit()
        return {"id": str(pack.id), "version": pack.version, "status": pack.status}


@router.post("/packs/{version}/review")
def review_pack(version: str, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == version))
        if pack is None:
            raise HTTPException(status_code=404, detail="rule pack not found")
        try:
            review_rule_pack(pack)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        pack.reviewed_by = principal.user_id
        append_audit_event(event_type="rule.pack.reviewed", entity_type="rule_pack", entity_id=str(pack.id), actor_id=principal.user_id, payload={"version": version}, reason="review rule pack", session=session)
        session.commit()
        return {"version": version, "status": pack.status, "reviewed_by": pack.reviewed_by}


@router.post("/packs/{version}/approve")
def approve_pack(version: str, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == version))
        if pack is None:
            raise HTTPException(status_code=404, detail="rule pack not found")
        result = approve_rule_pack(session, pack, principal.user_id)
        if not result["ready"]:
            raise HTTPException(status_code=409, detail={"message": "rule pack is not legally ready", "blockers": result["blockers"]})
        append_audit_event(event_type="rule.pack.approved", entity_type="rule_pack", entity_id=str(pack.id), actor_id=principal.user_id, payload={"version": version}, reason="approve rule pack", session=session)
        session.commit()
        return {"version": version, "status": pack.status, "approved_by": pack.approved_by, "approved_at": pack.approved_at.isoformat() if pack.approved_at else None}


@router.post("/evidence", status_code=201)
def create_evidence(payload: EvidenceInput, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    try:
        validate_evidence_payload(article=payload.article, population_scope=payload.population_scope, source_hash=payload.source_hash, regression_suite_hash=payload.regression_suite_hash)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    with SessionLocal() as session:
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == payload.rule_pack_version))
        source = session.get(LegalSourceRecord, payload.legal_source_id)
        if pack is None:
            raise HTTPException(status_code=404, detail="rule pack not found")
        if source is None:
            raise HTTPException(status_code=404, detail="legal source not found")
        if pack.status == "approved":
            raise HTTPException(status_code=409, detail="cannot add evidence to an approved rule pack")
        if source.status != "approved":
            raise HTTPException(status_code=409, detail="legal source must be approved before evidence registration")
        if payload.source_hash != source.document_hash:
            raise HTTPException(status_code=409, detail="source_hash does not match legal source document hash")
        evidence = RuleEvidenceRecord(**payload.model_dump())
        session.add(evidence)
        try:
            session.flush()
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail="rule evidence already exists for this component and pack") from exc
        append_audit_event(event_type="rule.evidence.created", entity_type="rule_evidence", entity_id=str(evidence.id), actor_id=principal.user_id, payload={"rule_pack_version": evidence.rule_pack_version, "component_code": evidence.component_code, "source_hash": evidence.source_hash}, reason="register legal evidence for rule component", session=session)
        session.commit()
        return {"id": str(evidence.id), "status": evidence.status, "component_code": evidence.component_code}


@router.post("/evidence/{evidence_id}/review")
def review_rule_evidence(evidence_id: UUID, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        evidence = session.get(RuleEvidenceRecord, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="rule evidence not found")
        try:
            review_evidence(evidence, principal.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(event_type="rule.evidence.reviewed", entity_type="rule_evidence", entity_id=str(evidence.id), actor_id=principal.user_id, payload={"component_code": evidence.component_code}, reason="review rule evidence", session=session)
        session.commit()
        return {"id": str(evidence.id), "status": evidence.status, "reviewed_by": evidence.reviewed_by}


@router.post("/evidence/{evidence_id}/approve")
def approve_rule_evidence(evidence_id: UUID, principal: Principal = Depends(get_current_principal)):
    _write(principal)
    with SessionLocal() as session:
        evidence = session.get(RuleEvidenceRecord, evidence_id)
        if evidence is None:
            raise HTTPException(status_code=404, detail="rule evidence not found")
        source = session.get(LegalSourceRecord, evidence.legal_source_id)
        if source is None or source.status != "approved":
            raise HTTPException(status_code=409, detail="legal source must be approved before evidence approval")
        try:
            approve_evidence(evidence, principal.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(event_type="rule.evidence.approved", entity_type="rule_evidence", entity_id=str(evidence.id), actor_id=principal.user_id, payload={"component_code": evidence.component_code}, reason="approve rule evidence", session=session)
        session.commit()
        return {"id": str(evidence.id), "status": evidence.status, "approved_by": evidence.approved_by, "approved_at": evidence.approved_at.isoformat() if evidence.approved_at else None}


@router.get("/packs/{version}/readiness")
def get_pack_readiness(version: str, principal: Principal = Depends(get_current_principal)):
    _read(principal)
    with SessionLocal() as session:
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == version))
        if pack is None:
            raise HTTPException(status_code=404, detail="rule pack not found")
        result = pack_readiness(session, pack)
        return {"version": version, **result}
