from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.models import AuditChainHeadRecord, AuditEventRecord


_GENESIS = ""


def _canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)


def _event_hash(
    *,
    sequence_no: int,
    event_type: str,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    correlation_id: str | None,
    payload: dict[str, Any],
    previous_hash: str,
    reason: str | None,
    created_at: datetime,
) -> str:
    material = {
        "sequence_no": sequence_no,
        "event_type": event_type,
        "actor_id": actor_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "correlation_id": correlation_id,
        "payload": payload,
        "previous_hash": previous_hash,
        "reason": reason,
        "created_at": created_at.isoformat(),
    }
    return hashlib.sha256(_canonical_payload(material).encode("utf-8")).hexdigest()


def _get_or_create_head(session: Session) -> AuditChainHeadRecord:
    head = session.execute(
        select(AuditChainHeadRecord).where(AuditChainHeadRecord.id == 1).with_for_update()
    ).scalar_one_or_none()
    if head is None:
        head = AuditChainHeadRecord(id=1, last_sequence_no=0, last_hash=_GENESIS)
        session.add(head)
        session.flush()
    return head


def append_audit_event(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    payload: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditEventRecord:
    """Append a hash-linked audit event inside the caller's transaction."""
    head = _get_or_create_head(session)
    sequence_no = head.last_sequence_no + 1
    previous_hash = head.last_hash or _GENESIS
    created_at = datetime.utcnow()
    event_payload = payload or {}
    current_hash = _event_hash(
        sequence_no=sequence_no,
        event_type=event_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        payload=event_payload,
        previous_hash=previous_hash,
        reason=reason,
        created_at=created_at,
    )
    event = AuditEventRecord(
        sequence_no=sequence_no,
        event_type=event_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        correlation_id=correlation_id,
        payload=event_payload,
        previous_hash=previous_hash or None,
        current_hash=current_hash,
        created_at=created_at,
        reason=reason,
    )
    session.add(event)
    head.last_sequence_no = sequence_no
    head.last_hash = current_hash
    head.updated_at = created_at
    session.flush()
    return event


def verify_audit_chain(session: Session) -> tuple[bool, str | None]:
    """Recompute the full chain and compare it with the persisted head."""
    events = session.execute(
        select(AuditEventRecord).order_by(AuditEventRecord.sequence_no.asc())
    ).scalars().all()
    previous_hash = _GENESIS
    expected_sequence = 1
    for event in events:
        if event.sequence_no != expected_sequence:
            return False, f"audit sequence gap at {event.sequence_no}; expected {expected_sequence}"
        if (event.previous_hash or _GENESIS) != previous_hash:
            return False, f"audit previous-hash mismatch at sequence {event.sequence_no}"
        expected = _event_hash(
            sequence_no=event.sequence_no,
            event_type=event.event_type,
            actor_id=event.actor_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            correlation_id=event.correlation_id,
            payload=event.payload,
            previous_hash=previous_hash,
            reason=event.reason,
            created_at=event.created_at,
        )
        if event.current_hash != expected:
            return False, f"audit hash mismatch at sequence {event.sequence_no}"
        previous_hash = event.current_hash
        expected_sequence += 1

    head = session.execute(select(AuditChainHeadRecord).where(AuditChainHeadRecord.id == 1)).scalar_one_or_none()
    if head is not None and (head.last_sequence_no, head.last_hash or _GENESIS) != (len(events), previous_hash):
        return False, "audit chain head does not match event tail"
    return True, None
