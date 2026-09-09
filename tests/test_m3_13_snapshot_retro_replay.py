from uuid import uuid4
from decimal import Decimal
from hashlib import sha256
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import Base, PayrollArtifactRecord, PayslipLineRecord
from morva.persistence.models import PersonnelSnapshotRecord
from morva.payroll import PayrollCalculator, PayrollLine
from morva.payroll.replay import ReplayMismatch, replay_artifact
from morva.payroll.retro import RetroMismatch, calculate_snapshot_driven_retro


def _snapshot(session: Session, employee_no: str, period: str, marker: str) -> PersonnelSnapshotRecord:
    snapshot = PersonnelSnapshotRecord(
        employee_no=employee_no,
        effective_period=period,
        effective_date=None,
        organization_unit_id="ORG-1",
        position_id="POS-1",
        employment_type="teacher",
        employment_status="active",
        source_hash=sha256(marker.encode()).hexdigest(),
        snapshot_hash=sha256(f"{employee_no}|{period}|{marker}".encode()).hexdigest(),
        order_numbers=[],
        components={"marker": marker},
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _artifact(session: Session, snapshot: PersonnelSnapshotRecord, *, run_marker: str, net: str) -> PayrollArtifactRecord:
    artifact = PayrollArtifactRecord(
        id=uuid4(),
        payroll_run_id=uuid4(),
        employee_no=snapshot.employee_no,
        period=snapshot.effective_period,
        personnel_snapshot_id=snapshot.id,
        personnel_snapshot_hash=snapshot.snapshot_hash,
        rule_pack_version="test-pack",
        rule_pack_hash="r" * 64,
        input_hash=sha256(run_marker.encode()).hexdigest(),
        output_hash="pending",
        gross=Decimal(net) + Decimal("100"),
        deductions=Decimal("100"),
        net=Decimal(net),
    )
    session.add(artifact)
    session.flush()
    return artifact


def _output_hash(employee_no: str, period: str, amount: str) -> str:
    calculation = PayrollCalculator().calculate(
        employee_no=employee_no,
        period=period,
        ruleset_version="test-pack",
        lines=[PayrollLine(code="BASE", title="Base", amount=Decimal(amount), kind="earning")],
    )
    output = {
        "gross": str(calculation.result.gross),
        "deductions": str(calculation.result.deductions),
        "net": str(calculation.result.net),
        "fingerprint": calculation.fingerprint,
    }
    return sha256(json.dumps(output, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def test_replay_requires_historical_snapshot_and_hash() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        snapshot = _snapshot(session, "E-1", "1405-05", "frozen")
        artifact = _artifact(session, snapshot, run_marker="run", net="1000")
        artifact.output_hash = _output_hash("E-1", "1405-05", "1000")
        session.add(
            PayslipLineRecord(
                artifact_id=artifact.id,
                line_sequence=1,
                employee_no="E-1",
                code="BASE",
                title="Base",
                amount=Decimal("1000"),
                kind="earning",
            )
        )
        session.commit()
        result = replay_artifact(session, artifact.id)
        assert result["matches"] is True
        assert result["personnel_snapshot_hash"] == snapshot.snapshot_hash

        artifact.personnel_snapshot_hash = "x" * 64
        with pytest.raises(ReplayMismatch, match="snapshot hash"):
            replay_artifact(session, artifact.id)


def test_snapshot_retro_requires_the_same_frozen_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        snapshot = _snapshot(session, "E-2", "1405-05", "frozen")
        old_artifact = _artifact(session, snapshot, run_marker="old", net="1000")
        new_artifact = _artifact(session, snapshot, run_marker="new", net="1125")
        session.commit()
        result = calculate_snapshot_driven_retro(
            session,
            employee_no="E-2",
            original_artifacts={"1405-05": old_artifact.id},
            revised_artifacts={"1405-05": new_artifact.id},
        )
        assert result.snapshot_driven is True
        assert result.net_difference == Decimal("125")
        assert result.periods[0].original_snapshot_id == snapshot.id
        assert result.periods[0].revised_snapshot_id == snapshot.id

        with pytest.raises(RetroMismatch, match="both original and revised"):
            calculate_snapshot_driven_retro(
                session,
                employee_no="E-2",
                original_artifacts={"1405-06": old_artifact.id},
                revised_artifacts={},
            )
