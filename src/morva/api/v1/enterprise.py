from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.integrations.outbox import enqueue, record_inbox
from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import BankReconciliationRecord, PaymentBatchRecord, PaymentItemRecord, PayrollArtifactRecord, SensitiveIdentityRecord
from morva.persistence.models import EmployeeRecord, PayrollRunRecord, RulePackRecord
from morva.payroll.lifecycle import PayrollStatus, transition
from morva.payroll.artifacts import materialize_run_artifacts
from morva.payroll.replay import ReplayMismatch, replay_artifact
from morva.security.auth import Principal, get_current_principal
from morva.security.hierarchy import authorize_hierarchical
from morva.security.policy import require_distinct_actors

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


@router.post("/payroll/runs/{run_id}/materialize-artifacts")
def materialize_artifacts(run_id: UUID, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        run = session.get(PayrollRunRecord, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize_hierarchical(session, principal, "payroll.run.calculate", run.organization_unit_id)
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
        authorize_hierarchical(session, principal, "payroll.read", run.organization_unit_id)
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
        run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one_or_none()
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize_hierarchical(session, principal, "payroll.payment.release", run.organization_unit_id)
        if run.status != PayrollStatus.FROZEN.value:
            raise HTTPException(status_code=409, detail="payment batch requires a frozen payroll run")
        require_distinct_actors([run.created_by, run.reviewed_by, run.approved_by, principal.user_id])
        artifacts = session.scalars(select(PayrollArtifactRecord).where(PayrollArtifactRecord.payroll_run_id == run.id)).all()
        if not artifacts:
            raise HTTPException(status_code=423, detail="payment batch blocked: no persisted payroll artifacts")
        if any(artifact.net <= 0 for artifact in artifacts):
            raise HTTPException(status_code=423, detail="payment batch blocked: non-positive beneficiary net amount detected")
        pack = session.scalar(select(RulePackRecord).where(RulePackRecord.version == run.ruleset_version))
        if pack is None or pack.status not in {"approved", "published"} or not pack.rules_hash or not pack.legal_source_hash:
            raise HTTPException(status_code=423, detail="payment batch blocked: Rule Pack evidence is incomplete")
        existing = session.scalar(select(PaymentBatchRecord).where(PaymentBatchRecord.payroll_run_id == run.id))
        if existing is not None:
            return {"id": str(existing.id), "status": existing.status, "batch_reference": existing.batch_reference, "amount": str(existing.amount), "beneficiary_count": existing.beneficiary_count}
        employee_ids = {artifact.employee_no: artifact for artifact in artifacts}
        employees = session.scalars(select(EmployeeRecord).where(EmployeeRecord.employee_no.in_(employee_ids))).all()
        employee_by_no = {employee.employee_no: employee for employee in employees}
        identities = session.scalars(select(SensitiveIdentityRecord).where(SensitiveIdentityRecord.employee_id.in_([employee.id for employee in employees]))).all()
        identity_by_employee_id = {identity.employee_id: identity for identity in identities}
        if len(employee_by_no) != len(employee_ids):
            raise HTTPException(status_code=423, detail="payment batch blocked: beneficiary master data is incomplete")
        missing_accounts = [employee_no for employee_no, employee in employee_by_no.items() if employee.id not in identity_by_employee_id or not identity_by_employee_id[employee.id].bank_account_ciphertext]
        if missing_accounts:
            raise HTTPException(status_code=423, detail="payment batch blocked: secure bank-account record missing for one or more beneficiaries")
        total = sum((Decimal(artifact.net) for artifact in artifacts), Decimal("0"))
        batch = PaymentBatchRecord(id=uuid4(), payroll_run_id=run.id, batch_reference=f"MORVA-{run.period}-{uuid4().hex[:12].upper()}", currency_code=run.currency_code, amount=total, beneficiary_count=len(artifacts), status="approved_pending_submission", created_by=principal.user_id)
        session.add(batch)
        session.flush()
        for artifact in artifacts:
            employee = employee_by_no[artifact.employee_no]
            identity = identity_by_employee_id[employee.id]
            session.add(PaymentItemRecord(id=uuid4(), payment_batch_id=batch.id, employee_no=artifact.employee_no, artifact_id=artifact.id, amount=Decimal(artifact.net), currency_code=run.currency_code, bank_account_ciphertext=identity.bank_account_ciphertext, status="pending"))
        enqueue(session, operation="submit_payment_batch", provider="bank", correlation_id=correlation_id, idempotency_key=idempotency_key, payload={"payment_batch_id": str(batch.id), "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count, "currency_code": batch.currency_code})
        append_audit_event(event_type="payment.batch.created", entity_type="payment_batch", entity_id=str(batch.id), actor_id=principal.user_id, payload={"payroll_run_id": str(run.id), "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count}, reason="create secure beneficiary payment batch after frozen payroll approval", session=session)
        session.commit()
        return {"id": str(batch.id), "status": batch.status, "batch_reference": batch.batch_reference, "amount": str(batch.amount), "beneficiary_count": batch.beneficiary_count}


@router.post("/payments/bank-receipts")
def receive_bank_receipt(
    payload: dict[str, object],
    principal: Principal = Depends(get_current_principal),
    correlation_id: str = Header(min_length=8, max_length=100, alias="X-Correlation-Id"),
) -> dict[str, object]:
    provider = str(payload.get("provider", "bank"))
    external_id = str(payload.get("external_id", ""))
    batch_reference = str(payload.get("batch_reference", ""))
    settled_amount = Decimal(str(payload.get("settled_amount", "0")))
    if not external_id or not batch_reference or settled_amount < 0:
        raise HTTPException(status_code=422, detail="provider receipt fields are invalid")
    with SessionLocal() as session:
        batch = session.scalar(select(PaymentBatchRecord).where(PaymentBatchRecord.batch_reference == batch_reference))
        if batch is None:
            raise HTTPException(status_code=404, detail="payment batch not found")
        run = session.get(PayrollRunRecord, batch.payroll_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize_hierarchical(session, principal, "payroll.payment.reconcile", run.organization_unit_id)
        inbox = record_inbox(session, provider=provider, external_id=external_id, correlation_id=correlation_id, payload=payload)
        if inbox.status == "processed":
            existing = session.scalar(select(BankReconciliationRecord).where(BankReconciliationRecord.external_id == external_id))
            return {"status": "duplicate", "reconciliation_id": str(existing.id) if existing else None}
        expected = Decimal(batch.amount)
        difference = settled_amount - expected
        status_value = "reconciled" if difference == Decimal("0") else "exception"
        reconciliation = BankReconciliationRecord(id=uuid4(), payment_batch_id=batch.id, external_id=external_id, expected_amount=expected, settled_amount=settled_amount, status=status_value, difference=difference, evidence={"provider": provider, "correlation_id": correlation_id})
        session.add(reconciliation)
        inbox.status = "processed"
        if status_value == "reconciled":
            batch.status = "settled"
            for item in session.scalars(select(PaymentItemRecord).where(PaymentItemRecord.payment_batch_id == batch.id)).all():
                item.status = "settled"
        append_audit_event(event_type="bank.receipt.processed", entity_type="payment_batch", entity_id=str(batch.id), actor_id=principal.user_id, payload={"external_id": external_id, "expected_amount": str(expected), "settled_amount": str(settled_amount), "status": status_value}, reason="process bank settlement receipt", session=session)
        session.commit()
        return {"status": status_value, "payment_batch_id": str(batch.id), "reconciliation_id": str(reconciliation.id), "difference": str(difference)}
