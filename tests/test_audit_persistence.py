from morva.audit.persistence import append_audit_event, verify_audit_chain
from morva.persistence.models import AuditEventRecord


def test_audit_chain_is_hash_linked(db_session):
    first = append_audit_event(
        db_session,
        event_type="TEST_CREATED",
        entity_type="Test",
        entity_id="1",
        actor_id="tester",
        payload={"amount": "100"},
    )
    second = append_audit_event(
        db_session,
        event_type="TEST_UPDATED",
        entity_type="Test",
        entity_id="1",
        actor_id="reviewer",
        payload={"amount": "125"},
    )
    db_session.commit()

    assert first.sequence_no == 1
    assert second.sequence_no == 2
    assert second.previous_hash == first.current_hash
    assert verify_audit_chain(db_session) == (True, None)


def test_audit_chain_detects_tampering(db_session):
    append_audit_event(
        db_session,
        event_type="TEST_CREATED",
        entity_type="Test",
        entity_id="1",
        payload={"value": "10"},
    )
    db_session.commit()

    event = db_session.query(AuditEventRecord).one()
    event.payload = {"value": "999"}
    db_session.commit()

    valid, reason = verify_audit_chain(db_session)
    assert valid is False
    assert reason == "audit hash mismatch at sequence 1"
