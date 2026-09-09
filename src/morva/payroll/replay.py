from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import PayrollArtifactRecord, PayslipLineRecord
from morva.persistence.models import PersonnelSnapshotRecord
from morva.payroll import PayrollCalculator, PayrollLine


class ReplayMismatch(RuntimeError):
    pass


def _validate_snapshot(session: Session, artifact: PayrollArtifactRecord) -> PersonnelSnapshotRecord:
    snapshot = session.get(PersonnelSnapshotRecord, artifact.personnel_snapshot_id)
    if snapshot is None:
        raise ReplayMismatch("historical personnel snapshot not found")
    if snapshot.employee_no != artifact.employee_no or snapshot.effective_period != artifact.period:
        raise ReplayMismatch("historical personnel snapshot identity does not match payroll artifact")
    if snapshot.snapshot_hash != artifact.personnel_snapshot_hash:
        raise ReplayMismatch("historical personnel snapshot hash does not match payroll artifact")
    return snapshot


def replay_artifact(session: Session, artifact_id: UUID) -> dict[str, object]:
    artifact = session.get(PayrollArtifactRecord, artifact_id)
    if artifact is None:
        raise ReplayMismatch("payroll artifact not found")
    _validate_snapshot(session, artifact)

    rows = session.scalars(
        select(PayslipLineRecord)
        .where(PayslipLineRecord.artifact_id == artifact.id)
        .order_by(PayslipLineRecord.line_sequence.asc())
    ).all()
    if not rows:
        raise ReplayMismatch("payroll artifact has no persisted payslip lines")
    lines = [
        PayrollLine(
            code=row.code,
            title=row.title,
            amount=Decimal(row.amount),
            kind=row.kind,
            taxable=row.taxable,
            pensionable=row.pensionable,
            insurable=row.insurable,
            rule_code=row.rule_code,
            explanation=row.explanation,
        )
        for row in rows
    ]
    calculation = PayrollCalculator().calculate(
        employee_no=artifact.employee_no,
        period=artifact.period,
        ruleset_version=artifact.rule_pack_version,
        lines=lines,
    )
    replay_output = {
        "gross": str(calculation.result.gross),
        "deductions": str(calculation.result.deductions),
        "net": str(calculation.result.net),
        "fingerprint": calculation.fingerprint,
    }
    replay_hash = hashlib.sha256(
        json.dumps(replay_output, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if replay_hash != artifact.output_hash:
        raise ReplayMismatch("historical payroll replay does not match persisted output hash")
    return {
        "artifact_id": str(artifact.id),
        "employee_no": artifact.employee_no,
        "period": artifact.period,
        "personnel_snapshot_id": str(artifact.personnel_snapshot_id),
        "personnel_snapshot_hash": artifact.personnel_snapshot_hash,
        "rule_pack_version": artifact.rule_pack_version,
        "matches": True,
        "output_hash": replay_hash,
        "gross": replay_output["gross"],
        "deductions": replay_output["deductions"],
        "net": replay_output["net"],
    }
