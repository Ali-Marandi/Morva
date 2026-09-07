from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from morva.masterdata.acceptance import (
    MasterDataAcceptanceRequest,
    assess_master_data_acceptance,
    confirm_master_data_acceptance,
)
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.persistence.database import SessionLocal
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize

router = APIRouter(prefix="/master-data", tags=["master-data-acceptance"])


class AcceptanceInput(BaseModel):
    dataset_name: str = Field(min_length=1, max_length=120)
    schema_version: str = Field(min_length=1, max_length=50)
    source_system: str = Field(min_length=1, max_length=120)
    source_uri: str = Field(min_length=1, max_length=500)
    authoritative_source_reference: str = Field(min_length=1, max_length=300)
    dataset_period: str = Field(min_length=7, max_length=7)
    dataset_sha256: str = Field(min_length=64, max_length=64)
    row_count: int = Field(gt=0)
    duplicate_key_count: int = Field(ge=0)
    rejected_row_count: int = Field(ge=0)
    schema_valid: bool


class AcceptanceConfirmationInput(BaseModel):
    authority_confirmation_reference: str = Field(min_length=1, max_length=300)


def _authorize_write(principal: Principal) -> None:
    authorize(principal, "admin", Scope.MINISTRY, privileged=True)


@router.post("/acceptance-assessments", status_code=201)
def create_acceptance_assessment(
    payload: AcceptanceInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize_write(principal)
    with SessionLocal() as session:
        result = assess_master_data_acceptance(
            session,
            MasterDataAcceptanceRequest(**payload.model_dump()),
            principal.user_id,
        )
        return result.as_dict()


@router.post("/acceptance-assessments/{acceptance_id}/confirm")
def confirm_acceptance(
    acceptance_id: UUID,
    payload: AcceptanceConfirmationInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize_write(principal)
    with SessionLocal() as session:
        try:
            record = confirm_master_data_acceptance(
                session,
                acceptance_id,
                principal.user_id,
                payload.authority_confirmation_reference,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "id": str(record.id),
            "status": record.status,
            "dataset_name": record.dataset_name,
            "dataset_sha256": record.dataset_sha256,
            "accepted_by": record.accepted_by,
            "accepted_at": record.accepted_at.isoformat() if record.accepted_at else None,
            "authority_confirmation_reference": record.authority_confirmation_reference,
        }


@router.get("/acceptance-assessments/{acceptance_id}")
def get_acceptance_assessment(
    acceptance_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize_write(principal)
    with SessionLocal() as session:
        record = session.get(MasterDataAcceptanceRecord, acceptance_id)
        if record is None:
            raise HTTPException(status_code=404, detail="master-data acceptance assessment not found")
        return {
            "id": str(record.id),
            "dataset_name": record.dataset_name,
            "schema_version": record.schema_version,
            "source_system": record.source_system,
            "source_uri": record.source_uri,
            "authoritative_source_reference": record.authoritative_source_reference,
            "dataset_period": record.dataset_period,
            "dataset_sha256": record.dataset_sha256,
            "row_count": record.row_count,
            "duplicate_key_count": record.duplicate_key_count,
            "rejected_row_count": record.rejected_row_count,
            "schema_valid": record.schema_valid,
            "status": record.status,
            "integrity_blocking": record.integrity_blocking,
            "blockers": record.blockers or [],
            "warnings": record.warnings or [],
            "submitted_by": record.submitted_by,
            "accepted_by": record.accepted_by,
            "accepted_at": record.accepted_at.isoformat() if record.accepted_at else None,
            "authority_confirmation_reference": record.authority_confirmation_reference,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
