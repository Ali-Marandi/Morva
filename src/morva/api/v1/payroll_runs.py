from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from morva.persistence.database import SessionLocal
from morva.payroll.run_service import create_run, transition
from morva.security.auth import Principal, principal_from_headers

router = APIRouter(prefix="/payroll-runs", tags=["payroll-runs"])


class CreateRunIn(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    ruleset_version: str = Field(min_length=1, max_length=80)
    organization_scope: str = Field(min_length=1, max_length=80)


class TransitionIn(BaseModel):
    target_status: str = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, max_length=1000)
    correlation_id: str | None = Field(default=None, max_length=100)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payroll_run(
    payload: CreateRunIn,
    principal: Principal = Depends(principal_from_headers),
) -> dict[str, object]:
    with SessionLocal() as session:
        run = create_run(
            session,
            period=payload.period,
            ruleset_version=payload.ruleset_version,
            principal=principal,
            organization_scope=payload.organization_scope,
        )
        session.commit()
        return {
            "id": str(run.id),
            "period": run.period,
            "ruleset_version": run.ruleset_version,
            "status": run.status,
            "organization_scope": run.organization_scope,
            "version": run.version,
        }


@router.post("/{run_id}/transition")
def transition_payroll_run(
    run_id: UUID,
    payload: TransitionIn,
    principal: Principal = Depends(principal_from_headers),
) -> dict[str, object]:
    with SessionLocal() as session:
        try:
            result = transition(
                session,
                run_id=run_id,
                target_status=payload.target_status,
                principal=principal,
                reason=payload.reason,
                correlation_id=payload.correlation_id,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {
            "id": str(result.run_id),
            "from_status": result.from_status,
            "to_status": result.to_status,
            "version": result.version,
        }
