from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Iterable

from morva.runtime.authoritative_evidence_intake import AuthoritativeEvidenceRegistry


class EvidenceLifecycleError(ValueError):
    """Raised when an evidence supersession chain is unsafe."""


@dataclass(frozen=True, slots=True)
class EvidenceLifecycleLink:
    link_version: int
    predecessor_evidence_id: str
    successor_evidence_id: str
    linked_by: str
    linked_at: datetime
    reason: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.link_version != 1:
            raise EvidenceLifecycleError("unsupported evidence lifecycle link version")
        for name, value in (
            ("predecessor_evidence_id", self.predecessor_evidence_id),
            ("successor_evidence_id", self.successor_evidence_id),
            ("linked_by", self.linked_by),
            ("reason", self.reason),
        ):
            if not value.strip():
                raise EvidenceLifecycleError(f"{name} is required")
        if self.predecessor_evidence_id.strip() == self.successor_evidence_id.strip():
            raise EvidenceLifecycleError("evidence cannot supersede itself")
        if self.linked_at.tzinfo is None:
            raise EvidenceLifecycleError("linked_at must be timezone-aware")
        if len(self.fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in self.fingerprint.lower()
        ):
            raise EvidenceLifecycleError("fingerprint must be SHA-256")

    @property
    def expected_fingerprint(self) -> str:
        payload = {
            "link_version": self.link_version,
            "predecessor_evidence_id": self.predecessor_evidence_id.strip(),
            "successor_evidence_id": self.successor_evidence_id.strip(),
            "linked_by": self.linked_by.strip(),
            "linked_at": self.linked_at.astimezone(timezone.utc).isoformat(),
            "reason": self.reason.strip(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def verify(self) -> None:
        if self.fingerprint.lower() != self.expected_fingerprint:
            raise EvidenceLifecycleError("evidence lifecycle link fingerprint mismatch")

    def to_payload(self) -> dict[str, object]:
        return {
            "link_version": self.link_version,
            "predecessor_evidence_id": self.predecessor_evidence_id,
            "successor_evidence_id": self.successor_evidence_id,
            "linked_by": self.linked_by,
            "linked_at": self.linked_at.astimezone(timezone.utc).isoformat(),
            "reason": self.reason,
            "fingerprint": self.fingerprint.lower(),
        }


@dataclass(frozen=True, slots=True)
class EvidenceLifecycleAssessment:
    assessment_version: int
    repository: str
    checked_at: datetime
    registry_fingerprint: str
    link_fingerprints: tuple[str, ...]
    head_evidence_ids: tuple[str, ...]
    superseded_evidence_ids: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.assessment_version != 1:
            raise EvidenceLifecycleError("unsupported evidence lifecycle assessment version")
        if not self.repository.strip():
            raise EvidenceLifecycleError("repository is required")
        if self.checked_at.tzinfo is None:
            raise EvidenceLifecycleError("checked_at must be timezone-aware")
        for name, value in (
            ("registry_fingerprint", self.registry_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise EvidenceLifecycleError(f"{name} must be SHA-256")

    def to_payload(self) -> dict[str, object]:
        return {
            "assessment_version": self.assessment_version,
            "repository": self.repository,
            "checked_at": self.checked_at.isoformat(),
            "registry_fingerprint": self.registry_fingerprint,
            "link_fingerprints": list(self.link_fingerprints),
            "head_evidence_ids": list(self.head_evidence_ids),
            "superseded_evidence_ids": list(self.superseded_evidence_ids),
            "fingerprint": self.fingerprint,
        }


def build_lifecycle_link(
    *,
    predecessor_evidence_id: str,
    successor_evidence_id: str,
    linked_by: str,
    linked_at: datetime,
    reason: str,
) -> EvidenceLifecycleLink:
    draft = EvidenceLifecycleLink(
        link_version=1,
        predecessor_evidence_id=predecessor_evidence_id,
        successor_evidence_id=successor_evidence_id,
        linked_by=linked_by,
        linked_at=linked_at,
        reason=reason,
        fingerprint="0" * 64,
    )
    return EvidenceLifecycleLink(
        link_version=draft.link_version,
        predecessor_evidence_id=draft.predecessor_evidence_id,
        successor_evidence_id=draft.successor_evidence_id,
        linked_by=draft.linked_by,
        linked_at=draft.linked_at,
        reason=draft.reason,
        fingerprint=draft.expected_fingerprint,
    )


def build_lifecycle_assessment(
    registry: AuthoritativeEvidenceRegistry,
    *,
    repository: str,
    checked_at: datetime,
    links: Iterable[EvidenceLifecycleLink],
) -> EvidenceLifecycleAssessment:
    if checked_at.tzinfo is None:
        raise EvidenceLifecycleError("checked_at must be timezone-aware")
    if not repository.strip():
        raise EvidenceLifecycleError("repository is required")

    by_id = {item.evidence_id: item for item in registry.items}
    predecessor_to_successor: dict[str, str] = {}
    successor_to_predecessor: dict[str, str] = {}
    verified_links: list[EvidenceLifecycleLink] = []

    now = checked_at.astimezone(timezone.utc)

    for link in links:
        link.verify()
        if link.linked_at.astimezone(timezone.utc) > now:
            raise EvidenceLifecycleError("future-dated lifecycle link")

        predecessor_id = link.predecessor_evidence_id.strip()
        successor_id = link.successor_evidence_id.strip()
        predecessor = by_id.get(predecessor_id)
        successor = by_id.get(successor_id)
        if predecessor is None:
            raise EvidenceLifecycleError(
                f"predecessor evidence {predecessor_id} is missing"
            )
        if successor is None:
            raise EvidenceLifecycleError(
                f"successor evidence {successor_id} is missing"
            )
        if predecessor.status != "accepted":
            raise EvidenceLifecycleError(
                f"predecessor evidence {predecessor_id} is not accepted"
            )
        if successor.status != "accepted":
            raise EvidenceLifecycleError(
                f"successor evidence {successor_id} is not accepted"
            )
        if predecessor.source_type != successor.source_type:
            raise EvidenceLifecycleError(
                "supersession requires matching source_type"
            )
        if predecessor.population_scope.strip() != successor.population_scope.strip():
            raise EvidenceLifecycleError(
                "supersession requires matching population_scope"
            )
        predecessor_effective_from = _parse_timestamp(
            predecessor.effective_from, "predecessor effective_from"
        )
        successor_effective_from = _parse_timestamp(
            successor.effective_from, "successor effective_from"
        )
        if successor_effective_from <= predecessor_effective_from:
            raise EvidenceLifecycleError(
                "successor effective_from must be later than predecessor effective_from"
            )
        successor_approved_at = _parse_timestamp(
            successor.approved_at or "",
            "successor approved_at",
        )
        if successor_approved_at > now:
            raise EvidenceLifecycleError("successor approval is future-dated")

        if predecessor_id in predecessor_to_successor:
            raise EvidenceLifecycleError(
                f"predecessor evidence {predecessor_id} has multiple successors"
            )
        if successor_id in successor_to_predecessor:
            raise EvidenceLifecycleError(
                f"successor evidence {successor_id} has multiple predecessors"
            )
        predecessor_to_successor[predecessor_id] = successor_id
        successor_to_predecessor[successor_id] = predecessor_id
        verified_links.append(link)

    _ensure_acyclic(predecessor_to_successor)

    accepted_ids = {
        item.evidence_id
        for item in registry.items
        if item.status == "accepted"
    }
    superseded = tuple(sorted(predecessor_to_successor))
    heads = tuple(sorted(accepted_ids - set(superseded)))
    link_fingerprints = tuple(sorted(link.fingerprint.lower() for link in verified_links))

    fingerprint = _assessment_fingerprint(
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry.fingerprint,
        link_fingerprints=link_fingerprints,
        head_evidence_ids=heads,
        superseded_evidence_ids=superseded,
    )
    return EvidenceLifecycleAssessment(
        assessment_version=1,
        repository=repository,
        checked_at=checked_at,
        registry_fingerprint=registry.fingerprint,
        link_fingerprints=link_fingerprints,
        head_evidence_ids=heads,
        superseded_evidence_ids=superseded,
        fingerprint=fingerprint,
    )


def _parse_timestamp(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceLifecycleError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise EvidenceLifecycleError(f"{name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _ensure_acyclic(edges: dict[str, str]) -> None:
    for start in edges:
        seen: set[str] = set()
        current = start
        while current in edges:
            if current in seen:
                raise EvidenceLifecycleError("evidence supersession cycle detected")
            seen.add(current)
            current = edges[current]


def _assessment_fingerprint(
    *,
    repository: str,
    checked_at: datetime,
    registry_fingerprint: str,
    link_fingerprints: tuple[str, ...],
    head_evidence_ids: tuple[str, ...],
    superseded_evidence_ids: tuple[str, ...],
) -> str:
    payload = {
        "assessment_version": 1,
        "repository": repository,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "registry_fingerprint": registry_fingerprint.lower(),
        "link_fingerprints": list(link_fingerprints),
        "head_evidence_ids": list(head_evidence_ids),
        "superseded_evidence_ids": list(superseded_evidence_ids),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
