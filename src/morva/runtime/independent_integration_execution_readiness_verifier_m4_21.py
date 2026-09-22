from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
    IntegrationExecutionReadinessAssessmentError,
)


class IndependentIntegrationExecutionReadinessVerificationError(ValueError):
    """Raised when an M4.20 assessment fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentIntegrationExecutionReadinessVerification:
    assessment: IntegrationExecutionReadinessAssessment
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.verified_at.tzinfo is None:
            raise IndependentIntegrationExecutionReadinessVerificationError(
                "verified_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "assessment_fingerprint": self.assessment.fingerprint.lower(),
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


def _load_assessment(path: Path) -> IntegrationExecutionReadinessAssessment:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assessment = IntegrationExecutionReadinessAssessment(
            assessment_version=int(payload["assessment_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
            evidence_readiness_fingerprint=payload[
                "evidence_readiness_fingerprint"
            ],
            binding_fingerprint=payload["binding_fingerprint"],
            binding_verification_fingerprint=payload[
                "binding_verification_fingerprint"
            ],
            state=payload["state"],
            blockers=tuple(payload["blockers"]),
            fingerprint=payload["fingerprint"],
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        IntegrationExecutionReadinessAssessmentError,
    ) as exc:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "integration execution readiness assessment structure is invalid"
        ) from exc
    if bool(payload.get("ready")) != assessment.ready:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "integration execution readiness ready flag mismatch"
        )
    return assessment


def _recompute_fingerprint(assessment: IntegrationExecutionReadinessAssessment) -> str:
    payload = {
        "assessment_version": assessment.assessment_version,
        "repository": assessment.repository,
        "candidate_sha": assessment.candidate_sha.lower(),
        "target_environment": assessment.target_environment,
        "checked_at": assessment.checked_at.astimezone(timezone.utc).isoformat(),
        "evidence_readiness_fingerprint": assessment.evidence_readiness_fingerprint.lower(),
        "binding_fingerprint": assessment.binding_fingerprint.lower(),
        "binding_verification_fingerprint": assessment.binding_verification_fingerprint.lower(),
        "state": assessment.state,
        "blockers": list(assessment.blockers),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def verify_integration_execution_readiness_assessment(
    assessment_path: Path,
    *,
    repository: str,
    candidate_sha: str,
    verified_at: datetime,
) -> IndependentIntegrationExecutionReadinessVerification:
    if verified_at.tzinfo is None:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "verified_at must be timezone-aware"
        )

    assessment = _load_assessment(assessment_path)
    if assessment.repository != repository:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "integration readiness assessment repository mismatch"
        )
    if assessment.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "integration readiness assessment candidate SHA mismatch"
        )
    if assessment.checked_at > verified_at:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "verification timestamp precedes assessment check time"
        )

    expected_fingerprint = _recompute_fingerprint(assessment)
    if assessment.fingerprint.lower() != expected_fingerprint:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "integration readiness assessment fingerprint mismatch"
        )

    return IndependentIntegrationExecutionReadinessVerification(
        assessment=assessment,
        verified_at=verified_at.astimezone(timezone.utc),
    )
