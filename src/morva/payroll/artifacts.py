from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Iterable
from uuid import UUID, uuid4

from sqlalchemy import select

from morva.persistence.database import SessionLocal
from morva.persistence.enterprise_models import PayrollArtifactRecord, PayslipLineRecord
from morva.persistence.models import PayrollLineRecord, PayrollRunRecord, PersonnelSnapshotRecord
from morva.payroll import PayrollCalculator, PayrollLine


class PayrollArtifactError(RuntimeError):
    pass


def _canonical_result_payload(employee_no: str, period: str, ruleset_version: str, snapshot_hash: str, lines: Iterable[PayrollLine]) -> str:
    payload = {
        "employee_no": employee_no,
        "period": period,
        "ruleset_version": ruleset_version,
        "snapshot_hash": snapshot_hash,
        "lines": [
            {
                "code": line.code,
                "title": line.title,
                "amount": str(line.amount),
                "kind": line.kind,
                "taxable": line.taxable,
                "pensionable": line.pensionable,
                "insurable": line.insurable,
                "rule_code": line.rule_code,
            }
            for line in lines
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def materialize_run_artifacts(run_id: UUID) -> int:
    """Persist employee-level deterministic results; never overwrites an existing artifact."""
    calculator = PayrollCalculator()
    with SessionLocal() as session:
        run = session.get(PayrollRunRecord, run_id)
        if run is None:
            raise PayrollArtifactError("payroll run not found")
        if not run.ruleset_hash:
            raise PayrollArtifactError("payroll run has no immutable rule-pack hash")
        lines = session.scalars(select(PayrollLineRecord).where(PayrollLineRecord.payroll_run_id == run.id)).all()
        if not lines:
            raise PayrollArtifactError("payroll run has no payroll lines")
        employees = sorted({line.employee_no for line in lines})
        created = 0
        for employee_no in employees:
            snapshot = session.scalar(
                select(PersonnelSnapshotRecord).where(
                    PersonnelSnapshotRecord.employee_no == employee_no,
                    PersonnelSnapshotRecord.effective_period == run.period,
                )
            )
            if snapshot is None:
                raise PayrollArtifactError(f"personnel snapshot missing for {employee_no}")
            existing = session.scalar(
                select(PayrollArtifactRecord).where(
                    PayrollArtifactRecord.payroll_run_id == run.id,
                    PayrollArtifactRecord.employee_no == employee_no,
                )
            )
            if existing is not None:
                continue
            employee_lines = [
                PayrollLine(
                    code=line.code,
                    title=line.title,
                    amount=Decimal(line.amount),
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
            calculation = calculator.calculate(
                employee_no=employee_no,
                period=run.period,
                ruleset_version=run.ruleset_version,
                lines=employee_lines,
            )
            canonical = _canonical_result_payload(employee_no, run.period, run.ruleset_version, snapshot.snapshot_hash, employee_lines)
            input_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            output_hash = hashlib.sha256(
                json.dumps(
                    {"gross": str(calculation.result.gross), "deductions": str(calculation.result.deductions), "net": str(calculation.result.net), "fingerprint": calculation.fingerprint},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            artifact = PayrollArtifactRecord(
                id=uuid4(), payroll_run_id=run.id, employee_no=employee_no, period=run.period,
                currency_code=run.currency_code, personnel_snapshot_id=snapshot.id,
                personnel_snapshot_hash=snapshot.snapshot_hash, rule_pack_version=run.ruleset_version,
                rule_pack_hash=run.ruleset_hash, input_hash=input_hash, output_hash=output_hash,
                gross=calculation.result.gross, deductions=calculation.result.deductions, net=calculation.result.net,
                status="calculated",
            )
            session.add(artifact)
            session.flush()
            for line in calculation.result.lines:
                source = next((item for item in lines if item.employee_no == employee_no and item.code == line.code), None)
                session.add(
                    PayslipLineRecord(
                        id=uuid4(), artifact_id=artifact.id, employee_no=employee_no, code=line.code,
                        title=line.title, amount=line.amount, currency_code=run.currency_code, kind=line.kind,
                        taxable=line.taxable, pensionable=line.pensionable, insurable=line.insurable,
                        rule_code=line.rule_code,
                        source_record_id=source.source_record_id if source else None,
                        explanation=line.explanation,
                    )
                )
            created += 1
        session.commit()
        return created
