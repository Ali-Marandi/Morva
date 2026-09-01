from morva.payroll.run_service import transition
from morva.persistence.models import PayrollRunRecord
from morva.security.auth import Permission, Principal


def principal(subject: str, role: str = "district_finance") -> Principal:
    return Principal(
        subject=subject,
        role=role,
        organization_unit_id="U-1",
        mfa_verified=True,
        permissions=frozenset(permission.value for permission in Permission),
    )


def test_approval_is_not_self_approval(db_session):
    run = PayrollRunRecord(
        period="1405-05",
        ruleset_version="verified-test",
        status="reviewed",
        created_by="creator",
        organization_scope="U-1",
    )
    db_session.add(run)
    db_session.commit()

    try:
        transition(
            db_session,
            run_id=run.id,
            target_status="approved",
            principal=principal("creator"),
            reason="same actor",
            correlation_id="c-1",
        )
    except PermissionError as exc:
        assert "separation of duties" in str(exc)
    else:
        raise AssertionError("creator must not approve the same payroll run")


def test_valid_lifecycle_transition_records_actor(db_session):
    run = PayrollRunRecord(
        period="1405-05",
        ruleset_version="verified-test",
        status="draft",
        created_by="creator",
        organization_scope="U-1",
    )
    db_session.add(run)
    db_session.commit()

    result = transition(
        db_session,
        run_id=run.id,
        target_status="data_received",
        principal=principal("importer"),
        reason="source batch validated",
        correlation_id="c-2",
    )
    assert result.to_status == "data_received"
    assert result.version == 2
