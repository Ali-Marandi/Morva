from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from morva.persistence.database import SessionLocal
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479Record,
)
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    IndependentM477VerificationReceiptM480Error,
    independently_verify_m4_79_verification_receipt,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope, authorize

router = APIRouter()

_BASE_PATH = (
    "/integration-execution/readiness/convergence/freshness/"
    "policy-registry-snapshot-bound/receipt-lineage/"
    "independent-verification-history-integrity/m4-77-verification-receipts/"
    "m4-79-verification-receipts"
)


class IndependentM477VerificationReceiptM480Response(BaseModel):
    id: UUID
    verification: dict[str, object]


def _require_ministry(principal: Principal) -> None:
    authorize(principal, "evidence.read", principal.scope)
    if principal.scope is not Scope.MINISTRY:
        raise HTTPException(
            status_code=403,
            detail="M4.80 independent verification is ministry-managed",
        )


@router.get(
    _BASE_PATH + "/{verification_id}/verify-independent",
    response_model=IndependentM477VerificationReceiptM480Response,
)
def independently_verify_m4_79_verification_receipt_m4_80(
    verification_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> IndependentM477VerificationReceiptM480Response:
    _require_ministry(principal)
    with SessionLocal() as session:
        receipt = session.get(
            IndependentM477VerificationReceiptM479Record,
            verification_id,
        )
        if receipt is None:
            raise HTTPException(
                status_code=404,
                detail="M4.79 independent verification receipt not found",
            )

        source_receipt = session.get(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
            receipt.verification_receipt_id,
        )
        if source_receipt is None:
            raise HTTPException(
                status_code=404,
                detail="M4.77 independent verification receipt not found",
            )
        snapshot = session.get(
            HistoricalM474VerificationReceiptHistoryIntegrityRecord,
            source_receipt.snapshot_id,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail="M4.75 verification-receipt history snapshot not found",
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
            verification = independently_verify_m4_79_verification_receipt(
                receipt=receipt,
                source_receipt=source_receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
        except IndependentM477VerificationReceiptM480Error as exc:
            status = 404 if "not found" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

        response = IndependentM477VerificationReceiptM480Response(
            id=receipt.id,
            verification=verification.to_payload(),
        )
    return response
