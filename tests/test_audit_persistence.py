from morva.audit.persistence import append_audit_event, verify_audit_chain


def test_persistent_audit_chain_round_trip() -> None:
    first = append_audit_event(
        event_type="test.created",
        entity_type="test",
        entity_id="A1",
        actor_id="tester-1",
        payload={"safe": True},
        reason="test",
    )
    second = append_audit_event(
        event_type="test.updated",
        entity_type="test",
        entity_id="A1",
        actor_id="tester-2",
        payload={"before": {"status": "draft"}, "after": {"status": "approved"}},
        reason="test state change",
    )
    assert first.sequence_no + 1 == second.sequence_no
    assert second.previous_hash == first.digest
    assert second.actor_id == "tester-2"
    assert second.reason == "test state change"
    assert second.created_at is not None
    assert second.payload["before"] == {"status": "draft"}
    assert second.payload["after"] == {"status": "approved"}
    verify_audit_chain()
