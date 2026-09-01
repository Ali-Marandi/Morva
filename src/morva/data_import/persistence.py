from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.data_import.models import ImportRecord, ImportReport
from morva.persistence.models import (
    EmployeeRecord,
    ImportBatchRecord,
    ImportIssueRecord,
    PayrollLineRecord,
    PayrollRunRecord,
    PersonnelSnapshotRecord,
)


def _sha256(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _period_start(period: str) -> date:
    year, month = (int(part) for part in period.split("-", 1))
    return date(year, month, 1)


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
    payroll_records: list[ImportRecord],
) -> ImportBatchRecord:
    """Persist an import as an auditable batch. Payroll lines are created only from the payroll source."""
    if report.critical_exception_count:
        raise ValueError("critical import exceptions must be quarantined before materialization")

    duplicate = session.scalar(
        select(ImportBatchRecord).where(
            ImportBatchRecord.period == period,
            ImportBatchRecord.source_name == source_name,
            ImportBatchRecord.file_sha256 == file_sha256,
        )
    )
    if duplicate:
        raise ValueError("identical import batch already exists")

    batch = ImportBatchRecord(
        source_name=source_name,
        template_version=template_version,
        period=period,
        owner=owner,
        file_sha256=file_sha256,
        status="validated",
        provenance=dict(provenance),
    )
    session.add(batch)
    session.flush()

    for exception in report.exceptions:
        issue = ImportIssueRecord(
            import_batch_id=batch.id,
            issue_code=exception.code,
            severity=exception.severity,
            record_key=exception.employee_key,
            evidence={
                "expected": str(exception.expected),
                "actual": str(exception.actual),
                "delta": str(exception.delta),
                "source": exception.source,
                "details": exception.details,
            },
            status="quarantined",
        )
        session.add(issue)

    for record in payroll_records:
        payload = record.payload
        employee_no = payload["employee_key"]
        employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
        if employee is None:
            session.add(
                ImportIssueRecord(
                    import_batch_id=batch.id,
                    issue_code="EMPLOYEE_MASTER_MISSING",
                    severity="critical",
                    record_key=employee_no,
                    evidence={"source": record.source},
                    status="quarantined",
                )
            )
            continue

        line_payload = {
            "employee_no": employee_no,
            "gross": payload.get("gross", "0"),
            "deductions": payload.get("deductions", "0"),
            "net": payload.get("net", "0"),
        }
        snapshot_hash = _sha256(
            {
                "employee_no": employee_no,
                "period": period,
                "organization_unit_id": employee.organization_unit_id,
                "position_id": employee.position_id,
                "employment_type": employee.employment_type,
                "status": employee.status,
                "source": record.source,
                "source_hash": file_sha256,
            }
        )
        snapshot = PersonnelSnapshotRecord(
            employee_no=employee_no,
            effective_period=period,
            effective_date=_period_start(period),
            organization_unit_id=employee.organization_unit_id,
            position_id=employee.position_id,
            employment_type=employee.employment_type,
            employment_status=employee.status,
            source_import_batch_id=batch.id,
            source_hash=file_sha256,
            snapshot_hash=snapshot_hash,
            order_numbers=[],
            components={"gross": line_payload["gross"], "deductions": line_payload["deductions"], "net": line_payload["net"]},
        )
        existing_snapshot = session.scalar(
            select(PersonnelSnapshotRecord).where(
                PersonnelSnapshotRecord.employee_no == employee_no,
                PersonnelSnapshotRecord.effective_period == period,
            )
        )
        if existing_snapshot and existing_snapshot.snapshot_hash != snapshot_hash:
            raise ValueError(f"immutable personnel snapshot conflict for {employee_no} / {period}")
        if not existing_snapshot:
            session.add(snapshot)

        # Materialized source totals are control lines; their semantic classification is deliberately explicit.
        session.add_all(
            [
                PayrollLineRecord(
                    payroll_run_id=UUID(int=0),
                    employee_no=employee_no,
                    code="SOURCE_GROSS",
                    title="Imported gross total",
                    amount=line_payload["gross"],
                    currency_code="IRR",
                    kind="earning",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    rule_code="IMPORT_CONTROL",
                    explanation="Source-control total; not a legal payroll component.",
                ),
                PayrollLineRecord(
                    payroll_run_id=UUID(int=0),
                    employee_no=employee_no,
                    code="SOURCE_DEDUCTIONS",
                    title="Imported deductions total",
                    amount=line_payload["deductions"],
                    currency_code="IRR",
                    kind="deduction",
                    taxable=False,
                    pensionable=False,
                    insurable=False,
                    rule_code="IMPORT_CONTROL",
                    explanation="Source-control total; not a legal payroll component.",
                ),
            ]
        )

    batch.status = "quarantined" if session.scalar(
        select(ImportIssueRecord).where(
            ImportIssueRecord.import_batch_id == batch.id,
            ImportIssueRecord.severity == "critical",
        )
    ) else "ready"
    session.flush()
    append_audit_event(
        event_type="import.batch.materialized",
        entity_type="import_batch",
        entity_id=batch.id,
        actor_id=owner,
        payload={"period": period, "source_name": source_name, "file_sha256": file_sha256, "status": batch.status},
        reason="materialize validated import",
        session=session,
    )
    return batch
