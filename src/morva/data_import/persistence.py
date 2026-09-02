from __future__ import annotations

import hashlib
import json
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.data_import.models import ImportRecord, ImportReport
from morva.persistence.models import EmployeeRecord, ImportBatchRecord, ImportIssueRecord, ImportRecordRecord, PersonnelSnapshotRecord


def _sha256(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def materialize_import(
    session: Session,
    *,
    source_name: str,
    template_version: str,
    period: str,
    owner: str,
    file_sha256: str,
    provenance: Mapping[str, object],
    report: ImportReport,
    records: list[ImportRecord],
) -> ImportBatchRecord:
    """Persist the immutable source layer. It never fabricates payroll components."""
    duplicate = session.scalar(select(ImportBatchRecord).where(ImportBatchRecord.period == period, ImportBatchRecord.source_name == source_name, ImportBatchRecord.file_sha256 == file_sha256))
    if duplicate:
        raise ValueError("identical import batch already exists")

    batch = ImportBatchRecord(source_name=source_name, template_version=template_version, period=period, owner=owner, file_sha256=file_sha256, status="quarantined" if report.critical_exception_count else "ready", provenance=dict(provenance))
    session.add(batch)
    session.flush()

    for exception in report.exceptions:
        session.add(ImportIssueRecord(import_batch_id=batch.id, issue_code=exception.code, severity=exception.severity, record_key=exception.employee_key, evidence={"expected": str(exception.expected), "actual": str(exception.actual), "delta": str(exception.delta), "source": exception.source, "details": exception.details}, status="quarantined"))

    for record in records:
        record_hash = _sha256({"source": record.source, "period": record.period, "employee_key": record.employee_key, "payload": record.payload})
        session.add(ImportRecordRecord(import_batch_id=batch.id, source_name=record.source, period=record.period, source_employee_key=record.employee_key, record_hash=record_hash, payload=record.payload))

        employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.source_employee_key == record.employee_key))
        if employee is None:
            session.add(ImportIssueRecord(import_batch_id=batch.id, issue_code="EMPLOYEE_MASTER_MISSING", severity="critical", record_key=record.employee_key, evidence={"source": record.source, "period": record.period}, status="quarantined"))
            batch.status = "quarantined"
            continue
        if record.source != "گزارش لیست حقوق.xlsx":
            continue

        snapshot_hash = _sha256({"employee_no": employee.employee_no, "effective_period": period, "organization_unit_id": employee.organization_unit_id, "position_id": employee.position_id, "employment_type": employee.employment_type, "employment_status": employee.status, "source_record_hash": record_hash})
        existing_snapshot = session.scalar(select(PersonnelSnapshotRecord).where(PersonnelSnapshotRecord.employee_no == employee.employee_no, PersonnelSnapshotRecord.effective_period == period))
        if existing_snapshot:
            if existing_snapshot.snapshot_hash != snapshot_hash:
                raise ValueError(f"immutable personnel snapshot conflict for {employee.employee_no} / {period}")
        else:
            session.add(PersonnelSnapshotRecord(employee_no=employee.employee_no, effective_period=period, effective_date=None, organization_unit_id=employee.organization_unit_id, position_id=employee.position_id, employment_type=employee.employment_type, employment_status=employee.status, source_import_batch_id=batch.id, source_hash=record_hash, snapshot_hash=snapshot_hash, order_numbers=[], components={}))

    session.flush()
    append_audit_event(event_type="import.batch.materialized", entity_type="import_batch", entity_id=batch.id, actor_id=owner, payload={"period": period, "source_name": source_name, "file_sha256": file_sha256, "record_count": len(records), "status": batch.status}, reason="materialize immutable source import", session=session)
    return batch
