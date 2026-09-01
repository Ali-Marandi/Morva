from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from morva.payroll.persisted_run import PayrollRunBlockedError, add_snapshot, calculate_persisted_snapshot
from morva.payroll.run_service import transition
from morva.persistence.database import SessionLocal
from morva.security.auth import Permission, Principal, principal_from_headers

router = APIRouter(prefix="/payroll-runs", tags=["payroll-run-snapshots"])


class SnapshotLineIn(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0)
    kind: str = Field(pattern="^(earning|deduction)$")
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    rule_code: str | None = Field(default=None, max_length=80)
    explanation: str | None = Field(default=None, max_length=2000)


class SnapshotIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=50)
    source_manifest_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    lines: list[SnapshotLineIn] = Field(min_length=1)


@router.post("/{run_id}/snapshots", status_code=status.HTTP_201_CREATED)
def create_snapshot(
    run_id: UUID,
    payload: SnapshotIn,
    principal: Principal = Depends(principal_from_headers),
) -> dict[str, object]:
    principal.require(Permission.CALCULATE_PAYROLL)
    with SessionLocal() as session:
        try:
            record = add_snapshot(
                session,
                run_id=run_id,
                employee_no=payload.employee_no,
                source_manifest_hash=payload.source_manifest_hash.lower(),
                payload={"employee_no": payload.employee_no, "lines": [line.model_dump(mode="json") for line in payload.lines]},
                principal=principal,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except PayrollRunBlockedError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {
            "id": str(record.id),
            "run_id": str(record.payroll_run_id),
            "employee_no": record.employee_no,
            "snapshot_hash": record.snapshot_hash,
            "source_manifest_hash": record.source_manifest_hash,
        }


@router.post("/{run_id}/admit")
def admit(
    run_id: UUID,
    principal: Principal = Depends(principal_from_headers),
) -> dict[str, object]:
    principal.require(Permission.CALCULATE_PAYROLL)
    with SessionLocal() as session:
        try:
            result = transition(
                session,
                run_id=run_id,
                target_status="data_received",
                principal=principal,
                reason="validated employee snapshots admitted",
                correlation_id=None,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {"id": str(result.run_id), "status": result.to_status, "version": result.version}


@router.post("/{run_id}/calculate/{employee_no}")
def calculate_persisted(
    run_id: UUID,
    employee_no: str,
    principal: Principal = Depends(principal_from_headers),
) -> dict[str, object]:
    principal.require(Permission.CALCULATE_PAYROLL)
    with SessionLocal() as session:
        try:
            calculation = calculate_persisted_snapshot(
                session,
                run_id=run_id,
                employee_no=employee_no,
                principal=principal,
            )
            transition_result = transition(
                session,
                run_id=run_id,
                target_status="calculated",
                principal=principal,
                reason=f"persisted snapshot calculation for {employee_no}",
                correlation_id=None,
            )
            session.commit()
        except PermissionError as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except (PayrollRunBlockedError, ValueError) as exc:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        result = calculation.result
        return {
            "employee_no": result.employee_no,
            "period": result.period,
            "ruleset_version": result.ruleset_version,
            "status": transition_result.to_status,
            "gross": str(result.gross),
            "deductions": str(result.deductions),
            "net": str(result.net),
            "fingerprint": calculation.fingerprint,
            "lines": [
                {
                    "code": line.code,
                    "title": line.title,
                    "amount": str(line.amount),
                    "kind": line.kind,
                    "rule_code": line.rule_code,
                    "explanation": line.explanation,
                }
                for line in result.lines
            ],
        }
