from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.api.v1.integration_execution_readiness import _normalize_history_timestamp
from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Repository,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope, authorize

router = APIRouter()

_BASE_PATH = (
    "/integration-execution/readiness/convergence/freshness/"
    "policy-registry-snapshot-bound/receipt-lineage/"
    "independent-verification-history-integrity/"
    "m4-77-verification-receipts"
)


class IndependentM477VerificationReceiptM479Response(BaseModel):
    id: UUID
    verification_receipt_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentM477VerificationReceiptM479HistoryResponse(BaseModel):
    items: list[IndependentM477VerificationReceiptM479Response]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


def _require_ministry(principal: Principal) -> None:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.79 independent verification receipts are ministry-managed",
        )


@router.post(
    _BASE_PATH + "/{verification_receipt_id}/verification-receipts",
    response_model=IndependentM477VerificationReceiptM479Response,
)
def persist_m4_78_verification_receipt(
    verification_receipt_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentM477VerificationReceiptM479Response:
    authorize(principal, "evidence.binding.write", principal.scope, privileged=True)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(status_code=403, detail="M4.79 independent verification receipts are ministry-managed")

    with SessionLocal() as session:
        repository = IndependentM477VerificationReceiptM479Repository(session)
        try:
            record = repository.record(
                verification_receipt_id=verification_receipt_id,
                recorded_by=principal.user_id,
            )
            append_audit_event(
                event_type="integration.readiness.independent_m4_78_verification_receipt.recorded",
                entity_type="independent_m4_77_verification_receipts_m4_79",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "verification_receipt_id": str(record.verification_receipt_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.79 independent M4.78 verification receipt persisted",
                session=session,
            )
            session.commit()
        except IndependentM477VerificationReceiptM479PersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return IndependentM477VerificationReceiptM479Response(
        id=record.id,
        verification_receipt_id=record.verification_receipt_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    _BASE_PATH + "/verification-history",
    response_model=IndependentM477VerificationReceiptM479HistoryResponse,
)
def list_m4_79_verification_receipts(
    verification_receipt_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentM477VerificationReceiptM479HistoryResponse:
    _require_ministry(principal)
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)
    with SessionLocal() as session:
        repository = IndependentM477VerificationReceiptM479Repository(session)
        try:
            records, has_more = repository.list(
                verification_receipt_id=verification_receipt_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentM477VerificationReceiptM479PersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return IndependentM477VerificationReceiptM479HistoryResponse(
        items=[
            IndependentM477VerificationReceiptM479Response(
                id=record.id,
                verification_receipt_id=record.verification_receipt_id,
                verification=record.to_verification().to_payload(),
                recorded_by=record.recorded_by,
                created_at=record.created_at,
            )
            for record in records
        ],
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    _BASE_PATH + "/verification-receipts/{verification_id}/verify",
    response_model=IndependentM477VerificationReceiptM479Response,
)
def verify_m4_79_verification_receipt(
    verification_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentM477VerificationReceiptM479Response:
    _require_ministry(principal)
    with SessionLocal() as session:
        repository = IndependentM477VerificationReceiptM479Repository(session)
        try:
            record = repository.verify(verification_id)
        except IndependentM477VerificationReceiptM479PersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return IndependentM477VerificationReceiptM479Response(
        id=record.id,
        verification_receipt_id=record.verification_receipt_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )
