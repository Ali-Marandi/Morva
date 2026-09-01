from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor_id: str | None
    payload: Mapping[str, object]
    previous_hash: str | None = None

    def digest(self) -> str:
        canonical = json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type,
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "actor_id": self.actor_id,
                "payload": self.payload,
                "previous_hash": self.previous_hash,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


class AuditChain:
    def __init__(self) -> None:
        self._last_hash: str | None = None

    def append(self, event: AuditEvent) -> AuditEvent:
        if event.previous_hash not in {None, self._last_hash}:
            raise ValueError("audit event is not linked to the current chain")
        linked = AuditEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            actor_id=event.actor_id,
            payload=event.payload,
            previous_hash=self._last_hash,
        )
        self._last_hash = linked.digest()
        return linked

    @property
    def last_hash(self) -> str | None:
        return self._last_hash
