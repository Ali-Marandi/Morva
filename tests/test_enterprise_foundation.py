from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from morva.integrations.outbox import enqueue, record_inbox
from morva.persistence.enterprise_models import Base, InboxMessageRecord, OutboxMessageRecord, PayrollArtifactRecord, PayslipLineRecord
from morva.security.field_crypto import decrypt, encrypt, lookup_hmac


def test_field_encryption_round_trip_and_keyed_lookup() -> None:
    token = encrypt("0123456789", key_material="test-field-key")
    assert token != "0123456789"
    assert decrypt(token, key_material="test-field-key") == "0123456789"
    assert lookup_hmac("0123456789", key_material="test-lookup-key") == lookup_hmac("0123456789", key_material="test-lookup-key")
    assert lookup_hmac("0123456789", key_material="test-lookup-key") != lookup_hmac("0123456788", key_material="test-lookup-key")


def test_outbox_and_inbox_are_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = enqueue(session, operation="submit_payment_batch", provider="bank", correlation_id="corr-1", idempotency_key="idem-123456", payload={"amount": "100.00"})
        second = enqueue(session, operation="submit_payment_batch", provider="bank", correlation_id="corr-2", idempotency_key="idem-123456", payload={"amount": "999.00"})
        assert first.id == second.id
        inbox1 = record_inbox(session, provider="bank", external_id="ext-1", correlation_id="corr-1", payload={"status": "accepted"})
        inbox2 = record_inbox(session, provider="bank", external_id="ext-1", correlation_id="corr-2", payload={"status": "accepted"})
        assert inbox1.id == inbox2.id
        session.commit()
        assert session.scalar(select(OutboxMessageRecord).where(OutboxMessageRecord.id == first.id)) is not None
        assert session.scalar(select(InboxMessageRecord).where(InboxMessageRecord.id == inbox1.id)) is not None


def test_payroll_artifact_has_exact_decimal_amounts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        artifact = PayrollArtifactRecord(
            id=uuid4(), payroll_run_id=uuid4(), employee_no="E-1", period="1405-05", currency_code="IRR",
            personnel_snapshot_id=uuid4(), personnel_snapshot_hash="a" * 64, rule_pack_version="verified-1",
            rule_pack_hash="b" * 64, input_hash="c" * 64, output_hash="d" * 64,
            gross=Decimal("100.10"), deductions=Decimal("10.01"), net=Decimal("90.09"), status="calculated",
        )
        session.add(artifact)
        session.commit()
        loaded = session.get(PayrollArtifactRecord, artifact.id)
        assert loaded is not None
        assert Decimal(loaded.net) == Decimal("90.09")
