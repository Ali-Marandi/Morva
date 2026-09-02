from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import LifecycleEventRecord, PayrollArtifactRecord
from morva.persistence.models import ImportBatchRecord, PayrollLineRecord, PayrollRunRecord, PersonnelSnapshotRecord, RulePackRecord
from morva.payroll import PayrollCalculator, PayrollLine
from morva.payroll.artifacts import materialize_run_artifacts
from morva.payroll.lifecycle import PayrollStatus, transition
from morva.runtime.config import settings
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical
from morva.security.policy import authorize, require_distinct_actors

router = APIRouter(prefix="/payroll", tags=["payroll"])
calculator = PayrollCalculator()

class PayrollRunCreate(BaseModel):
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    ruleset_version: str = Field(min_length=1, max_length=50)
    organization_unit_id: str = Field(min_length=1, max_length=50)
    ruleset_hash: str | None = Field(default=None, min_length=64, max_length=64)

class TransitionNote(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)

@router.post("/runs", status_code=status.HTTP_201_CREATED)
def create_run(payload: PayrollRunCreate, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    authorize(principal, "payroll.run.create", principal.scope, resource_scope_id=payload.organization_unit_id)
    with SessionLocal() as session:
        existing = session.scalar(select(PayrollRunRecord).where(PayrollRunRecord.period == payload.period, PayrollRunRecord.organization_unit_id == payload.organization_unit_id))
        if existing and existing.status != PayrollStatus.CANCELLED.value:
            raise HTTPException(status_code=409, detail="payroll run already exists for period and organization")
        record = PayrollRunRecord(id=uuid4(), period=payload.period, organization_unit_id=payload.organization_unit_id, ruleset_version=payload.ruleset_version, ruleset_hash=payload.ruleset_hash, status=PayrollStatus.DRAFT.value, created_by=principal.user_id)
        session.add(record)
        session.flush()
        append_audit_event(event_type="payroll.run.created", entity_type="payroll_run", entity_id=record.id, actor_id=principal.user_id, payload={"period": payload.period, "organization_unit_id": payload.organization_unit_id, "ruleset_version": payload.ruleset_version}, reason="create payroll run", session=session)
        session.commit()
        return {"id": str(record.id), "status": PayrollStatus.DRAFT.value, "created_by": principal.user_id}

@router.post("/calculate", status_code=status.HTTP_410_GONE)
def legacy_calculate_blocked(_principal: Principal = Depends(get_current_principal)) -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="direct payroll calculation from caller-supplied lines is disabled; create a PayrollRun and import approved source data")

def _load_run(session, run_id: UUID, principal: Principal, permission: str) -> PayrollRunRecord:
    run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="payroll run not found")
    authorize_hierarchical(session, principal, permission, run.organization_unit_id)
    return run

def _transition_run(*, session, run: PayrollRunRecord, target: PayrollStatus, principal: Principal, permission: str, reason: str, distinct_from: list[str | None] = (), correlation_id: str, idempotency_key: str) -> None:
    authorize_hierarchical(session, principal, permission, run.organization_unit_id)
    if target in {PayrollStatus.APPROVED, PayrollStatus.FROZEN, PayrollStatus.REVIEWED} and not principal.mfa_verified:
        raise HTTPException(status_code=403, detail="MFA is required for privileged payroll transitions")
    require_distinct_actors([*distinct_from, principal.user_id])
    run_locked = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run.id).with_for_update()).scalar_one()
    previous = PayrollStatus(run_locked.status)
    existing = session.scalar(select(LifecycleEventRecord).where(LifecycleEventRecord.payroll_run_id == run.id, LifecycleEventRecord.idempotency_key == idempotency_key))
    if existing is not None:
        run.status = existing.new_status
        return
    new_status = transition(previous, target)
    sequence = (session.scalar(select(func.max(LifecycleEventRecord.sequence_no)).where(LifecycleEventRecord.payroll_run_id == run.id)) or 0) + 1
    now = datetime.utcnow()
    run_locked.status = new_status.value
    if target is PayrollStatus.REVIEWED:
        run_locked.reviewed_by, run_locked.reviewed_at = principal.user_id, now
    elif target is PayrollStatus.APPROVED:
        run_locked.approved_by, run_locked.approved_at = principal.user_id, now
    elif target is PayrollStatus.FROZEN:
        run_locked.frozen_at = now
    elif target is PayrollStatus.EXPORTED:
        run_locked.exported_at = now
    elif target is PayrollStatus.SUBMITTED:
        run_locked.submitted_by, run_locked.submitted_at = principal.user_id, now
    elif target is PayrollStatus.PAYMENT_CONFIRMED:
        run_locked.payment_confirmed_by, run_locked.payment_confirmed_at = principal.user_id, now
    elif target is PayrollStatus.RECONCILED:
        run_locked.reconciled_by, run_locked.reconciled_at = principal.user_id, now
    session.add(LifecycleEventRecord(id=uuid4(), payroll_run_id=run.id, sequence_no=sequence, previous_status=previous.value, new_status=new_status.value, actor_id=principal.user_id, organization_unit_id=run.organization_unit_id, reason=reason, correlation_id=correlation_id, idempotency_key=idempotency_key, evidence_hash=run_locked.output_hash))
    append_audit_event(event_type=f"payroll.run.{target.value}", entity_type="payroll_run", entity_id=str(run.id), actor_id=principal.user_id, payload={"previous_status": previous.value, "status": target.value, "correlation_id": correlation_id}, reason=reason, session=session)

