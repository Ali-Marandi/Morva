from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Iterable

from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceIntakeError,
    AuthoritativeEvidenceItem,
    AuthoritativeEvidenceRegistry,
    build_registry,
)
from morva.runtime.evidence_submission import verify_submission_record


class EvidenceRegistryBridgeError(ValueError):
    """Raised when accepted submissions cannot form a trusted registry projection."""


@dataclass(frozen=True, slots=True)
class EvidenceRegistryProjection:
    projection_version: int
    projected_at: datetime
    source_submission_count: int
    accepted_evidence_ids: tuple[str, ...]
    registry_fingerprint: str
    projection_fingerprint: str

    def __post_init__(self) -> None:
        if self.projection_version != 1:
            raise EvidenceRegistryBridgeError(
                "unsupported evidence registry projection version"
            )
        if self.projected_at.tzinfo is None:
            raise EvidenceRegistryBridgeError(
                "projected_at must be timezone-aware"
            )
        if self.source_submission_count != len(self.accepted_evidence_ids):
            raise EvidenceRegistryBridgeError(
                "source submission count does not match evidence ids"
            )
        for name, value in (
            ("registry_fingerprint", self.registry_fingerprint),
            ("projection_fingerprint", self.projection_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise EvidenceRegistryBridgeError(f"{name} must be SHA-256")

    def to_payload(self) -> dict[str, object]:
        return {
            "projection_version": self.projection_version,
            "projected_at": self.projected_at.isoformat(),
            "source_submission_count": self.source_submission_count,
            "accepted_evidence_ids": list(self.accepted_evidence_ids),
            "registry_fingerprint": self.registry_fingerprint,
            "projection_fingerprint": self.projection_fingerprint,
        }


def submission_to_authoritative_item(
    record: AuthoritativeEvidenceSubmissionRecord,
) -> AuthoritativeEvidenceItem:
    try:
        verify_submission_record(record)
    except ValueError as exc:
        raise EvidenceRegistryBridgeError(
            f"submission verification failed: {exc}"
        ) from exc
    if record.status != "accepted":
        raise EvidenceRegistryBridgeError(
            "only accepted evidence submissions can enter the registry"
        )
    if not record.decided_by or not record.decided_at:
        raise EvidenceRegistryBridgeError(
            "accepted evidence is missing approval metadata"
        )

    try:
        item = AuthoritativeEvidenceItem(
            intake_version=1,
        evidence_id=record.evidence_id.strip(),
        source_type=record.source_type.strip(),
        source_uri=record.source_uri.strip(),
        source_sha256=record.source_sha256.strip().lower(),
        issuer=record.issuer.strip(),
        population_scope=record.population_scope.strip(),
        effective_from=_as_iso(record.effective_from, "effective_from"),
        effective_to=(
            _as_iso(record.effective_to, "effective_to")
            if record.effective_to
            else None
        ),
        status="accepted",
        approved_by=record.decided_by.strip(),
        approved_at=_as_iso(record.decided_at, "decided_at"),
            expires_at=(
                _as_iso(record.expires_at, "expires_at")
                if record.expires_at
                else None
            ),
        )
    except (AuthoritativeEvidenceIntakeError, ValueError) as exc:
        raise EvidenceRegistryBridgeError(
            f"accepted evidence cannot be mapped into M4.1 registry: {exc}"
        ) from exc
    return item


def _as_iso(value: datetime, name: str) -> str:
    if value.tzinfo is None:
        raise EvidenceRegistryBridgeError(f"{name} must include a timezone")
    return value.astimezone(timezone.utc).isoformat()


def build_registry_projection(
    records: Iterable[AuthoritativeEvidenceSubmissionRecord],
    *,
    projected_at: datetime,
) -> tuple[AuthoritativeEvidenceRegistry, EvidenceRegistryProjection]:
    if projected_at.tzinfo is None:
        raise EvidenceRegistryBridgeError(
            "projected_at must be timezone-aware"
        )

    accepted_items: list[AuthoritativeEvidenceItem] = []
    seen_ids: set[str] = set()
    source_count = 0

    for record in records:
        try:
            verify_submission_record(record)
        except ValueError as exc:
            raise EvidenceRegistryBridgeError(
                f"submission verification failed: {exc}"
            ) from exc
        if record.status != "accepted":
            continue
        source_count += 1
        evidence_id = record.evidence_id.strip()
        if evidence_id in seen_ids:
            raise EvidenceRegistryBridgeError(
                f"duplicate accepted evidence_id: {evidence_id}"
            )
        seen_ids.add(evidence_id)
        accepted_items.append(submission_to_authoritative_item(record))

    if source_count == 0:
        raise EvidenceRegistryBridgeError(
            "cannot project an empty authoritative evidence registry"
        )

    registry = build_registry(
        tuple(accepted_items),
        registered_at=projected_at,
    )
    accepted_evidence_ids = tuple(item.evidence_id for item in registry.items)
    projection_fingerprint = _projection_fingerprint(
        registry=registry,
        projected_at=projected_at,
        accepted_evidence_ids=accepted_evidence_ids,
    )
    projection = EvidenceRegistryProjection(
        projection_version=1,
        projected_at=projected_at,
        source_submission_count=source_count,
        accepted_evidence_ids=accepted_evidence_ids,
        registry_fingerprint=registry.fingerprint,
        projection_fingerprint=projection_fingerprint,
    )
    return registry, projection


def _projection_fingerprint(
    *,
    registry: AuthoritativeEvidenceRegistry,
    projected_at: datetime,
    accepted_evidence_ids: tuple[str, ...],
) -> str:
    payload = {
        "projection_version": 1,
        "projected_at": projected_at.astimezone(timezone.utc).isoformat(),
        "registry_fingerprint": registry.fingerprint,
        "accepted_evidence_ids": list(accepted_evidence_ids),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
