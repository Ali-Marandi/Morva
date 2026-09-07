from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from morva.audit.persistence import append_audit_event
from morva.persistence.calculation_matrix_records import CalculationMatrixRecord
from morva.persistence.database import SessionLocal
from morva.rules.calculation_matrix import (
    approve_matrix_entry,
    create_matrix_entry,
    matrix_readiness,
    validate_matrix_payload,
)
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import Scope, authorize

router = APIRouter(prefix="/calculation-matrix", tags=["calculation-matrix"])


class MatrixEntryInput(BaseModel):
    rule_pack_version: str = Field(min_length=1, max_length=80)
    component_code: str = Field(min_length=1, max_length=80)
    population_scope: str = Field(min_length=1, max_length=200)
    treatment: str
    expression: dict[str, Any]
    effective_from: date
    effective_to: date | None = None
    legal_source_id: UUID
    legal_article: str = Field(min_length=1, max_length=100)
    legal_clause: str | None = Field(default=None, max_length=100)
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    regression_suite_hash: str = Field(min_length=64, max_length=64)
    notes: str | None = None


def _authorize(principal: Principal) -> None:
    authorize(principal, "admin", Scope.MINISTRY, privileged=True)


@router.post("/entries", status_code=201)
def create_entry(
    payload: MatrixEntryInput,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize(principal)
    try:
        validate_matrix_payload(
            treatment=payload.treatment,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            regression_suite_hash=payload.regression_suite_hash,
            expression=payload.expression,
            legal_article=payload.legal_article,
            population_scope=payload.population_scope,
        )
        with SessionLocal() as session:
            entry = create_matrix_entry(session, payload.model_dump(), principal.user_id)
            session.commit()
            return {
                "id": str(entry.id),
                "status": entry.status,
                "component_code": entry.component_code,
                "rule_pack_version": entry.rule_pack_version,
            }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/entries/{entry_id}/review")
def review_entry(
    entry_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize(principal)
    with SessionLocal() as session:
        entry = session.get(CalculationMatrixRecord, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="calculation-matrix entry not found")
        if entry.status != "review_required":
            raise HTTPException(status_code=409, detail="calculation-matrix entry can only be reviewed from review_required")
        entry.status = "reviewed"
        entry.reviewed_by = principal.user_id
        entry.reviewed_at = datetime.utcnow()
        append_audit_event(
            event_type="rule.matrix.reviewed",
            entity_type="calculation_matrix",
            entity_id=str(entry.id),
            actor_id=principal.user_id,
            payload={"component_code": entry.component_code, "rule_pack_version": entry.rule_pack_version},
            reason="review calculation matrix entry",
            session=session,
        )
        session.commit()
        return {"id": str(entry.id), "status": entry.status, "reviewed_by": entry.reviewed_by}


@router.post("/entries/{entry_id}/approve")
def approve_entry(
    entry_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize(principal)
    with SessionLocal() as session:
        entry = session.get(CalculationMatrixRecord, entry_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="calculation-matrix entry not found")
        try:
            approve_matrix_entry(entry, principal.user_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        append_audit_event(
            event_type="rule.matrix.approved",
            entity_type="calculation_matrix",
            entity_id=str(entry.id),
            actor_id=principal.user_id,
            payload={"component_code": entry.component_code, "rule_pack_version": entry.rule_pack_version},
            reason="approve calculation matrix entry",
            session=session,
        )
        session.commit()
        return {
            "id": str(entry.id),
            "status": entry.status,
            "approved_by": entry.approved_by,
            "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
        }


@router.get("/{rule_pack_version}/readiness")
def get_readiness(
    rule_pack_version: str,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    _authorize(principal)
    with SessionLocal() as session:
        return {"rule_pack_version": rule_pack_version, **matrix_readiness(session, rule_pack_version).as_dict()}
