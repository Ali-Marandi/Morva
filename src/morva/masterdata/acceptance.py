from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.masterdata.authoritative import validate_authoritative_master_data
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.persistence.domain_extensions import AssignmentRecord, AttendanceFactRecord, TeacherRankCaseRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
COVERAGE_KEYS = (
    "organization_count",
    "position_count",
    "employee_count",
    "assignment_count",
    "personnel_snapshot_count",
    "attendance_fact_count",
    "teacher_rank_case_count",
)


@dataclass(frozen=True, slots=True)
class MasterDataAcceptanceRequest:
    dataset_name: str
    schema_version: str
    source_system: str
    source_uri: str
    authoritative_source_reference: str
    evidence_reference: str
    evidence_sha256: str
    population_scope: str
    coverage_evidence: dict[str, int]
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
    evidence_fingerprint: str

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
        "evidence_reference": payload.evidence_reference,
        "population_scope": payload.population_scope,
    }
    blockers.extend(f"{name} is required" for name, value in required_text.items() if not value.strip())
    if not payload.source_uri.startswith(("https://", "sftp://")):
        blockers.append("source_uri must use https:// or sftp://")
    if not SHA256_RE.fullmatch(payload.dataset_sha256):
        blockers.append("dataset_sha256 must be a 64-character hexadecimal SHA-256")
    if not SHA256_RE.fullmatch(payload.evidence_sha256):
        blockers.append("evidence_sha256 must be a 64-character hexadecimal SHA-256")
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
    missing_keys = [key for key in COVERAGE_KEYS if key not in payload.coverage_evidence]
    blockers.extend(f"coverage_evidence.{key} is required" for key in missing_keys)
    unexpected_keys = sorted(set(payload.coverage_evidence) - set(COVERAGE_KEYS))
    blockers.extend(f"coverage_evidence.{key} is not allowed" for key in unexpected_keys)
    for key in COVERAGE_KEYS:
        value = payload.coverage_evidence.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            blockers.append(f"coverage_evidence.{key} must be a non-negative integer")
    return blockers


