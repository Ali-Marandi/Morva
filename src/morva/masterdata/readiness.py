from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.masterdata.acceptance import (
    COVERAGE_KEYS,
    _current_coverage_evidence,
    _evidence_fingerprint,
    _master_data_integrity_snapshot_hash,
    validate_authoritative_master_data,
)
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord


@dataclass(frozen=True, slots=True)
class MasterDataReadinessResult:
    ready: bool
    blockers: tuple[str, ...]
    acceptance_id: str | None
    dataset_name: str | None
    dataset_sha256: str | None
    integrity_snapshot_hash: str | None


def verify_master_data_readiness(
    session: Session,
    *,
    dataset_name: str | None = None,
    dataset_sha256: str | None = None,
) -> MasterDataReadinessResult:
    """Fail closed unless an accepted master-data assessment still matches live state."""
    blockers: list[str] = []
    query = select(MasterDataAcceptanceRecord).where(MasterDataAcceptanceRecord.status == "accepted")
    if dataset_name is not None:
        query = query.where(MasterDataAcceptanceRecord.dataset_name == dataset_name)
    if dataset_sha256 is not None:
        query = query.where(MasterDataAcceptanceRecord.dataset_sha256 == dataset_sha256.lower())
    records = session.scalars(query.order_by(MasterDataAcceptanceRecord.created_at.desc())).all()
    if not records:
        return MasterDataReadinessResult(
            ready=False,
            blockers=("no accepted master-data assessment is available",),
            acceptance_id=None,
            dataset_name=dataset_name,
            dataset_sha256=dataset_sha256.lower() if dataset_sha256 else None,
            integrity_snapshot_hash=None,
        )

    record = records[0]
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

    current_snapshot_hash = _master_data_integrity_snapshot_hash(session)
    if current_snapshot_hash != record.integrity_snapshot_hash:
        blockers.append("master-data integrity snapshot differs from accepted evidence")

    current_coverage = _current_coverage_evidence(session)
    stored_coverage = record.coverage_evidence or {}
    if any(stored_coverage.get(key) != current_coverage[key] for key in COVERAGE_KEYS):
        blockers.append("master-data population coverage differs from accepted evidence")

    if record.status == "accepted":
        from morva.masterdata.acceptance import MasterDataAcceptanceRequest

        request = MasterDataAcceptanceRequest(
            dataset_name=record.dataset_name,
            schema_version=record.schema_version,
            source_system=record.source_system,
            source_uri=record.source_uri,
            authoritative_source_reference=record.authoritative_source_reference,
            evidence_reference=record.evidence_reference,
            evidence_sha256=record.evidence_sha256,
            population_scope=record.population_scope,
            coverage_evidence={key: int(stored_coverage[key]) for key in COVERAGE_KEYS if key in stored_coverage},
            dataset_period=record.dataset_period,
            dataset_sha256=record.dataset_sha256,
            row_count=record.row_count,
            duplicate_key_count=record.duplicate_key_count,
            rejected_row_count=record.rejected_row_count,
            schema_valid=record.schema_valid,
        )
        if _evidence_fingerprint(request, current_snapshot_hash) != record.evidence_fingerprint:
            blockers.append("accepted master-data evidence fingerprint is inconsistent")

    return MasterDataReadinessResult(
        ready=not blockers,
        blockers=tuple(blockers),
        acceptance_id=str(record.id),
        dataset_name=record.dataset_name,
        dataset_sha256=record.dataset_sha256,
        integrity_snapshot_hash=current_snapshot_hash,
    )