@router.post("/runs/{run_id}/calculate")
def calculate_persisted_run(run_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.calculate")
        if run.status != PayrollStatus.DATA_RECEIVED.value:
            raise HTTPException(status_code=409, detail="payroll run must be in data_received state before calculation")
        if run.source_import_batch_id is None:
            raise HTTPException(status_code=423, detail="calculation is blocked: no immutable source import is attached")
        batch = session.get(ImportBatchRecord, run.source_import_batch_id)
        if batch is None or batch.status != "ready":
            raise HTTPException(status_code=423, detail="calculation is blocked: source import is not ready")
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == run.ruleset_version))
        if pack is None or pack.status not in {"approved", "published"}:
            raise HTTPException(status_code=423, detail="payroll calculation is blocked: Rule Pack is not approved/published")
        if not run.ruleset_hash or not pack.rules_hash or run.ruleset_hash != pack.rules_hash:
            raise HTTPException(status_code=423, detail="payroll calculation is blocked: immutable Rule Pack hash evidence is required")
        lines = session.scalars(select(PayrollLineRecord).where(PayrollLineRecord.payroll_run_id == run.id)).all()
        if not lines:
            raise HTTPException(status_code=409, detail="payroll run contains no projected payroll lines")
        if any(line.mapping_status != "approved" for line in lines):
            raise HTTPException(status_code=423, detail="calculation is blocked: one or more payroll-line mappings require review")
        employee_numbers = {line.employee_no for line in lines}
        snapshots = session.scalars(select(PersonnelSnapshotRecord).where(PersonnelSnapshotRecord.effective_period == run.period, PersonnelSnapshotRecord.employee_no.in_(employee_numbers))).all()
        snapshot_by_employee = {item.employee_no: item for item in snapshots}
        if set(snapshot_by_employee) != employee_numbers:
            missing = sorted(employee_numbers - set(snapshot_by_employee))
            raise HTTPException(status_code=423, detail=f"calculation is blocked: personnel snapshot missing for {missing}")
        if any(line.currency_code != run.currency_code for line in lines):
            raise HTTPException(status_code=409, detail="payroll line currency does not match payroll run currency")
        results: dict[str, object] = {}
        for employee_no in sorted(employee_numbers):
            employee_lines = [PayrollLine(code=line.code, title=line.title, amount=line.amount, kind=line.kind, taxable=line.taxable, pensionable=line.pensionable, insurable=line.insurable, rule_code=line.rule_code, explanation=line.explanation) for line in lines if line.employee_no == employee_no]
            result = calculator.calculate(employee_no=employee_no, period=run.period, ruleset_version=run.ruleset_version, lines=employee_lines)
            results[employee_no] = {"gross": str(result.result.gross), "deductions": str(result.result.deductions), "net": str(result.result.net), "fingerprint": result.fingerprint, "personnel_snapshot_hash": snapshot_by_employee[employee_no].snapshot_hash}
        run.input_hash = _hash_lines(lines)
        run.output_hash = _hash_results(results)
        run.status = transition(PayrollStatus.DATA_RECEIVED, PayrollStatus.CALCULATING).value
        artifact_count = materialize_run_artifacts(session, run.id)
        if artifact_count != len(employee_numbers):
            raise HTTPException(status_code=500, detail="authoritative payroll artifact count does not match calculation population")
        session.add(LifecycleEventRecord(id=uuid4(), payroll_run_id=run.id, sequence_no=1, previous_status=PayrollStatus.DATA_RECEIVED.value, new_status=run.status, actor_id=principal.user_id, organization_unit_id=run.organization_unit_id, reason="calculate and persist authoritative payroll artifacts", correlation_id=f"calc-{run.id}", idempotency_key=f"calc-{run.id}", evidence_hash=run.output_hash))
        append_audit_event(event_type="payroll.run.calculated", entity_type="payroll_run", entity_id=str(run.id), actor_id=principal.user_id, payload={"input_hash": run.input_hash, "output_hash": run.output_hash, "employee_count": len(results), "artifact_count": artifact_count, "source_import_batch_id": str(batch.id)}, reason="calculate and persist authoritative payroll artifacts", session=session)
        session.commit()
        return {"run_id": str(run.id), "status": run.status, "employee_count": len(results), "artifact_count": artifact_count, "input_hash": run.input_hash, "output_hash": run.output_hash}

