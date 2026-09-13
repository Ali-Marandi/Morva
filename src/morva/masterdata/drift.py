from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.masterdata.acceptance import (
    COVERAGE_KEYS,
    MasterDataAcceptanceRequest,
    _current_coverage_evidence,
    _evidence_fingerprint,
    _master_data_integrity_snapshot_hash,
    validate_authoritative_master_data,
)
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord


@dataclass(frozen=True, slots=True)
class MasterDataDriftResult:
    acceptance_id: str
    dataset_name: str
    dataset_sha256: str
    detected: bool
    blockers: tuple[str, ...]
    coverage_deltas: dict[str, int]
    accepted_integrity_snapshot_hash: str | None
    current_integrity_snapshot_hash: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_master_data_drift(
    session: Session,
    acceptance_id: UUID | str,
) -> MasterDataDriftResult:
    """Compare an accepted master-data assessment with the current persisted state."""
    acceptance_uuid = acceptance_id if isinstance(acceptance_id, UUID) else UUID(str(acceptance_id))
    record = session.get(MasterDataAcceptanceRecord, acceptance_uuid)
    if record is None:
        raise ValueError("master-data acceptance assessment not found")

    blockers: list[str] = []
    current_snapshot_hash = _master_data_integrity_snapshot_hash(session)
    stored_coverage = record.coverage_evidence or {}
    current_coverage = _current_coverage_evidence(session)
    coverage_deltas = {
        key: current_coverage[key] - int(stored_coverage.get(key, 0))
        for key in COVERAGE_KEYS
    }

    if record.status != "accepted":
        blockers.append("master-data acceptance is not in accepted status")
    if not record.accepted_by or not record.accepted_at or not record.authority_confirmation_reference:
        blockers.append("accepted master-data record is missing authority confirmation evidence")

    integrity = validate_authoritative_master_data(session)
    if integrity.blocking:
        blockers.append("current authoritative master-data integrity gate is blocking")
        blockers.extend(
            f"integrity:{item.code}:{item.entity_id}"
            for item in integrity.findings
            if item.severity == "error"
        )

    if current_snapshot_hash != record.integrity_snapshot_hash:
        blockers.append("master-data integrity snapshot differs from accepted evidence")

    if any(delta != 0 for delta in coverage_deltas.values()):
        blockers.append("master-data population coverage differs from accepted evidence")

    request = MasterDataAcceptanceRequest(
        dataset_name=record.dataset_name,
        schema_version=record.schema_version,
        source_system=record.source_system,
        source_uri=record.source_uri,
        authoritative_source_reference=record.authoritative_source_reference,
        evidence_reference=record.evidence_reference,
        evidence_sha256=record.evidence_sha256,
        population_scope=record.population_scope,
        coverage_evidence={key: int(stored_coverage.get(key, 0)) for key in COVERAGE_KEYS},
        dataset_period=record.dataset_period,
        dataset_sha256=record.dataset_sha256,
        row_count=record.row_count,
        duplicate_key_count=record.duplicate_key_count,
        rejected_row_count=record.rejected_row_count,
        schema_valid=record.schema_valid,
    )
    if _evidence_fingerprint(request, current_snapshot_hash) != record.evidence_fingerprint:
        blockers.append("accepted master-data evidence fingerprint is inconsistent")

    return MasterDataDriftResult(
        acceptance_id=str(record.id),
        dataset_name=record.dataset_name,
        dataset_sha256=record.dataset_sha256,
        detected=bool(blockers),
        blockers=tuple(dict.fromkeys(blockers)),
        coverage_deltas=coverage_deltas,
        accepted_integrity_snapshot_hash=record.integrity_snapshot_hash,
        current_integrity_snapshot_hash=current_snapshot_hash,
    )
