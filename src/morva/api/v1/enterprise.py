from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select

from morva.audit.persistence import append_audit_event
from morva.integrations.outbox import enqueue
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import PaymentBatchRecord, PayrollArtifactRecord
from morva.persistence.models import PayrollRunRecord, RulePackRecord
from morva.payroll.artifacts import materialize_run_artifacts
from morva.payroll.lifecycle import PayrollStatus
from morva.payroll.replay import ReplayMismatch, replay_artifact
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import authorize, require_distinct_actors

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.post("/payroll/runs/{run_id}/materialize-artifacts")
def materialize_artifacts(run_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        run = session.get(PayrollRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize(principal, "payroll.run.calculate", principal.scope, resource_scope_id=run.organization_unit_id)
        if run.status not in {PayrollStatus.CALCULATING.value, PayrollStatus.VALIDATING.value}:
            raise HTTPException(status_code=409, detail="payroll run is not in a calculation/validation state")
        count = materialize_run_artifacts(session, run.id)
        append_audit_event(event_type="payroll.artifacts.materialized", entity_type="payroll_run", entity_id=str(run.id), actor_id=principal.user_id, payload={"created": count}, reason="persist deterministic employee payroll artifacts", session=session)
        session.commit()
        return {"run_id": str(run.id), "created_artifacts": count}


@router.get("/payroll/artifacts/{artifact_id}/replay")
def verify_historical_artifact(artifact_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        artifact = session.get(PayrollArtifactRecord, artifact_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="payroll artifact not found")
        run = session.get(PayrollRunRecord, artifact.payroll_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="source payroll run not found")
        authorize(principal, "payroll.read", principal.scope, resource_scope_id=run.organization_unit_id)
        try:
            result = replay_artifact(session, artifact.id)
        except ReplayMismatch as exc:
            append_audit_event(event_type="payroll.artifact.replay_failed", entity_type="payroll_artifact", entity_id=str(artifact.id), actor_id=principal.user_id, payload={"reason_code": "REPLAY_MISMATCH"}, reason="historical payroll replay mismatch", session=session)
            session.commit()
            raise HTTPException(status_code=409, detail="historical payroll replay mismatch") from exc
        append_audit_event(event_type="payroll.artifact.replayed", entity_type="payroll_artifact", entity_id=str(artifact.id), actor_id=principal.user_id, payload={"output_hash": result["output_hash"]}, reason="verify historical payroll artifact reproducibility", session=session)
        session.commit()
        return result


@router.post("/payroll/runs/{run_id}/payment-batch", status_code=status.HTTP_201_CREATED)
def create_payment_batch(
    run_id: UUID,
    principal: Principal = Depends(get_current_principal),
    idempotency_key: str = Header(min_length=12, max_length=150, alias="Idempotency-Key"),
    correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"),
) -> dict[str, object]:
    with SessionLocal() as session:
        run = session.get(PayrollRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize(principal, "payroll.payment.release", principal.scope, resource_scope_id=run.organization_unit_id, privileged=True)
        if run.status != PayrollStatus.FROZEN.value:
            raise HTTPException(status_code=409, detail="payment batch requires a frozen payroll run")
        require_distinct_actors([run.created_by, run.reviewed_by, run.approved_by, principal.user_id])
        artifact_count = session.scalar(select(func.count()).select_from(PayrollArtifactRecord).where(PayrollArtifactRecord.payroll_run_id == run.id)) or 0
        if artifact_count == 0:
            raise HTTPException(status_code=423, detail="payment batch blocked: no persisted payroll artifacts")
        artifact_sum = session.scalar(select(func.sum(PayrollArtifactRecord.net)).where(PayrollArtifactRecord.payroll_run_id == run.id)) or Decimal("0")
        existing = session.scalar(select(PaymentBatchRecord).where(PaymentBatchRecord.payroll_run_id == run.id))
        if existing is not None:
            return {"id": str(existing.id), "status": existing.status, "batch_reference": existing.batch_reference, "amount": str(existing.amount), "beneficiary_count": existing.beneficiary_count}
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == run.ruleset_version))
        if pack is None or pack.status not in {"approved", "published"} or not pack.rules_hash or not pack.legal_source_hash:
            raise HTTPException(status_code=423, detail="payment batch blocked: Rule Pack evidence is incomplete")
        batch = PaymentBatchRecord(id=uuid4(), payroll_run_id=run.id, batch_reference=f"MORVA-{run.period}-{uuid4().hex[:12].upper()}", currency_code=run.currency_code, amount=Decimal(artifact_sum), beneficiary_count=int(artifact_count), status="approved_pending_submission", created_by=principal.user_id)
        session.add(batch)
        session.flush()
        enqueue(session, operation="submit_payment_batch", provider="bank", correlation_id=correlation_id, idempotency_key=idempotency_key, payload={"payment_batch_id": str(batch.id), "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count, "currency_code": batch.currency_code})
        append_audit_event(event_type="payment.batch.created", entity_type="payment_batch", entity_id=str(batch.id), actor_id=principal.user_id, payload={"payroll_run_id": str(run.id), "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count}, reason="create payment batch after frozen payroll approval", session=session)
        session.commit()
        return {"id": str(batch.id), "status": batch.status, "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count}
