from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.evidence_readiness import EvidenceReadinessAssessment
from morva.runtime.integration_execution_evidence_binding_verifier import (
    IntegrationExecutionEvidenceBindingVerification,
)


class IntegrationExecutionReadinessAssessmentError(ValueError):
    """Raised when integration execution readiness cannot be assessed safely."""


@dataclass(frozen=True, slots=True)
class IntegrationExecutionReadinessAssessment:
    assessment_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    checked_at: datetime
    evidence_readiness_fingerprint: str
    binding_fingerprint: str
    binding_verification_fingerprint: str
    state: str
    blockers: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.assessment_version != 1:
            raise IntegrationExecutionReadinessAssessmentError(
                "unsupported integration execution readiness assessment version"
            )
        if not self.repository.strip():
            raise IntegrationExecutionReadinessAssessmentError(
                "repository is required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise IntegrationExecutionReadinessAssessmentError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IntegrationExecutionReadinessAssessmentError(
                "target_environment must be staging or pilot"
            )
        if self.checked_at.tzinfo is None:
            raise IntegrationExecutionReadinessAssessmentError(
                "checked_at must be timezone-aware"
            )
        for name, value in (
            ("evidence_readiness_fingerprint", self.evidence_readiness_fingerprint),
            ("binding_fingerprint", self.binding_fingerprint),
            ("binding_verification_fingerprint", self.binding_verification_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef"
                for char in value.lower()
            ):
                raise IntegrationExecutionReadinessAssessmentError(
                    f"{name} must be SHA-256"
                )
        if self.state not in {"ready", "blocked"}:
            raise IntegrationExecutionReadinessAssessmentError(
                "state must be ready or blocked"
            )
        if self.state == "ready" and self.blockers:
            raise IntegrationExecutionReadinessAssessmentError(
                "ready assessment cannot contain blockers"
            )
        if self.state == "blocked" and not self.blockers:
            raise IntegrationExecutionReadinessAssessmentError(
                "blocked assessment must contain blockers"
            )

    @property
    def ready(self) -> bool:
        return self.state == "ready"

    def to_payload(self) -> dict[str, object]:
        return {
            "assessment_version": self.assessment_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "checked_at": self.checked_at.astimezone(timezone.utc).isoformat(),
            "evidence_readiness_fingerprint": self.evidence_readiness_fingerprint,
            "binding_fingerprint": self.binding_fingerprint,
            "binding_verification_fingerprint": self.binding_verification_fingerprint,
            "state": self.state,
            "blockers": list(self.blockers),
            "ready": self.ready,
            "fingerprint": self.fingerprint,
        }


def build_integration_execution_readiness_assessment(
    evidence_readiness: EvidenceReadinessAssessment,
    binding_verification: IntegrationExecutionEvidenceBindingVerification,
    *,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> IntegrationExecutionReadinessAssessment:
    if checked_at.tzinfo is None:
        raise IntegrationExecutionReadinessAssessmentError(
            "checked_at must be timezone-aware"
        )

    binding = binding_verification.binding
    blockers: list[str] = []

    if binding.repository != repository:
        blockers.append("REPOSITORY_MISMATCH")
    if binding.candidate_sha.lower() != candidate_sha.lower():
        blockers.append("CANDIDATE_SHA_MISMATCH")
    if binding.registry_fingerprint.lower() != evidence_readiness.registry_fingerprint.lower():
        blockers.append("REGISTRY_FINGERPRINT_MISMATCH")
    if binding_verification.verified_at > checked_at:
        blockers.append("VERIFICATION_TIME_IN_FUTURE")
    if not evidence_readiness.complete:
        blockers.append("AUTHORITATIVE_EVIDENCE_CLOSURE_INCOMPLETE")

    state = "ready" if not blockers else "blocked"
    fingerprint = _assessment_fingerprint(
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=binding.target_environment,
        checked_at=checked_at,
        evidence_readiness_fingerprint=evidence_readiness.fingerprint,
        binding_fingerprint=binding.fingerprint,
        binding_verification_fingerprint=binding_verification.fingerprint,
        state=state,
        blockers=tuple(blockers),
    )
    return IntegrationExecutionReadinessAssessment(
        assessment_version=1,
        repository=repository,
        candidate_sha=candidate_sha.lower(),
        target_environment=binding.target_environment,
        checked_at=checked_at,
        evidence_readiness_fingerprint=evidence_readiness.fingerprint,
        binding_fingerprint=binding.fingerprint,
        binding_verification_fingerprint=binding_verification.fingerprint,
        state=state,
        blockers=tuple(blockers),
        fingerprint=fingerprint,
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
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
