from decimal import Decimal
from uuid import uuid4

import pytest

from morva.payroll.persisted_run import PayrollRunBlockedError, add_snapshot, calculate_persisted_snapshot, snapshot_hash
from morva.payroll.run_service import create_run, transition
from morva.persistence.models import RuleSetApprovalRecord
from morva.security.auth import Permission, Principal


ALL_PERMISSIONS = frozenset(permission.value for permission in Permission)


def principal(subject: str = "calculator") -> Principal:
    return Principal(
        subject=subject,
        role="ministry_finance",
        organization_unit_id="global",
        mfa_verified=True,
        permissions=ALL_PERMISSIONS,
    )


def test_snapshot_is_idempotent_and_immutable(db_session):
    run = create_run(
        db_session,
        period="1405-06",
        ruleset_version="legal-v1",
        principal=principal(),
        organization_scope="global",
    )
    source_hash = "a" * 64
    payload = {"employee_no": "E-1", "lines": [{"code": "BASE", "title": "Base", "amount": "1000", "kind": "earning"}]}
    first = add_snapshot(
        db_session,
        run_id=run.id,
        employee_no="E-1",
        payload=payload,
        source_manifest_hash=source_hash,
        principal=principal(),
    )
    second = add_snapshot(
        db_session,
        run_id=run.id,
        employee_no="E-1",
        payload=payload,
        source_manifest_hash=source_hash,
        principal=principal(),
    )
    assert first.id == second.id
    assert first.snapshot_hash == snapshot_hash(
        employee_no="E-1",
        period="1405-06",
        organization_scope="global",
        source_manifest_hash=source_hash,
        payload=payload,
    )
    with pytest.raises(PayrollRunBlockedError):
        add_snapshot(
            db_session,
            run_id=run.id,
            employee_no="E-1",
            payload={"employee_no": "E-1", "lines": [{"code": "BASE", "title": "Base", "amount": "2000", "kind": "earning"}]},
            source_manifest_hash=source_hash,
            principal=principal(),
        )


def test_persisted_calculation_requires_approved_ruleset(db_session):
    run = create_run(
        db_session,
        period="1405-06",
        ruleset_version="unapproved-v1",
        principal=principal(),
        organization_scope="global",
    )
    add_snapshot(
        db_session,
        run_id=run.id,
        employee_no="E-2",
        payload={"employee_no": "E-2", "lines": [{"code": "BASE", "title": "Base", "amount": "1250.00", "kind": "earning"}]},
        source_manifest_hash="b" * 64,
        principal=principal(),
    )
    transition(
        db_session,
        run_id=run.id,
        target_status="data_received",
        principal=principal(),
        reason="test admission",
        correlation_id=str(uuid4()),
    )
    with pytest.raises(PayrollRunBlockedError, match="ruleset is not approved"):
        calculate_persisted_snapshot(db_session, run_id=run.id, employee_no="E-2", principal=principal())


def test_approved_snapshot_calculates_from_persisted_values(db_session):
    run = create_run(
        db_session,
        period="1405-06",
        ruleset_version="approved-v1",
        principal=principal(),
        organization_scope="global",
    )
    db_session.add(RuleSetApprovalRecord(version="approved-v1", status="approved", population_scope="global", legal_manifest_hash="c" * 64, approved_by="legal-review"))
    add_snapshot(
        db_session,
        run_id=run.id,
        employee_no="E-3",
        payload={
            "employee_no": "E-3",
            "lines": [
                {"code": "BASE", "title": "Base", "amount": "2000.50", "kind": "earning"},
                {"code": "LOAN", "title": "Loan", "amount": "100.50", "kind": "deduction"},
            ],
        },
        source_manifest_hash="d" * 64,
        principal=principal(),
    )
    transition(db_session, run_id=run.id, target_status="data_received", principal=principal(), reason="test admission", correlation_id=None)
    result = calculate_persisted_snapshot(db_session, run_id=run.id, employee_no="E-3", principal=principal())
    assert result.result.gross == Decimal("2000.50")
    assert result.result.deductions == Decimal("100.50")
    assert result.result.net == Decimal("1900.00")
