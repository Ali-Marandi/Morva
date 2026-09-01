from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.payroll.calculator import PayrollCalculation, PayrollCalculator
from morva.payroll.models import PayrollLine
from morva.persistence.models import EmployeePayrollSnapshotRecord, PayrollLineRecord, PayrollRunRecord, RuleSetApprovalRecord
from morva.security.auth import Permission, Principal


class PayrollRunBlockedError(RuntimeError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def snapshot_hash(*, employee_no: str, period: str, organization_scope: str, source_manifest_hash: str, payload: dict) -> str:
    material = {
        "employee_no": employee_no,
        "period": period,
        "organization_scope": organization_scope,
        "source_manifest_hash": source_manifest_hash,
        "payload": payload,
    }
    return sha256(canonical_json(material).encode("utf-8")).hexdigest()


def add_snapshot(
    session: Session,
    *,
    run_id: UUID,
    employee_no: str,
    payload: dict,
    source_manifest_hash: str,
    principal: Principal,
) -> EmployeePayrollSnapshotRecord:
    principal.require(Permission.CALCULATE_PAYROLL)
    run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one()
    if run.status != "draft":
        raise PayrollRunBlockedError("snapshots may only be admitted while payroll run is draft")
    if run.organization_scope != principal.organization_scope and principal.organization_scope != "global":
        raise PermissionError("organization scope mismatch")
    if run.source_manifest_hash and run.source_manifest_hash != source_manifest_hash:
        raise PayrollRunBlockedError("source manifest hash mismatch for payroll run")
    if run.source_manifest_hash is None:
        run.source_manifest_hash = source_manifest_hash
    if run.period != payload.get("period", run.period):
        raise PayrollRunBlockedError("snapshot period does not match payroll run")
    if payload.get("employee_no") not in (None, employee_no):
        raise PayrollRunBlockedError("snapshot employee number mismatch")
    payload = dict(payload)
    payload["employee_no"] = employee_no
    digest = snapshot_hash(
        employee_no=employee_no,
        period=run.period,
        organization_scope=run.organization_scope,
        source_manifest_hash=source_manifest_hash,
        payload=payload,
    )
    existing = session.execute(
        select(EmployeePayrollSnapshotRecord).where(
            EmployeePayrollSnapshotRecord.payroll_run_id == run_id,
            EmployeePayrollSnapshotRecord.employee_no == employee_no,
        )
    ).scalar_one_or_none()
    if existing:
        if existing.snapshot_hash != digest:
            raise PayrollRunBlockedError("snapshot already exists with a different immutable payload")
        return existing
    record = EmployeePayrollSnapshotRecord(
        payroll_run_id=run_id,
        employee_no=employee_no,
        organization_scope=run.organization_scope,
        period=run.period,
        source_manifest_hash=source_manifest_hash,
        snapshot_hash=digest,
        payload=payload,
        created_by=principal.subject,
    )
    session.add(record)
    session.flush()
    return record


def admit_snapshots(session: Session, *, run_id: UUID, principal: Principal) -> int:
    principal.require(Permission.CALCULATE_PAYROLL)
    run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one()
    if run.status != "draft":
        raise PayrollRunBlockedError("snapshot admission is only allowed from draft")
    count = session.query(EmployeePayrollSnapshotRecord).filter(EmployeePayrollSnapshotRecord.payroll_run_id == run_id).count()
    if count == 0 or not run.source_manifest_hash:
        raise PayrollRunBlockedError("payroll run requires at least one snapshot and a source manifest hash")
    run.status = "data_received"
    run.version += 1
    session.flush()
    return count


def _lines_from_payload(payload: dict) -> tuple[PayrollLine, ...]:
    raw_lines = payload.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise PayrollRunBlockedError("snapshot must contain a non-empty lines array")
    lines: list[PayrollLine] = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise PayrollRunBlockedError("snapshot line must be an object")
        try:
            lines.append(
                PayrollLine(
                    code=str(raw["code"]),
                    title=str(raw["title"]),
                    amount=Decimal(str(raw["amount"])),
                    kind=str(raw["kind"]),
                    taxable=bool(raw.get("taxable", False)),
                    pensionable=bool(raw.get("pensionable", False)),
                    insurable=bool(raw.get("insurable", False)),
                    rule_code=raw.get("rule_code"),
                    explanation=raw.get("explanation"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise PayrollRunBlockedError(f"invalid snapshot payroll line: {exc}") from exc
    return tuple(lines)


def calculate_persisted_snapshot(
    session: Session,
    *,
    run_id: UUID,
    employee_no: str,
    principal: Principal,
    calculator: PayrollCalculator | None = None,
) -> PayrollCalculation:
    principal.require(Permission.CALCULATE_PAYROLL)
    run = session.execute(select(PayrollRunRecord).where(PayrollRunRecord.id == run_id).with_for_update()).scalar_one()
    if run.status not in {"data_received", "calculated"}:
        raise PayrollRunBlockedError(f"payroll run cannot be calculated from status {run.status}")
    approval = session.execute(
        select(RuleSetApprovalRecord).where(
            RuleSetApprovalRecord.version == run.ruleset_version,
            RuleSetApprovalRecord.status == "approved",
        )
    ).scalar_one_or_none()
    if approval is None:
        raise PayrollRunBlockedError("ruleset is not approved; legal payroll calculation remains fail-closed")
    if approval.population_scope not in {"global", run.organization_scope}:
        raise PayrollRunBlockedError("approved ruleset population scope does not cover payroll run")
    snapshot = session.execute(
        select(EmployeePayrollSnapshotRecord).where(
            EmployeePayrollSnapshotRecord.payroll_run_id == run_id,
            EmployeePayrollSnapshotRecord.employee_no == employee_no,
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise PayrollRunBlockedError("no persisted employee snapshot exists for payroll run")
    expected = snapshot_hash(
        employee_no=snapshot.employee_no,
        period=snapshot.period,
        organization_scope=snapshot.organization_scope,
        source_manifest_hash=snapshot.source_manifest_hash,
        payload=snapshot.payload,
    )
    if expected != snapshot.snapshot_hash or snapshot.source_manifest_hash != run.source_manifest_hash:
        raise PayrollRunBlockedError("persisted snapshot integrity or provenance check failed")
    period_year, period_month = (int(x) for x in run.period.split("-"))
    calculation = (calculator or PayrollCalculator()).calculate(
        employee_no=employee_no,
        period=date(period_year, period_month, 1),
        ruleset_version=run.ruleset_version,
        lines=_lines_from_payload(snapshot.payload),
    )
    for line in calculation.result.lines:
        session.add(
            PayrollLineRecord(
                payroll_run_id=run.id,
                employee_no=employee_no,
                code=line.code,
                title=line.title,
                amount=line.amount,
                kind=line.kind,
                rule_code=line.rule_code,
                explanation=line.explanation,
            )
        )
    run.status = "calculated"
    run.version += 1
    run.payroll_fingerprint = calculation.fingerprint
    session.flush()
    return calculation
