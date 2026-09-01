from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from morva.persistence.database import SessionLocal
from morva.persistence.models import PayrollLineRecord, PayrollRunRecord
from morva.payroll import PayrollCalculator, PayrollLine
from morva.payroll.lifecycle import PayrollStatus, transition
from morva.security.auth import Principal, get_current_principal

router = APIRouter(prefix="/payroll", tags=["payroll"])
calculator = PayrollCalculator()


class PayrollRunCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    ruleset_version: str = Field(min_length=1, max_length=50)
    organization_unit_id: str = Field(min_length=1, max_length=50)
    ruleset_hash: str | None = Field(default=None, min_length=64, max_length=64)


@router.post("/runs", status_code=status.HTTP_201_CREATED)
def create_run(
    payload: PayrollRunCreate,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        existing = session.scalar(
            select(PayrollRunRecord).where(
                PayrollRunRecord.period == payload.period,
                PayrollRunRecord.organization_unit_id == payload.organization_unit_id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="payroll run already exists for period and organization")
        record = PayrollRunRecord(
            id=uuid4(),
            period=payload.period,
            organization_unit_id=payload.organization_unit_id,
            ruleset_version=payload.ruleset_version,
            ruleset_hash=payload.ruleset_hash,
            status=PayrollStatus.DRAFT.value,
            created_by=principal.user_id,
        )
        session.add(record)
        session.commit()
        return {"id": str(record.id), "status": record.status, "created_by": record.created_by}


@router.post("/calculate", status_code=status.HTTP_410_GONE)
def legacy_calculate_blocked(_principal: Principal = Depends(get_current_principal)) -> None:
    """The legacy caller-supplied-line calculation API is intentionally disabled."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="direct payroll calculation from caller-supplied lines is disabled; use a persisted PayrollRun",
    )


@router.post("/runs/{run_id}/calculate")
def calculate_persisted_run(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, object]:
    with SessionLocal() as session:
        run = session.get(PayrollRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        if run.status != PayrollStatus.DRAFT.value:
            raise HTTPException(status_code=409, detail="payroll run is not in draft state")
        if run.created_by == principal.user_id:
            # Creation and calculation are deliberately separated from approval,
            # while the initial calculation may still be performed by a worker/finance role.
            pass

        lines = session.scalars(
            select(PayrollLineRecord).where(PayrollLineRecord.payroll_run_id == run.id)
        ).all()
        if not lines:
            raise HTTPException(status_code=409, detail="payroll run contains no server-approved source lines")

        employee_numbers = {line.employee_no for line in lines}
        results: dict[str, object] = {}
        for employee_no in sorted(employee_numbers):
            employee_lines = [
                PayrollLine(
                    code=line.code,
                    title=line.title,
                    amount=line.amount,
                    kind=line.kind,
                    taxable=line.taxable,
                    pensionable=line.pensionable,
                    insurable=line.insurable,
                    rule_code=line.rule_code,
                    explanation=line.explanation,
                )
                for line in lines
                if line.employee_no == employee_no
            ]
            result = calculator.calculate(
                employee_no=employee_no,
                period=datetime.strptime(run.period + "-01", "%Y-%m-%d").date(),
                ruleset_version=run.ruleset_version,
                lines=employee_lines,
            )
            results[employee_no] = {
                "gross": str(result.result.gross),
                "deductions": str(result.result.deductions),
                "net": str(result.result.net),
                "fingerprint": result.fingerprint,
            }

        run.status = transition(PayrollStatus.DRAFT, PayrollStatus.CALCULATING).value
        run.input_hash = _hash_lines(lines)
        run.output_hash = _hash_results(results)
        session.commit()
        return {
            "run_id": str(run.id),
            "status": run.status,
            "employee_count": len(results),
            "input_hash": run.input_hash,
            "output_hash": run.output_hash,
        }


def _hash_lines(lines: list[PayrollLineRecord]) -> str:
    import hashlib

    canonical = "|".join(
        f"{line.employee_no}:{line.code}:{line.kind}:{line.amount}:{line.rule_code or ''}"
        for line in sorted(lines, key=lambda item: (item.employee_no, item.code, item.kind, str(item.amount)))
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_results(results: dict[str, object]) -> str:
    import hashlib
    import json

    canonical = json.dumps(results, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