@router.post("/runs/{run_id}/validate")
def validate_run(run_id: UUID, note: TransitionNote, principal: Principal = Depends(get_current_principal), correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"), idempotency_key: str = Header(min_length=12, max_length=150, alias="Idempotency-Key")) -> dict[str, str]:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.calculate")
        if not run.input_hash or not run.output_hash:
            raise HTTPException(status_code=409, detail="calculation evidence is missing")
        artifacts = session.scalar(select(func.count()).select_from(PayrollArtifactRecord).where(PayrollArtifactRecord.payroll_run_id == run.id)) or 0
        if artifacts == 0:
            raise HTTPException(status_code=423, detail="validation is blocked: no persisted payroll artifacts")
        _transition_run(session=session, run=run, target=PayrollStatus.VALIDATING, principal=principal, permission="payroll.run.calculate", reason=note.reason, correlation_id=correlation_id, idempotency_key=idempotency_key)
        session.commit()
        return {"run_id": str(run.id), "status": run.status}

@router.post("/runs/{run_id}/review")
def review_run(run_id: UUID, note: TransitionNote, principal: Principal = Depends(get_current_principal), correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"), idempotency_key: str = Header(min_length=12, max_length=150, alias="Idempotency-Key")) -> dict[str, str]:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.review")
        _transition_run(session=session, run=run, target=PayrollStatus.REVIEWED, principal=principal, permission="payroll.run.review", reason=note.reason, distinct_from=[run.created_by], correlation_id=correlation_id, idempotency_key=idempotency_key)
        session.commit()
        return {"run_id": str(run.id), "status": run.status}

@router.post("/runs/{run_id}/approve")
def approve_run(run_id: UUID, note: TransitionNote, principal: Principal = Depends(get_current_principal), correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"), idempotency_key: str = Header(min_length=12, max_length=150, alias="Idempotency-Key")) -> dict[str, str]:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.approve")
        _transition_run(session=session, run=run, target=PayrollStatus.APPROVED, principal=principal, permission="payroll.run.approve", reason=note.reason, distinct_from=[run.created_by, run.reviewed_by], correlation_id=correlation_id, idempotency_key=idempotency_key)
        session.commit()
        return {"run_id": str(run.id), "status": run.status}

@router.post("/runs/{run_id}/freeze")
def freeze_run(run_id: UUID, note: TransitionNote, principal: Principal = Depends(get_current_principal), correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"), idempotency_key: str = Header(min_length=12, max_length=150, alias="Idempotency-Key")) -> dict[str, str]:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.approve")
        _transition_run(session=session, run=run, target=PayrollStatus.FROZEN, principal=principal, permission="payroll.run.approve", reason=note.reason, distinct_from=[run.created_by, run.reviewed_by, run.approved_by], correlation_id=correlation_id, idempotency_key=idempotency_key)
        session.commit()
        return {"run_id": str(run.id), "status": run.status}

@router.post("/runs/{run_id}/export")
def export_run(run_id: UUID, _note: TransitionNote, principal: Principal = Depends(get_current_principal)) -> None:
    with SessionLocal() as session:
        run = _load_run(session, run_id, principal, "payroll.run.approve")
        if run.status != PayrollStatus.FROZEN.value:
            raise HTTPException(status_code=409, detail="payroll run must be frozen before export")
    if not settings.integrations_enabled:
        raise HTTPException(status_code=503, detail="external integrations are not enabled; export is fail-closed")
    raise HTTPException(status_code=503, detail="no approved production export adapter is configured")

def _hash_lines(lines: list[PayrollLineRecord]) -> str:
    import hashlib
    canonical = "|".join(f"{line.employee_no}:{line.code}:{line.kind}:{line.amount}:{line.rule_code or ''}" for line in sorted(lines, key=lambda item: (item.employee_no, item.code, item.kind, str(item.amount))))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _hash_results(results: dict[str, object]) -> str:
    import hashlib, json
    canonical = json.dumps(results, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
