from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.evidence_submission_records import AuthoritativeEvidenceSubmissionRecord
from morva.runtime.authoritative_evidence_intake import ALLOWED_SOURCE_TYPES
from morva.security.policy import require_distinct_actors


class EvidenceSubmissionError(ValueError):
    """Raised when evidence submission cannot pass fail-closed validation."""


def _validate_sha256(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise EvidenceSubmissionError("source_sha256 must be SHA-256")
    return normalized


def _validate_datetime(name: str, value: datetime) -> datetime:
    if value.tzinfo is None:
        raise EvidenceSubmissionError(f"{name} must include a timezone")
    return value.astimezone(timezone.utc)


def _fingerprint(
    *,
    evidence_id: str,
    source_type: str,
    source_uri: str,
    source_sha256: str,
    issuer: str,
    population_scope: str,
    effective_from: datetime,
    effective_to: datetime | None,
    expires_at: datetime | None,
    submitted_by: str,
    submitted_at: datetime,
) -> str:
    payload = {
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_uri": source_uri,
        "source_sha256": source_sha256,
        "issuer": issuer,
        "population_scope": population_scope,
        "effective_from": effective_from.isoformat(),
        "effective_to": effective_to.isoformat() if effective_to else None,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "submitted_by": submitted_by,
        "submitted_at": submitted_at.isoformat(),
    }
    return sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def submit_evidence(
    session: Session,
    *,
    evidence_id: str,
    source_type: str,
    source_uri: str,
    source_sha256: str,
    issuer: str,
    population_scope: str,
    effective_from: datetime,
    effective_to: datetime | None,
    expires_at: datetime | None,
    submitted_by: str,
    submitted_at: datetime,
) -> AuthoritativeEvidenceSubmissionRecord:
    values = {
        "evidence_id": evidence_id.strip(),
        "source_type": source_type.strip(),
        "source_uri": source_uri.strip(),
        "issuer": issuer.strip(),
        "population_scope": population_scope.strip(),
        "submitted_by": submitted_by.strip(),
    }
    for name, value in values.items():
        if not value:
            raise EvidenceSubmissionError(f"{name} is required")
    if values["source_type"] not in ALLOWED_SOURCE_TYPES:
        raise EvidenceSubmissionError("unsupported source_type")
    digest = _validate_sha256(source_sha256)
    effective_from_utc = _validate_datetime("effective_from", effective_from)
    effective_to_utc = _validate_datetime("effective_to", effective_to) if effective_to else None
    expires_at_utc = _validate_datetime("expires_at", expires_at) if expires_at else None
    submitted_at_utc = _validate_datetime("submitted_at", submitted_at)
    if effective_to_utc and effective_to_utc <= effective_from_utc:
        raise EvidenceSubmissionError("effective_to must be after effective_from")
    if expires_at_utc and expires_at_utc <= effective_from_utc:
        raise EvidenceSubmissionError("expires_at must be after effective_from")

    existing = session.scalar(
        select(AuthoritativeEvidenceSubmissionRecord).where(
            AuthoritativeEvidenceSubmissionRecord.evidence_id == values["evidence_id"]
        )
    )
    if existing is not None:
        raise EvidenceSubmissionError("evidence_id already submitted")

    record = AuthoritativeEvidenceSubmissionRecord(
        evidence_id=values["evidence_id"],
        source_type=values["source_type"],
        source_uri=values["source_uri"],
        source_sha256=digest,
        issuer=values["issuer"],
        population_scope=values["population_scope"],
        effective_from=effective_from_utc,
        effective_to=effective_to_utc,
        expires_at=expires_at_utc,
        status="pending",
        submitted_by=values["submitted_by"],
        submitted_at=submitted_at_utc,
        fingerprint=_fingerprint(
            evidence_id=values["evidence_id"],
            source_type=values["source_type"],
            source_uri=values["source_uri"],
            source_sha256=digest,
            issuer=values["issuer"],
            population_scope=values["population_scope"],
            effective_from=effective_from_utc,
            effective_to=effective_to_utc,
            expires_at=expires_at_utc,
            submitted_by=values["submitted_by"],
            submitted_at=submitted_at_utc,
        ),
    )
    session.add(record)
    session.flush()
    return record


def decide_evidence(
    session: Session,
    *,
    evidence_id: str,
    approver_id: str,
    decision: str,
    decided_at: datetime,
    rejection_reason: str | None = None,
) -> AuthoritativeEvidenceSubmissionRecord:
    if decision not in {"accepted", "rejected"}:
        raise EvidenceSubmissionError("decision must be accepted or rejected")
    approver = approver_id.strip()
    if not approver:
        raise EvidenceSubmissionError("approver_id is required")
    decided_at_utc = _validate_datetime("decided_at", decided_at)

    record = session.scalar(
        select(AuthoritativeEvidenceSubmissionRecord)
        .where(AuthoritativeEvidenceSubmissionRecord.evidence_id == evidence_id.strip())
        .with_for_update()
    )
    if record is None:
        raise KeyError("evidence submission not found")
    if record.status != "pending":
        raise EvidenceSubmissionError("only pending evidence can be decided")

    require_distinct_actors((record.submitted_by, approver))

    if decision == "rejected":
        reason = (rejection_reason or "").strip()
        if not reason:
            raise EvidenceSubmissionError("rejection_reason is required")
        record.rejection_reason = reason
    else:
        record.rejection_reason = None

    record.status = decision
    record.approved_by = approver
    record.approved_at = decided_at_utc
    session.flush()
    return record
