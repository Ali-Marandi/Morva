from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from morva.audit.persistence import append_audit_event
from morva.persistence.database import SessionLocal
from morva.persistence.models import EmployeeRecord, ImportBatchRecord, ImportIssueRecord, ImportRecordRecord, PayrollLineRecord, PayrollRunRecord, PersonnelSnapshotRecord
from morva.payroll.lifecycle import PayrollStatus, transition
from morva.payroll.source_projection import project_components
from morva.security.auth import Principal, get_current_principal
from morva.security.policy import authorize

router = APIRouter(prefix="/imports", tags=["imports"])


class ProjectRequest(BaseModel):
    payroll_run_id: UUID


@router.post("/{import_batch_id}/project")
def project_import(import_batch_id: UUID, payload: ProjectRequest, principal: Principal = Depends(get_current_principal)) -> dict[str, object]:
    with SessionLocal() as session:
        batch = session.get(ImportBatchRecord, import_batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="import batch not found")
        run = session.get(PayrollRunRecord, payload.payroll_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="payroll run not found")
        authorize(principal, "payroll.run.create", principal.scope, resource_scope_id=run.organization_unit_id)
        if batch.status != "ready":
            raise HTTPException(status_code=423, detail="import batch is quarantined or not ready")
        if run.status != PayrollStatus.DRAFT.value:
            raise HTTPException(status_code=409, detail="payroll run must be draft before source projection")
        if run.period != batch.period:
            raise HTTPException(status_code=409, detail="import period does not match payroll run period")
        if session.scalar(select(PayrollLineRecord).where(PayrollLineRecord.payroll_run_id == run.id).limit(1)):
            raise HTTPException(status_code=409, detail="payroll run already has projected lines")
        records = session.scalars(select(ImportRecordRecord).where(ImportRecordRecord.import_batch_id == batch.id, ImportRecordRecord.source_name == "گزارش لیست حقوق.xlsx")).all()
        if not records:
            raise HTTPException(status_code=409, detail="no payroll source records found in import batch")
        created = 0
        quarantined = 0
        for record in records:
            employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.source_employee_key == record.source_employee_key))
            if employee is None:
                session.add(ImportIssueRecord(import_batch_id=batch.id, issue_code="EMPLOYEE_MASTER_MISSING", severity="critical", record_key=record.source_employee_key, evidence={"stage": "projection", "period": batch.period}, status="quarantined"))
                quarantined += 1
                continue
            snapshot = session.scalar(select(PersonnelSnapshotRecord).where(PersonnelSnapshotRecord.employee_no == employee.employee_no, PersonnelSnapshotRecord.effective_period == batch.period))
            if snapshot is None:
                session.add(ImportIssueRecord(import_batch_id=batch.id, issue_code="PERSONNEL_SNAPSHOT_MISSING", severity="critical", record_key=record.source_employee_key, evidence={"employee_no": employee.employee_no, "period": batch.period}, status="quarantined"))
                quarantined += 1
                continue
            for item in project_components(record.payload.get("components", {})):
                item_status = str(item["status"])
                if item_status == "quarantined":
                    session.add(ImportIssueRecord(import_batch_id=batch.id, issue_code="UNMAPPED_PAYROLL_COMPONENT", severity="critical", record_key=record.source_employee_key, evidence=dict(item), status="quarantined"))
                    quarantined += 1
                    continue
                session.add(PayrollLineRecord(id=uuid4(), payroll_run_id=run.id, source_record_id=record.id, employee_no=employee.employee_no, code=str(item["component_code"]), title=str(item["component_code"]), amount=item["amount"], currency_code=run.currency_code, kind=str(item["kind"]), taxable=False, pensionable=False, insurable=False, rule_code=str(item["component_code"]), mapping_status="review_required", explanation=f"source_column={item['source_column']}; source_record={record.id}"))
                created += 1
        if quarantined or created == 0:
            raise HTTPException(status_code=423, detail="source projection is not calculation-ready; unresolved quarantine/mapping findings remain")
        run.source_import_batch_id = batch.id
        run.status = transition(PayrollStatus(run.status), PayrollStatus.DATA_RECEIVED).value
        append_audit_event(event_type="import.batch.projected", entity_type="import_batch", entity_id=batch.id, actor_id=principal.user_id, payload={"payroll_run_id": str(run.id), "created_lines": created, "quarantined_components": quarantined, "next_status": run.status}, reason="project validated source import into payroll run", session=session)
        session.commit()
        return {"import_batch_id": str(batch.id), "payroll_run_id": str(run.id), "created_lines": created, "quarantined_components": quarantined, "mapping_status": "review_required", "payroll_run_status": run.status}
