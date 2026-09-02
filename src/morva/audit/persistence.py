from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from typing import Mapping
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.chain import AuditEvent
from morva.persistence.database import SessionLocal
from morva.persistence.models import AuditChainHeadRecord, AuditEventRecord


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


def _append_with_session(
    session: Session,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | UUID,
    actor_id: str | None,
    payload: Mapping[str, object],
    reason: str | None = None,
) -> AuditEventRecord:
    head = session.execute(
        select(AuditChainHeadRecord).where(AuditChainHeadRecord.id == 1).with_for_update()
    ).scalar_one_or_none()
    if head is None:
        head = AuditChainHeadRecord(id=1, sequence_no=0, digest=None)
        session.add(head)
        session.flush()

    event = AuditEvent(
        event_id=str(uuid4()),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_id=actor_id,
        payload=dict(payload),
        previous_hash=head.digest,
    )
    record = AuditEventRecord(
        event_id=event.event_id,
        sequence_no=head.sequence_no + 1,
        event_type=event.event_type,
        actor_id=event.actor_id,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        payload=dict(event.payload),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        reason=reason,
        previous_hash=event.previous_hash,
        digest=_digest(event),
    )
    session.add(record)
    head.sequence_no = record.sequence_no
    head.digest = record.digest
    session.flush()
    return record


def append_audit_event(
    *,
    event_type: str,
    entity_type: str,
    entity_id: str | UUID,
    actor_id: str | None,
    payload: Mapping[str, object],
    reason: str | None = None,
    session: Session | None = None,
) -> AuditEventRecord:
    """Append an audit event; pass the business transaction session for atomic audit."""
    if session is not None:
        return _append_with_session(
            session,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            payload=payload,
            reason=reason,
        )
    with SessionLocal() as own_session:
        record = _append_with_session(
            own_session,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            payload=payload,
            reason=reason,
        )
        own_session.commit()
        own_session.refresh(record)
        return record


def verify_audit_chain() -> None:
    """Raise if the persistent audit chain has a gap, mutation, or incorrect head."""
    with SessionLocal() as session:
        events = session.scalars(
            select(AuditEventRecord).order_by(AuditEventRecord.sequence_no.asc())
        ).all()
        previous_hash: str | None = None
        for expected_sequence, record in enumerate(events, start=1):
            if record.sequence_no != expected_sequence:
                raise RuntimeError("audit sequence gap detected")
            event = AuditEvent(
                event_id=record.event_id,
                event_type=record.event_type,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                actor_id=record.actor_id,
                payload=record.payload,
                previous_hash=record.previous_hash,
            )
            if record.previous_hash != previous_hash or record.digest != _digest(event):
                raise RuntimeError("audit chain integrity verification failed")
            previous_hash = record.digest

        head = session.get(AuditChainHeadRecord, 1)
        if head is None:
            if events:
                raise RuntimeError("audit chain head is missing")
            return
        if head.sequence_no != len(events) or head.digest != previous_hash:
            raise RuntimeError("audit chain head does not match event ledger")
