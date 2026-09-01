from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping
from uuid import UUID, uuid4

from sqlalchemy import func, select

from morva.audit.chain import AuditEvent
from morva.persistence.database import SessionLocal
from morva.persistence.models import AuditEventRecord


def _digest(event: AuditEvent) -> str:
    canonical = json.dumps(
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "actor_id": event.actor_id,
            "payload": event.payload,
            "previous_hash": event.previous_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def append_audit_event(
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | UUID,
    actor_id: str | None,
    payload: Mapping[str, object],
    reason: str | None = None,
) -> AuditEventRecord:
    """Persist one append-only audit event and link it to the previous digest."""
    with SessionLocal() as session:
        previous = session.scalar(select(AuditEventRecord).order_by(AuditEventRecord.sequence_no.desc()).limit(1))
        sequence_no = (previous.sequence_no + 1) if previous else 1
        previous_hash = previous.digest if previous else None
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_id=actor_id,
            payload=dict(payload),
            previous_hash=previous_hash,
        )
        record = AuditEventRecord(
            sequence_no=sequence_no,
            event_type=event.event_type,
            actor_id=event.actor_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            payload=dict(event.payload),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            reason=reason,
            previous_hash=previous_hash,
            digest=_digest(event),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
