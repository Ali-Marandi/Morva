from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import AuthoritativeEvidenceRegistry


class LoadValidationEvidenceError(ValueError):
    """Raised when load-validation evidence cannot bind safely."""


def _timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise LoadValidationEvidenceError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise LoadValidationEvidenceError(f"{name} must include a timezone")
    return parsed


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise LoadValidationEvidenceError(f"{name} must be SHA-256")


@dataclass(frozen=True, slots=True)
class LoadValidationEvidence:
    evidence_version: int
    validation_id: str
    environment: str
    workload_profile: str
    population_scope: str
    target_employees: int
    processed_employees: int
    elapsed_seconds: float
    throughput_per_second: float
    result_fingerprint: str
    authoritative_evidence_id: str
    reviewer_id: str
    approver_id: str
    tested_at: str
    approved_at: str
    status: str = "passed"

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise LoadValidationEvidenceError(
                "unsupported load-validation evidence version"
            )
        for name, value in (
            ("validation_id", self.validation_id),
            ("environment", self.environment),
            ("workload_profile", self.workload_profile),
            ("population_scope", self.population_scope),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
        ):
            if not value.strip():
                raise LoadValidationEvidenceError(f"{name} is required")
        if self.target_employees < 10_000:
            raise LoadValidationEvidenceError(
                "target_employees must be at least 10000"
            )
        if self.processed_employees != self.target_employees:
            raise LoadValidationEvidenceError(
                "processed_employees must equal target_employees"
            )
        if self.elapsed_seconds <= 0:
            raise LoadValidationEvidenceError(
                "elapsed_seconds must be positive"
            )
        if self.throughput_per_second <= 0:
            raise LoadValidationEvidenceError(
                "throughput_per_second must be positive"
            )
        if self.status != "passed":
            raise LoadValidationEvidenceError(
                "load-validation evidence must be passed"
            )
        _sha256("result_fingerprint", self.result_fingerprint)
        tested_at = _timestamp("tested_at", self.tested_at)
        approved_at = _timestamp("approved_at", self.approved_at)
        if approved_at < tested_at:
            raise LoadValidationEvidenceError(
                "approved_at cannot precede tested_at"
            )
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise LoadValidationEvidenceError(
                "reviewer and approver must be distinct"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "evidence_version": self.evidence_version,
            "validation_id": self.validation_id,
            "environment": self.environment,
            "workload_profile": self.workload_profile,
            "population_scope": self.population_scope,
            "target_employees": self.target_employees,
            "processed_employees": self.processed_employees,
            "elapsed_seconds": self.elapsed_seconds,
            "throughput_per_second": self.throughput_per_second,
            "result_fingerprint": self.result_fingerprint.lower(),
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "reviewer_id": self.reviewer_id,
            "approver_id": self.approver_id,
            "tested_at": self.tested_at,
            "approved_at": self.approved_at,
            "status": self.status,
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class LoadValidationBinding:
    binding_version: int
    validation_id: str
    environment: str
    workload_profile: str
    population_scope: str
    target_employees: int
    processed_employees: int
    throughput_per_second: float
    result_fingerprint: str
    authoritative_evidence_id: str
    bound_by: str
    bound_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "validation_id": self.validation_id,
            "environment": self.environment,
            "workload_profile": self.workload_profile,
            "population_scope": self.population_scope,
            "target_employees": self.target_employees,
            "processed_employees": self.processed_employees,
            "throughput_per_second": self.throughput_per_second,
            "result_fingerprint": self.result_fingerprint.lower(),
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


def build_load_validation_binding(
    evidence: LoadValidationEvidence,
    registry: AuthoritativeEvidenceRegistry,
    *,
    bound_by: str,
    bound_at: datetime,
) -> LoadValidationBinding:
    if not bound_by.strip():
        raise LoadValidationEvidenceError("bound_by is required")
    if bound_at.tzinfo is None:
        raise LoadValidationEvidenceError("bound_at must be timezone-aware")

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == evidence.authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise LoadValidationEvidenceError(
            "authoritative load-validation evidence is not present in registry"
        )
    if authoritative.source_type != "load_validation":
        raise LoadValidationEvidenceError(
            "load validation requires load_validation authority"
        )
    if authoritative.status != "accepted":
        raise LoadValidationEvidenceError(
            "authoritative load-validation evidence must be accepted"
        )
    if authoritative.source_sha256.lower() != evidence.fingerprint.lower():
        raise LoadValidationEvidenceError(
            "load-validation fingerprint does not match authoritative evidence SHA-256"
        )
    if authoritative.population_scope.strip() != evidence.population_scope.strip():
        raise LoadValidationEvidenceError(
            "population scope does not match authoritative evidence"
        )

    now = bound_at.astimezone(timezone.utc)
    approved_at = _timestamp("approved_at", authoritative.approved_at) if authoritative.approved_at else None
    if approved_at is None or approved_at > now:
        raise LoadValidationEvidenceError(
            "binding precedes authoritative load-validation approval"
        )
    effective_from = _timestamp("effective_from", authoritative.effective_from)
    if effective_from > now:
        raise LoadValidationEvidenceError(
            "authoritative load-validation evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = _timestamp("effective_to", authoritative.effective_to)
        if effective_to <= now:
            raise LoadValidationEvidenceError(
                "authoritative load-validation evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = _timestamp("expires_at", authoritative.expires_at)
        if expires_at <= now:
            raise LoadValidationEvidenceError(
                "authoritative load-validation evidence is expired"
            )
    if bound_by.strip() == evidence.reviewer_id.strip():
        raise LoadValidationEvidenceError(
            "binding actor must differ from reviewer"
        )
    if bound_by.strip() == evidence.approver_id.strip():
        raise LoadValidationEvidenceError(
            "binding actor must differ from approver"
        )

    return LoadValidationBinding(
        binding_version=1,
        validation_id=evidence.validation_id.strip(),
        environment=evidence.environment.strip(),
        workload_profile=evidence.workload_profile.strip(),
        population_scope=evidence.population_scope.strip(),
        target_employees=evidence.target_employees,
        processed_employees=evidence.processed_employees,
        throughput_per_second=evidence.throughput_per_second,
        result_fingerprint=evidence.result_fingerprint.lower(),
        authoritative_evidence_id=evidence.authoritative_evidence_id.strip(),
        bound_by=bound_by.strip(),
        bound_at=now,
    )
