from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json


CANONICAL_REPOSITORY = "Ali-Marandi/Morva"


class IndependentPersistedIntegrationReadinessVerificationError(ValueError):
    """Raised when an M4.22 persisted readiness receipt fails M4.23 verification."""


@dataclass(frozen=True, slots=True)
class IndependentPersistedIntegrationExecutionReadinessVerification:
    repository: str
    candidate_sha: str
    target_environment: str
    assessment_checked_at: datetime
    verified_at: datetime
    created_at: datetime
    assessment_version: int
    evidence_readiness_fingerprint: str
    binding_fingerprint: str
    binding_verification_fingerprint: str
    state: str
    blockers: tuple[str, ...]
    assessment_fingerprint: str
    verification_fingerprint: str

    def __post_init__(self) -> None:
        if self.repository != CANONICAL_REPOSITORY:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "persisted readiness repository must be the canonical repository"
            )
        if self.assessment_version != 1:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "unsupported persisted readiness assessment version"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "target_environment must be staging or pilot"
            )
        for name, value in (
            ("assessment_checked_at", self.assessment_checked_at),
            ("verified_at", self.verified_at),
            ("created_at", self.created_at),
        ):
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise IndependentPersistedIntegrationReadinessVerificationError(
                    f"{name} must be a timezone-aware datetime"
                )
        if self.assessment_checked_at > self.verified_at:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "verification timestamp precedes assessment check time"
            )
        if self.created_at < self.verified_at:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "persistence timestamp precedes verification time"
            )
        for name, value in (
            ("evidence_readiness_fingerprint", self.evidence_readiness_fingerprint),
            ("binding_fingerprint", self.binding_fingerprint),
            (
                "binding_verification_fingerprint",
                self.binding_verification_fingerprint,
            ),
            ("assessment_fingerprint", self.assessment_fingerprint),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IndependentPersistedIntegrationReadinessVerificationError(
                    f"{name} must be SHA-256"
                )
        if self.state not in {"ready", "blocked"}:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "state must be ready or blocked"
            )
        if any(
            not isinstance(blocker, str) or not blocker.strip()
            for blocker in self.blockers
        ):
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "blockers must be non-empty strings"
            )
        if self.state == "ready" and self.blockers:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "ready persisted assessment cannot contain blockers"
            )
        if self.state == "blocked" and not self.blockers:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                "blocked persisted assessment must contain blockers"
            )

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    @property
    def independent_verification_fingerprint(self) -> str:
        payload = {
            "assessment_fingerprint": self.assessment_fingerprint.lower(),
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
    def independent_assessment_fingerprint(self) -> str:
        payload = {
            "assessment_version": self.assessment_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "checked_at": self.assessment_checked_at.astimezone(
                timezone.utc
            ).isoformat(),
            "evidence_readiness_fingerprint": (
                self.evidence_readiness_fingerprint.lower()
            ),
            "binding_fingerprint": self.binding_fingerprint.lower(),
            "binding_verification_fingerprint": (
                self.binding_verification_fingerprint.lower()
            ),
            "state": self.state,
            "blockers": list(self.blockers),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "assessment_version": self.assessment_version,
            "assessment_checked_at": self.assessment_checked_at.astimezone(
                timezone.utc
            ).isoformat(),
            "verified_at": self.verified_at.astimezone(timezone.utc).isoformat(),
            "created_at": self.created_at.astimezone(timezone.utc).isoformat(),
            "evidence_readiness_fingerprint": (
                self.evidence_readiness_fingerprint.lower()
            ),
            "binding_fingerprint": self.binding_fingerprint.lower(),
            "binding_verification_fingerprint": (
                self.binding_verification_fingerprint.lower()
            ),
            "state": self.state,
            "blockers": list(self.blockers),
            "ready": self.ready,
            "assessment_fingerprint": self.assessment_fingerprint.lower(),
            "verification_fingerprint": self.verification_fingerprint.lower(),
            "independent_assessment_fingerprint": (
                self.independent_assessment_fingerprint
            ),
            "independent_verification_fingerprint": (
                self.independent_verification_fingerprint
            ),
            "verified": True,
        }


def verify_persisted_integration_execution_readiness(
    *,
    repository: str,
    candidate_sha: str,
    target_environment: str,
    assessment_version: int,
    assessment_checked_at: datetime,
    verified_at: datetime,
    created_at: datetime,
    evidence_readiness_fingerprint: str,
    binding_fingerprint: str,
    binding_verification_fingerprint: str,
    state: str,
    blockers: tuple[str, ...],
    assessment_fingerprint: str,
    verification_fingerprint: str,
) -> IndependentPersistedIntegrationExecutionReadinessVerification:
    for name, value in (
        ("assessment_checked_at", assessment_checked_at),
        ("verified_at", verified_at),
        ("created_at", created_at),
    ):
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise IndependentPersistedIntegrationReadinessVerificationError(
                f"{name} must be a timezone-aware datetime"
            )

    verification = IndependentPersistedIntegrationExecutionReadinessVerification(
        repository=repository,
        candidate_sha=candidate_sha.lower(),
        target_environment=target_environment,
        assessment_checked_at=assessment_checked_at.astimezone(timezone.utc),
        verified_at=verified_at.astimezone(timezone.utc),
        created_at=created_at.astimezone(timezone.utc),
        assessment_version=assessment_version,
        evidence_readiness_fingerprint=evidence_readiness_fingerprint.lower(),
        binding_fingerprint=binding_fingerprint.lower(),
        binding_verification_fingerprint=binding_verification_fingerprint.lower(),
        state=state,
        blockers=tuple(blockers),
        assessment_fingerprint=assessment_fingerprint.lower(),
        verification_fingerprint=verification_fingerprint.lower(),
    )
    if (
        verification.assessment_fingerprint
        != verification.independent_assessment_fingerprint
    ):
        raise IndependentPersistedIntegrationReadinessVerificationError(
            "persisted assessment fingerprint mismatch"
        )
    if (
        verification.verification_fingerprint
        != verification.independent_verification_fingerprint
    ):
        raise IndependentPersistedIntegrationReadinessVerificationError(
            "persisted verification fingerprint mismatch"
        )
    return verification
