from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Protocol


CANONICAL_REPOSITORY = "Ali-Marandi/Morva"


class PersistedIntegrationExecutionReadinessVerificationError(ValueError):
    """Raised when an M4.22 persisted readiness receipt fails M4.23 verification."""


class PersistedIntegrationExecutionReadinessRecord(Protocol):
    repository: str
    candidate_sha: str
    target_environment: str
    assessment_checked_at: datetime
    verified_at: datetime
    evidence_readiness_fingerprint: str
    binding_fingerprint: str
    binding_verification_fingerprint: str
    state: str
    blockers: list[object] | tuple[object, ...]
    assessment_fingerprint: str
    verification_fingerprint: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class IndependentPersistedIntegrationExecutionReadinessVerification:
    verifier_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    state: str
    blockers: tuple[str, ...]
    assessment_fingerprint: str
    verification_fingerprint: str
    created_at: datetime
    assessment_checked_at: datetime
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.verifier_version != 1:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "unsupported M4.23 verifier version"
            )
        if self.repository != CANONICAL_REPOSITORY:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "repository must be the canonical Morva repository"
            )
        _validate_candidate_sha(self.candidate_sha)
        if self.target_environment not in {"staging", "pilot"}:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "target_environment must be staging or pilot"
            )
        if self.state not in {"ready", "blocked"}:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "state must be ready or blocked"
            )
        if self.state == "ready" and self.blockers:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "ready persisted receipt cannot contain blockers"
            )
        if self.state == "blocked" and not self.blockers:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "blocked persisted receipt must contain blockers"
            )
        for name, value in (("assessment_fingerprint", self.assessment_fingerprint),
                            ("verification_fingerprint", self.verification_fingerprint)):
            _validate_sha256(value, name)
        for name, value in (
            ("created_at", self.created_at),
            ("assessment_checked_at", self.assessment_checked_at),
            ("verified_at", self.verified_at),
        ):
            if value.tzinfo is None:
                raise PersistedIntegrationExecutionReadinessVerificationError(
                    f"{name} must be timezone-aware"
                )
        if self.assessment_checked_at > self.verified_at:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "verification timestamp precedes assessment check time"
            )
        if self.created_at > self.verified_at:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "created timestamp postdates verification timestamp"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "state": self.state,
            "blockers": list(self.blockers),
            "assessment_fingerprint": self.assessment_fingerprint.lower(),
            "verification_fingerprint": self.verification_fingerprint.lower(),
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "assessment_checked_at": self.assessment_checked_at.astimezone(
                timezone.utc
            ).isoformat(),
            "verified_at": self.verified_at.astimezone(timezone.utc).isoformat(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    @property
    def verified(self) -> bool:
        return True

    def to_payload(self) -> dict[str, object]:
        return {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "state": self.state,
            "blockers": list(self.blockers),
            "assessment_fingerprint": self.assessment_fingerprint,
            "verification_fingerprint": self.verification_fingerprint,
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "assessment_checked_at": self.assessment_checked_at.astimezone(
                timezone.utc
            ).isoformat(),
            "verified_at": self.verified_at.astimezone(timezone.utc).isoformat(),
            "verified": self.verified,
            "fingerprint": self.fingerprint,
        }


def verify_persisted_integration_execution_readiness(
    record: PersistedIntegrationExecutionReadinessRecord,
    *,
    repository: str = CANONICAL_REPOSITORY,
    candidate_sha: str | None = None,
    target_environment: str | None = None,
    verified_at: datetime | None = None,
) -> IndependentPersistedIntegrationExecutionReadinessVerification:
    effective_verified_at = (
        record.verified_at if verified_at is None else verified_at
    )
    _validate_timestamp(effective_verified_at, "verified_at")

    if repository != CANONICAL_REPOSITORY:
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "verification requires the canonical repository"
        )
    if record.repository != repository:
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "persisted repository mismatch"
        )
    expected_candidate = record.candidate_sha.lower()
    if candidate_sha is not None:
        _validate_candidate_sha(candidate_sha)
        if expected_candidate != candidate_sha.lower():
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "persisted candidate SHA mismatch"
            )
    if target_environment is not None:
        if target_environment not in {"staging", "pilot"}:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "target_environment must be staging or pilot"
            )
        if record.target_environment != target_environment:
            raise PersistedIntegrationExecutionReadinessVerificationError(
                "persisted target environment mismatch"
            )

    blockers = _normalize_blockers(record.blockers)
    assessment_checked_at = _validate_timestamp(
        record.assessment_checked_at, "assessment_checked_at"
    )
    verified_timestamp = _validate_timestamp(effective_verified_at, "verified_at")
    created_at = _validate_timestamp(record.created_at, "created_at")

    expected_assessment_fingerprint = _assessment_fingerprint(
        repository=record.repository,
        candidate_sha=record.candidate_sha,
        target_environment=record.target_environment,
        checked_at=assessment_checked_at,
        evidence_readiness_fingerprint=record.evidence_readiness_fingerprint,
        binding_fingerprint=record.binding_fingerprint,
        binding_verification_fingerprint=record.binding_verification_fingerprint,
        state=record.state,
        blockers=blockers,
    )
    if record.assessment_fingerprint.lower() != expected_assessment_fingerprint:
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "persisted assessment fingerprint mismatch"
        )

    expected_verification_fingerprint = _verification_fingerprint(
        assessment_fingerprint=expected_assessment_fingerprint,
        verified_at=verified_timestamp,
    )
    if record.verification_fingerprint.lower() != expected_verification_fingerprint:
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "persisted verification fingerprint mismatch"
        )

    return IndependentPersistedIntegrationExecutionReadinessVerification(
        verifier_version=1,
        repository=record.repository,
        candidate_sha=expected_candidate,
        target_environment=record.target_environment,
        state=record.state,
        blockers=blockers,
        assessment_fingerprint=expected_assessment_fingerprint,
        verification_fingerprint=expected_verification_fingerprint,
        created_at=created_at,
        assessment_checked_at=assessment_checked_at,
        verified_at=verified_timestamp,
    )


