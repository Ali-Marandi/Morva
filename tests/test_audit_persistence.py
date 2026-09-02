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
        payload={"safe": True},
        reason="test",
    )
    assert first.sequence_no + 1 == second.sequence_no
    assert second.previous_hash == first.digest
    verify_audit_chain()
