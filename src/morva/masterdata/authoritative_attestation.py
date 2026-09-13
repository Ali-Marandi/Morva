from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.masterdata.acceptance import COVERAGE_KEYS, _current_coverage_evidence
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord


@dataclass(frozen=True, slots=True)
class MasterDataAuthorityAttestation:
    acceptance_id: UUID | str
    authority_reference: str
    authority_actor_id: str
    attested_at: datetime
    expected_coverage: dict[str, int]
    complete_dimensions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MasterDataAuthorityAttestationResult:
    eligible: bool
    blockers: tuple[str, ...]
    attestation_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "blockers": self.blockers,
            "attestation_fingerprint": self.attestation_fingerprint,
        }


def _canonicalize(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _fingerprint(attestation: MasterDataAuthorityAttestation, record: MasterDataAcceptanceRecord) -> str:
    payload = {
        "acceptance_id": str(attestation.acceptance_id),
        "dataset_name": record.dataset_name,
        "dataset_sha256": record.dataset_sha256,
        "evidence_fingerprint": record.evidence_fingerprint,
        "authority_reference": attestation.authority_reference.strip(),
        "authority_actor_id": attestation.authority_actor_id.strip(),
        "attested_at": attestation.attested_at,
        "expected_coverage": attestation.expected_coverage,
        "complete_dimensions": sorted(attestation.complete_dimensions),
        "integrity_snapshot_hash": record.integrity_snapshot_hash,
    }
    encoded = json.dumps(_canonicalize(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assess_authoritative_master_data_attestation(
    session: Session,
    attestation: MasterDataAuthorityAttestation,
) -> MasterDataAuthorityAttestationResult:
    blockers: list[str] = []
    acceptance_uuid = attestation.acceptance_id if isinstance(attestation.acceptance_id, UUID) else UUID(str(attestation.acceptance_id))
    record = session.scalar(select(MasterDataAcceptanceRecord).where(MasterDataAcceptanceRecord.id == acceptance_uuid))
    if record is None:
        return MasterDataAuthorityAttestationResult(False, ("master-data acceptance assessment not found",), "")
    if record.status != "accepted":
        blockers.append("master-data acceptance must be accepted before authority attestation")
    if not attestation.authority_reference.strip():
        blockers.append("authority_reference is required")
    if not attestation.authority_actor_id.strip():
        blockers.append("authority_actor_id is required")
    if attestation.authority_actor_id == record.submitted_by:
        blockers.append("authority attestor must differ from dataset submitter")
    if record.accepted_by and attestation.authority_actor_id == record.accepted_by:
        blockers.append("authority attestor must differ from acceptance confirmer")
    if attestation.attested_at.tzinfo is None:
        blockers.append("attested_at must be timezone-aware")
    missing = sorted(set(COVERAGE_KEYS) - set(attestation.expected_coverage))
    extra = sorted(set(attestation.expected_coverage) - set(COVERAGE_KEYS))
    blockers.extend(f"expected_coverage.{key} is required" for key in missing)
    blockers.extend(f"expected_coverage.{key} is not allowed" for key in extra)
    for key in COVERAGE_KEYS:
        value = attestation.expected_coverage.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            blockers.append(f"expected_coverage.{key} must be a non-negative integer")
    complete = set(attestation.complete_dimensions)
    invalid_complete = sorted(complete - set(COVERAGE_KEYS))
    blockers.extend(f"complete_dimensions.{key} is not allowed" for key in invalid_complete)
    missing_complete = sorted(set(COVERAGE_KEYS) - complete)
    blockers.extend(f"complete_dimensions.{key} must be explicitly attested" for key in missing_complete)

    current_coverage = _current_coverage_evidence(session)
    if not blockers:
        for key in COVERAGE_KEYS:
            if attestation.expected_coverage[key] != current_coverage[key]:
                blockers.append(
                    f"expected_coverage.{key}={attestation.expected_coverage[key]} does not match persisted count {current_coverage[key]}"
                )
            stored = (record.coverage_evidence or {}).get(key)
            if stored != attestation.expected_coverage[key]:
                blockers.append(f"expected_coverage.{key} does not match accepted evidence coverage")

    fingerprint = _fingerprint(attestation, record) if record is not None else ""
    return MasterDataAuthorityAttestationResult(not blockers, tuple(blockers), fingerprint)
