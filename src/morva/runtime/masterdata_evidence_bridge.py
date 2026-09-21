from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)


class MasterDataEvidenceBridgeError(ValueError):
    """Raised when external master-data evidence cannot bind to internal acceptance."""


@dataclass(frozen=True, slots=True)
class MasterDataEvidenceBinding:
    binding_version: int
    evidence_id: str
    acceptance_id: str
    population_scope: str
    dataset_sha256: str
    evidence_sha256: str
    acceptance_evidence_fingerprint: str
    integrity_snapshot_hash: str
    authority_confirmation_reference: str
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise MasterDataEvidenceBridgeError(
                "unsupported master-data evidence binding version"
            )
        for name, value in (
            ("evidence_id", self.evidence_id),
            ("acceptance_id", self.acceptance_id),
            ("population_scope", self.population_scope),
            ("bound_by", self.bound_by),
            ("authority_confirmation_reference", self.authority_confirmation_reference),
        ):
            if not value.strip():
                raise MasterDataEvidenceBridgeError(f"{name} is required")
        for name, value in (
            ("dataset_sha256", self.dataset_sha256),
            ("evidence_sha256", self.evidence_sha256),
            ("acceptance_evidence_fingerprint", self.acceptance_evidence_fingerprint),
            ("integrity_snapshot_hash", self.integrity_snapshot_hash),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise MasterDataEvidenceBridgeError(
                    f"{name} must be SHA-256"
                )
        try:
            UUID(self.acceptance_id)
        except ValueError as exc:
            raise MasterDataEvidenceBridgeError(
                "acceptance_id must be a UUID"
            ) from exc
        if self.bound_at.tzinfo is None:
            raise MasterDataEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "evidence_id": self.evidence_id,
            "acceptance_id": self.acceptance_id,
            "population_scope": self.population_scope,
            "dataset_sha256": self.dataset_sha256.lower(),
            "evidence_sha256": self.evidence_sha256.lower(),
            "acceptance_evidence_fingerprint": (
                self.acceptance_evidence_fingerprint.lower()
            ),
            "integrity_snapshot_hash": self.integrity_snapshot_hash.lower(),
            "authority_confirmation_reference": (
                self.authority_confirmation_reference
            ),
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.isoformat(),
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "evidence_id": self.evidence_id,
            "acceptance_id": self.acceptance_id,
            "population_scope": self.population_scope,
            "dataset_sha256": self.dataset_sha256,
            "evidence_sha256": self.evidence_sha256,
            "acceptance_evidence_fingerprint": self.acceptance_evidence_fingerprint,
            "integrity_snapshot_hash": self.integrity_snapshot_hash,
            "authority_confirmation_reference": self.authority_confirmation_reference,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_master_data_evidence_binding(
    session: Session,
    registry: AuthoritativeEvidenceRegistry,
    *,
    acceptance_id: UUID | str,
    evidence_id: str,
    bound_by: str,
    bound_at: datetime,
) -> MasterDataEvidenceBinding:
    if not evidence_id.strip():
        raise MasterDataEvidenceBridgeError("evidence_id is required")
    if not bound_by.strip():
        raise MasterDataEvidenceBridgeError("bound_by is required")
    if bound_at.tzinfo is None:
        raise MasterDataEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )

    acceptance_uuid = (
        acceptance_id
        if isinstance(acceptance_id, UUID)
        else UUID(str(acceptance_id))
    )
    record = session.scalar(
        select(MasterDataAcceptanceRecord).where(
            MasterDataAcceptanceRecord.id == acceptance_uuid
        )
    )
    if record is None:
        raise MasterDataEvidenceBridgeError(
            "master-data acceptance assessment not found"
        )
    if record.status != "accepted":
        raise MasterDataEvidenceBridgeError(
            "master-data acceptance must be accepted before binding"
        )
    if not record.accepted_by or not record.accepted_at:
        raise MasterDataEvidenceBridgeError(
            "accepted master-data record is missing authority confirmation"
        )
    if not record.authority_confirmation_reference:
        raise MasterDataEvidenceBridgeError(
            "master-data authority confirmation reference is required"
        )
    if not record.integrity_snapshot_hash:
        raise MasterDataEvidenceBridgeError(
            "master-data integrity snapshot is required"
        )
    if not record.evidence_fingerprint:
        raise MasterDataEvidenceBridgeError(
            "master-data evidence fingerprint is required"
        )

    authoritative = next(
        (item for item in registry.items if item.evidence_id == evidence_id),
        None,
    )
    if authoritative is None:
        raise MasterDataEvidenceBridgeError(
            "authoritative evidence ID is not present in registry"
        )
    if authoritative.source_type != "master_data":
        raise MasterDataEvidenceBridgeError(
            "binding evidence must use master_data source type"
        )
    if authoritative.status != "accepted":
        raise MasterDataEvidenceBridgeError(
            "authoritative master-data evidence must be accepted"
        )
    if authoritative.population_scope.strip() != record.population_scope.strip():
        raise MasterDataEvidenceBridgeError(
            "authoritative evidence population scope does not match acceptance"
        )
    if authoritative.source_sha256.lower() != record.evidence_sha256.lower():
        raise MasterDataEvidenceBridgeError(
            "authoritative evidence SHA-256 does not match accepted evidence"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    accepted_at = record.accepted_at
    if accepted_at.tzinfo is None:
        raise MasterDataEvidenceBridgeError(
            "accepted_at must be timezone-aware"
        )
    if accepted_at > bound_at_utc:
        raise MasterDataEvidenceBridgeError(
            "binding precedes internal acceptance"
        )
    approved_at = (
        datetime.fromisoformat(authoritative.approved_at)
        if authoritative.approved_at
        else None
    )
    if approved_at is None or approved_at > bound_at_utc:
        raise MasterDataEvidenceBridgeError(
            "binding precedes authoritative evidence approval"
        )
    if authoritative.expires_at is not None:
        expires_at = datetime.fromisoformat(authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise MasterDataEvidenceBridgeError(
                "authoritative master-data evidence is expired"
            )
    effective_from = datetime.fromisoformat(authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise MasterDataEvidenceBridgeError(
            "authoritative master-data evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = datetime.fromisoformat(authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise MasterDataEvidenceBridgeError(
                "authoritative master-data evidence is no longer effective"
            )

    if record.submitted_by and bound_by == record.submitted_by:
        raise MasterDataEvidenceBridgeError(
            "binding actor must differ from dataset submitter"
        )
    if record.accepted_by and bound_by == record.accepted_by:
        raise MasterDataEvidenceBridgeError(
            "binding actor must differ from acceptance confirmer"
        )

    return MasterDataEvidenceBinding(
        binding_version=1,
        evidence_id=evidence_id,
        acceptance_id=str(record.id),
        population_scope=record.population_scope.strip(),
        dataset_sha256=record.dataset_sha256,
        evidence_sha256=record.evidence_sha256,
        acceptance_evidence_fingerprint=record.evidence_fingerprint,
        integrity_snapshot_hash=record.integrity_snapshot_hash,
        authority_confirmation_reference=(
            record.authority_confirmation_reference
        ),
        bound_by=bound_by,
        bound_at=bound_at_utc,
    )