def _canonicalize(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _master_data_integrity_snapshot_hash(session: Session) -> str:
    models = (
        OrganizationUnitRecord,
        PositionRecord,
        EmployeeRecord,
        AssignmentRecord,
        PersonnelSnapshotRecord,
        AttendanceFactRecord,
        TeacherRankCaseRecord,
    )
    snapshot: dict[str, list[dict[str, object]]] = {}
    for model in models:
        mapper = inspect(model)
        rows = session.scalars(select(model)).all()
        serialized_rows: list[dict[str, object]] = []
        for row in rows:
            serialized_rows.append(
                {
                    column.key: _canonicalize(getattr(row, column.key))
                    for column in mapper.columns
                }
            )
        serialized_rows.sort(key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        snapshot[model.__tablename__] = serialized_rows
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _current_coverage_evidence(session: Session) -> dict[str, int]:
    models = (
        ("organization_count", OrganizationUnitRecord),
        ("position_count", PositionRecord),
        ("employee_count", EmployeeRecord),
        ("assignment_count", AssignmentRecord),
        ("personnel_snapshot_count", PersonnelSnapshotRecord),
        ("attendance_fact_count", AttendanceFactRecord),
        ("teacher_rank_case_count", TeacherRankCaseRecord),
    )
    return {key: len(session.scalars(select(model)).all()) for key, model in models}


def _evidence_fingerprint(payload: MasterDataAcceptanceRequest, integrity_snapshot_hash: str) -> str:
    canonical = {
        "dataset_name": payload.dataset_name,
        "schema_version": payload.schema_version,
        "source_system": payload.source_system,
        "source_uri": payload.source_uri,
        "authoritative_source_reference": payload.authoritative_source_reference,
        "evidence_reference": payload.evidence_reference,
        "evidence_sha256": payload.evidence_sha256.lower(),
        "population_scope": payload.population_scope,
        "coverage_evidence": payload.coverage_evidence,
        "dataset_period": payload.dataset_period,
        "dataset_sha256": payload.dataset_sha256.lower(),
        "row_count": payload.row_count,
        "duplicate_key_count": payload.duplicate_key_count,
        "rejected_row_count": payload.rejected_row_count,
        "schema_valid": payload.schema_valid,
        "integrity_snapshot_hash": integrity_snapshot_hash,
    }
    encoded = json.dumps(_canonicalize(canonical), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assess_master_data_acceptance(
    session: Session,
    payload: MasterDataAcceptanceRequest,
    actor_id: str,
) -> MasterDataAcceptanceResult:
    normalized_hash = payload.dataset_sha256.lower()
    blockers = _validate_contract(payload)
    warnings: list[str] = []
    integrity = validate_authoritative_master_data(session)
    integrity_snapshot_hash = _master_data_integrity_snapshot_hash(session)
    current_coverage = _current_coverage_evidence(session)
    if any(payload.coverage_evidence.get(key) != current_coverage[key] for key in COVERAGE_KEYS):
        blockers.append("coverage_evidence does not match persisted master-data population counts")
    if integrity.blocking:
        blockers.append("current authoritative master-data integrity gate is blocking")
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
    evidence_fingerprint = _evidence_fingerprint(payload, integrity_snapshot_hash)

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
            evidence_fingerprint=existing.evidence_fingerprint,
        )

    eligible = not blockers
    record = MasterDataAcceptanceRecord(
        dataset_name=payload.dataset_name,
        schema_version=payload.schema_version,
        source_system=payload.source_system,
        source_uri=payload.source_uri,
        authoritative_source_reference=payload.authoritative_source_reference,
        evidence_reference=payload.evidence_reference,
        evidence_sha256=payload.evidence_sha256.lower(),
        population_scope=payload.population_scope,
        coverage_evidence=payload.coverage_evidence,
        evidence_fingerprint=evidence_fingerprint,
        dataset_period=payload.dataset_period,
        dataset_sha256=normalized_hash,
        row_count=payload.row_count,
        duplicate_key_count=payload.duplicate_key_count,
        rejected_row_count=payload.rejected_row_count,
        schema_valid=payload.schema_valid,
        status="eligible" if eligible else "blocked",
        integrity_blocking=integrity.blocking,
        integrity_snapshot_hash=integrity_snapshot_hash,
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
            "evidence_sha256": record.evidence_sha256,
            "evidence_fingerprint": record.evidence_fingerprint,
            "integrity_snapshot_hash": record.integrity_snapshot_hash,
            "coverage_evidence": record.coverage_evidence,
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
        evidence_fingerprint=record.evidence_fingerprint,
    )


def confirm_master_data_acceptance(
    session: Session,
    acceptance_id: UUID | str,
    actor_id: str,
    authority_confirmation_reference: str,
) -> MasterDataAcceptanceRecord:
    acceptance_uuid = acceptance_id if isinstance(acceptance_id, UUID) else UUID(str(acceptance_id))
    record = session.get(MasterDataAcceptanceRecord, acceptance_uuid)
    if record is None:
        raise ValueError("master-data acceptance assessment not found")
    if record.status != "eligible":
        raise ValueError("master-data acceptance is blocked")
    if not authority_confirmation_reference.strip():
        raise ValueError("authority confirmation reference is required")
    if record.submitted_by == actor_id:
        raise ValueError("master-data acceptance confirmation requires a distinct authority from submitter")
    if not record.integrity_snapshot_hash:
        raise ValueError("master-data acceptance assessment is missing integrity snapshot")
    integrity = validate_authoritative_master_data(session)
    if integrity.blocking:
        raise ValueError("master-data integrity changed after assessment")
    current_snapshot_hash = _master_data_integrity_snapshot_hash(session)
    if current_snapshot_hash != record.integrity_snapshot_hash:
        raise ValueError("master-data integrity snapshot changed after assessment")
    current_coverage = _current_coverage_evidence(session)
    stored_coverage = record.coverage_evidence or {}
    if any(stored_coverage.get(key) != current_coverage[key] for key in COVERAGE_KEYS):
        raise ValueError("master-data coverage evidence changed after assessment")
    request = MasterDataAcceptanceRequest(
        dataset_name=record.dataset_name,
        schema_version=record.schema_version,
        source_system=record.source_system,
        source_uri=record.source_uri,
        authoritative_source_reference=record.authoritative_source_reference,
        evidence_reference=record.evidence_reference,
        evidence_sha256=record.evidence_sha256,
        population_scope=record.population_scope,
        coverage_evidence={key: int(stored_coverage[key]) for key in COVERAGE_KEYS},
        dataset_period=record.dataset_period,
        dataset_sha256=record.dataset_sha256,
        row_count=record.row_count,
        duplicate_key_count=record.duplicate_key_count,
        rejected_row_count=record.rejected_row_count,
        schema_valid=record.schema_valid,
    )
    if _evidence_fingerprint(request, current_snapshot_hash) != record.evidence_fingerprint:
        raise ValueError("master-data acceptance evidence fingerprint changed")
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
            "evidence_fingerprint": record.evidence_fingerprint,
            "integrity_snapshot_hash": record.integrity_snapshot_hash,
            "authority_confirmation_reference": record.authority_confirmation_reference,
        },
        reason="confirm authoritative master-data acceptance",
        session=session,
    )
    session.commit()
    return record
