from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.masterdata.validation import validate_master_data
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


@dataclass(frozen=True, slots=True)
class MasterDataAcceptanceRequest:
    dataset_name: str
    schema_version: str
    source_system: str
    source_uri: str
    authoritative_source_reference: str
    dataset_period: str
    dataset_sha256: str
    row_count: int
    duplicate_key_count: int
    rejected_row_count: int
    schema_valid: bool


@dataclass(frozen=True, slots=True)
class MasterDataAcceptanceResult:
    status: str
    eligible: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    integrity_blocking: bool
    acceptance_id: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_contract(payload: MasterDataAcceptanceRequest) -> list[str]:
    blockers: list[str] = []
    required_text = {
        "dataset_name": payload.dataset_name,
        "schema_version": payload.schema_version,
        "source_system": payload.source_system,
        "source_uri": payload.source_uri,
        "authoritative_source_reference": payload.authoritative_source_reference,
    }
    blockers.extend(
        f"{name} is required" for name, value in required_text.items() if not value.strip()
    )
    if not payload.source_uri.startswith(("https://", "sftp://")):
        blockers.append("source_uri must use https:// or sftp://")
    if not SHA256_RE.fullmatch(payload.dataset_sha256):
        blockers.append("dataset_sha256 must be a 64-character hexadecimal SHA-256")
    if not PERIOD_RE.fullmatch(payload.dataset_period):
        blockers.append("dataset_period must use YYYY-MM")
    if payload.row_count <= 0:
        blockers.append("row_count must be greater than zero")
    if payload.duplicate_key_count != 0:
        blockers.append("duplicate_key_count must be zero")
    if payload.rejected_row_count != 0:
        blockers.append("rejected_row_count must be zero")
    if not payload.schema_valid:
        blockers.append("schema_valid must be true")
    return blockers


def assess_master_data_acceptance(
    session: Session,
    payload: MasterDataAcceptanceRequest,
    actor_id: str,
) -> MasterDataAcceptanceResult:
    normalized_hash = payload.dataset_sha256.lower()
    blockers = _validate_contract(payload)
    warnings: list[str] = []
    integrity = validate_master_data(session)
    if integrity.blocking:
        blockers.append("current master-data integrity gate is blocking")
        blockers.extend(
            f"integrity:{item.code}:{item.entity_id}"
            for item in integrity.findings
            if item.severity == "error"
        )
    warnings.extend(
        f"integrity:{item.code}:{item.entity_id}"
        for item in integrity.findings
        if item.severity == "warning"
    )

    existing = session.scalar(
        select(MasterDataAcceptanceRecord).where(
            MasterDataAcceptanceRecord.dataset_name == payload.dataset_name,
            MasterDataAcceptanceRecord.dataset_sha256 == normalized_hash,
        )
    )
    if existing is not None:
        return MasterDataAcceptanceResult(
            status=existing.status,
            eligible=existing.status in {"eligible", "accepted"},
            blockers=tuple(existing.blockers or []),
            warnings=tuple(existing.warnings or []),
            integrity_blocking=existing.integrity_blocking,
            acceptance_id=str(existing.id),
        )

    eligible = not blockers
    record = MasterDataAcceptanceRecord(
        dataset_name=payload.dataset_name,
        schema_version=payload.schema_version,
        source_system=payload.source_system,
        source_uri=payload.source_uri,
        authoritative_source_reference=payload.authoritative_source_reference,
        dataset_period=payload.dataset_period,
        dataset_sha256=normalized_hash,
        row_count=payload.row_count,
        duplicate_key_count=payload.duplicate_key_count,
        rejected_row_count=payload.rejected_row_count,
        schema_valid=payload.schema_valid,
        status="eligible" if eligible else "blocked",
        integrity_blocking=integrity.blocking,
        blockers=blockers,
        warnings=warnings,
        submitted_by=actor_id,
    )
    session.add(record)
    session.flush()
    append_audit_event(
        event_type="masterdata.acceptance.assessed",
        entity_type="master_data_acceptance",
        entity_id=str(record.id),
        actor_id=actor_id,
        payload={
            "dataset_name": record.dataset_name,
            "dataset_sha256": record.dataset_sha256,
            "status": record.status,
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        reason="assess master-data acceptance contract",
        session=session,
    )
    session.commit()
    return MasterDataAcceptanceResult(
        status=record.status,
        eligible=eligible,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        integrity_blocking=integrity.blocking,
        acceptance_id=str(record.id),
    )


def confirm_master_data_acceptance(
    session: Session,
    acceptance_id: UUID,
    actor_id: str,
    authority_confirmation_reference: str,
) -> MasterDataAcceptanceRecord:
    record = session.get(MasterDataAcceptanceRecord, acceptance_id)
    if record is None:
        raise ValueError("master-data acceptance assessment not found")
    if record.status != "eligible":
        raise ValueError("master-data acceptance is blocked")
    if not authority_confirmation_reference.strip():
        raise ValueError("authority confirmation reference is required")
    record.status = "accepted"
    record.accepted_by = actor_id
    record.accepted_at = datetime.utcnow()
    record.authority_confirmation_reference = authority_confirmation_reference.strip()
    record.blockers = []
    append_audit_event(
        event_type="masterdata.acceptance.confirmed",
        entity_type="master_data_acceptance",
        entity_id=str(record.id),
        actor_id=actor_id,
        payload={
            "dataset_name": record.dataset_name,
            "dataset_sha256": record.dataset_sha256,
            "authority_confirmation_reference": record.authority_confirmation_reference,
        },
        reason="confirm authoritative master-data acceptance",
        session=session,
    )
    session.commit()
    return record
