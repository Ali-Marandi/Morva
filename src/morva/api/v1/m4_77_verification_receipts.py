from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope, authorize
from morva.api.v1.integration_execution_readiness import _normalize_history_timestamp

router = APIRouter()

_BASE_PATH = (
    "/readiness/convergence/freshness/policy-registry-snapshot-bound/"
    "receipt-lineage/independent-verification-history-integrity/"
    "m4-75-verification-receipt-history-integrity-snapshots"
)


class IndependentHistoricalM475VerificationReceiptResponse(BaseModel):
    id: UUID
    snapshot_id: UUID
    verification: dict[str, object]
    recorded_by: str
    created_at: datetime


class IndependentHistoricalM475VerificationReceiptHistoryResponse(BaseModel):
    items: list[IndependentHistoricalM475VerificationReceiptResponse]
    has_more: bool
    next_before_created_at: datetime | None = None
    next_before_id: UUID | None = None


@router.post(
    _BASE_PATH + "/{snapshot_id}/verification-receipts",
    response_model=IndependentHistoricalM475VerificationReceiptResponse,
)
def persist_independent_historical_m4_75_verification_receipt(
    snapshot_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM475VerificationReceiptResponse:
    authorize(principal, "evidence.binding.write", principal.scope, privileged=True)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.77 independent verification receipts are ministry-managed",
        )
    with SessionLocal() as session:
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            record = repository.record(
                snapshot_id=snapshot_id,
                recorded_by=principal.user_id,
            )
            verification = record.to_verification()
            append_audit_event(
                event_type="integration.readiness.independent_historical_m4_75_verification_receipt.recorded",
                entity_type="independent_historical_m4_75_verification_receipts_m4_77",
                entity_id=str(record.id),
                actor_id=principal.user_id,
                payload={
                    "snapshot_id": str(record.snapshot_id),
                    "valid": record.valid,
                    "verification_fingerprint": record.verification_fingerprint,
                },
                reason="M4.77 independent M4.76 verification receipt persisted",
                session=session,
            )
            session.commit()
        except IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
            session.rollback()
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return IndependentHistoricalM475VerificationReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=verification.to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )


@router.get(
    _BASE_PATH + "/verification-history",
    response_model=IndependentHistoricalM475VerificationReceiptHistoryResponse,
)
def list_independent_historical_m4_75_verification_receipts(
    snapshot_id: UUID | None = Query(default=None),
    valid: bool | None = Query(default=None),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM475VerificationReceiptHistoryResponse:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.77 independent verification receipts are ministry-managed",
        )
    if (before_created_at is None) != (before_id is None):
        raise HTTPException(
            status_code=422,
            detail="before_created_at and before_id must be supplied together",
        )
    if before_created_at is not None:
        before_created_at = _normalize_history_timestamp(before_created_at)

    with SessionLocal() as session:
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            records, has_more = repository.list(
                snapshot_id=snapshot_id,
                valid=valid,
                before_created_at=before_created_at,
                before_id=before_id,
                limit=limit,
            )
        except IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    items = [
        IndependentHistoricalM475VerificationReceiptResponse(
            id=record.id,
            snapshot_id=record.snapshot_id,
            verification=record.to_verification().to_payload(),
            recorded_by=record.recorded_by,
            created_at=record.created_at,
        )
        for record in records
    ]
    return IndependentHistoricalM475VerificationReceiptHistoryResponse(
        items=items,
        has_more=has_more,
        next_before_created_at=records[-1].created_at if has_more and records else None,
        next_before_id=records[-1].id if has_more and records else None,
    )


@router.get(
    _BASE_PATH + "/verification-receipts/{verification_id}/verify",
    response_model=IndependentHistoricalM475VerificationReceiptResponse,
)
def verify_independent_historical_m4_75_verification_receipt(
    verification_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM475VerificationReceiptResponse:
    authorize(principal, "evidence.read", principal.scope)
    with SessionLocal() as session:
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        try:
            record = repository.verify(verification_id)
        except IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    return IndependentHistoricalM475VerificationReceiptResponse(
        id=record.id,
        snapshot_id=record.snapshot_id,
        verification=record.to_verification().to_payload(),
        recorded_by=record.recorded_by,
        created_at=record.created_at,
    )