def _assessment_fingerprint(
    *,
    repository: str,
    candidate_sha: str,
    target_environment: str,
    checked_at: datetime,
    evidence_readiness_fingerprint: str,
    binding_fingerprint: str,
    binding_verification_fingerprint: str,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "assessment_version": 1,
        "repository": repository,
        "candidate_sha": candidate_sha.lower(),
        "target_environment": target_environment,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "evidence_readiness_fingerprint": evidence_readiness_fingerprint.lower(),
        "binding_fingerprint": binding_fingerprint.lower(),
        "binding_verification_fingerprint": binding_verification_fingerprint.lower(),
        "state": state,
        "blockers": list(blockers),
    }
    return _sha256_payload(payload)


def _verification_fingerprint(
    *,
    assessment_fingerprint: str,
    verified_at: datetime,
) -> str:
    return _sha256_payload(
        {
            "assessment_fingerprint": assessment_fingerprint.lower(),
            "verified_at": verified_at.astimezone(timezone.utc).isoformat(),
        }
    )


def _normalize_blockers(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "persisted blockers must be a list or tuple of strings"
        )
    if not all(isinstance(item, str) and item for item in value):
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "persisted blockers must contain only non-empty strings"
        )
    return tuple(value)


def _validate_candidate_sha(value: str) -> None:
    if len(value) != 40 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise PersistedIntegrationExecutionReadinessVerificationError(
            "candidate_sha must be a Git commit SHA-1"
        )


def _validate_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise PersistedIntegrationExecutionReadinessVerificationError(
            f"{name} must be SHA-256"
        )


def _validate_timestamp(value: datetime, name: str) -> datetime:
    if value.tzinfo is None:
        raise PersistedIntegrationExecutionReadinessVerificationError(
            f"{name} must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


def _sha256_payload(payload: dict[str, object]) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
