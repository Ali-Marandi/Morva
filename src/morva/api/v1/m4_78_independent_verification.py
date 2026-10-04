from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from morva.persistence.database import SessionLocal
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_m4_78 import (
    IndependentHistoricalM475VerificationReceiptM478Error,
    independently_verify_historical_m4_75_verification_receipt_m4_77,
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


class IndependentHistoricalM475VerificationReceiptM478Response(BaseModel):
    verification: dict[str, object]


@router.get(
    _BASE_PATH + "/{verification_id}/verify-independent",
    response_model=IndependentHistoricalM475VerificationReceiptM478Response,
)
def verify_independent_m4_77_verification_receipt(
    verification_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentHistoricalM475VerificationReceiptM478Response:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.78 independent verification is ministry-managed",
        )

    with SessionLocal() as session:
        receipt = session.get(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
            verification_id,
        )
        if receipt is None:
            raise HTTPException(
                status_code=404,
                detail="M4.77 independent verification receipt not found",
            )

        snapshot = session.get(
            HistoricalM474VerificationReceiptHistoryIntegrityRecord,
            receipt.snapshot_id,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="M4.75 verification-receipt history integrity snapshot not found",
            )

        source_query = (
            select(IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        )
        source_records = list(session.scalars(source_query).all())
        source_repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        try:
            verification = independently_verify_historical_m4_75_verification_receipt_m4_77(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
        except IndependentHistoricalM475VerificationReceiptM478Error as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return IndependentHistoricalM475VerificationReceiptM478Response(
        verification=verification.to_payload()
    )
