from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.evidence_readiness import (
    EvidenceReadinessAssessment,
    replay_readiness_fingerprint,
)
from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
)
from morva.runtime.readiness_scope_binding_m4_25 import (
    ReadinessScopeBindingError,
    normalize_readiness_scope,
)


class ScopeBoundReadinessConvergenceError(ValueError):
    """Raised when a persisted readiness receipt diverges from current scoped evidence."""


@dataclass(frozen=True, slots=True)
class ScopeBoundReadinessConvergence:
    convergence_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    organization_scope: str
    organization_scope_id: str
    checked_at: datetime
    persisted_verification_fingerprint: str
    persisted_evidence_readiness_fingerprint: str
    current_evidence_readiness_fingerprint: str
    state: str
    blockers: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.convergence_version != 1:
            raise ScopeBoundReadinessConvergenceError(
                "unsupported scope-bound readiness convergence version"
            )
        if not self.repository.strip():
            raise ScopeBoundReadinessConvergenceError("repository is required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise ScopeBoundReadinessConvergenceError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise ScopeBoundReadinessConvergenceError(
                "target_environment must be staging or pilot"
            )
        if self.checked_at.tzinfo is None:
            raise ScopeBoundReadinessConvergenceError(
                "checked_at must be timezone-aware"
            )
        try:
            normalize_readiness_scope(
                self.organization_scope,
                self.organization_scope_id,
            )
        except ReadinessScopeBindingError as exc:
            raise ScopeBoundReadinessConvergenceError(str(exc)) from exc

        for name, value in (
            (
                "persisted_verification_fingerprint",
                self.persisted_verification_fingerprint,
            ),
            (
                "persisted_evidence_readiness_fingerprint",
                self.persisted_evidence_readiness_fingerprint,
            ),
            (
                "current_evidence_readiness_fingerprint",
                self.current_evidence_readiness_fingerprint,
            ),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef"
                for char in value.lower()
            ):
                raise ScopeBoundReadinessConvergenceError(
                    f"{name} must be SHA-256"
                )
        if self.state not in {"converged", "blocked"}:
            raise ScopeBoundReadinessConvergenceError(
                "state must be converged or blocked"
            )
        if self.state == "converged" and self.blockers:
            raise ScopeBoundReadinessConvergenceError(
                "converged result cannot contain blockers"
            )
        if self.state == "blocked" and not self.blockers:
            raise ScopeBoundReadinessConvergenceError(
                "blocked result must contain blockers"
            )

        expected = _fingerprint(
            repository=self.repository,
            candidate_sha=self.candidate_sha,
            target_environment=self.target_environment,
            organization_scope=self.organization_scope,
            organization_scope_id=self.organization_scope_id,
            checked_at=self.checked_at,
            persisted_verification_fingerprint=self.persisted_verification_fingerprint,
            persisted_evidence_readiness_fingerprint=self.persisted_evidence_readiness_fingerprint,
            current_evidence_readiness_fingerprint=self.current_evidence_readiness_fingerprint,
            state=self.state,
            blockers=self.blockers,
        )
        if self.fingerprint.lower() != expected:
            raise ScopeBoundReadinessConvergenceError(
                "scope-bound readiness convergence fingerprint mismatch"
            )

    @property
    def converged(self) -> bool:
        return self.state == "converged"

    def to_payload(self) -> dict[str, object]:
        return {
            "convergence_version": self.convergence_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "organization_scope": self.organization_scope,
            "organization_scope_id": self.organization_scope_id,
            "checked_at": self.checked_at.astimezone(timezone.utc).isoformat(),
            "persisted_verification_fingerprint": self.persisted_verification_fingerprint,
            "persisted_evidence_readiness_fingerprint": (
                self.persisted_evidence_readiness_fingerprint
            ),
            "current_evidence_readiness_fingerprint": (
                self.current_evidence_readiness_fingerprint
            ),
            "state": self.state,
            "blockers": list(self.blockers),
            "converged": self.converged,
            "fingerprint": self.fingerprint,
        }


def build_scope_bound_readiness_convergence(
    verification: IndependentIntegrationExecutionReadinessVerification,
    current_evidence_readiness: EvidenceReadinessAssessment,
    *,
    organization_scope: str,
    organization_scope_id: str,
    checked_at: datetime,
) -> ScopeBoundReadinessConvergence:
    if checked_at.tzinfo is None:
        raise ScopeBoundReadinessConvergenceError(
            "checked_at must be timezone-aware"
        )
    scope, scope_id = _normalize_scope(
        organization_scope,
        organization_scope_id,
    )
    blockers: list[str] = []

    assessment = verification.assessment
    if assessment.repository != current_evidence_readiness.repository:
        blockers.append("REPOSITORY_MISMATCH")
    if assessment.state != "ready":
        blockers.append("PERSISTED_READINESS_NOT_READY")
    if verification.verified_at.astimezone(timezone.utc) > checked_at.astimezone(
        timezone.utc
    ):
        blockers.append("VERIFICATION_TIME_IN_FUTURE")
    if not current_evidence_readiness.complete:
        blockers.append("CURRENT_EVIDENCE_READINESS_INCOMPLETE")
    replayed_current_fingerprint = replay_readiness_fingerprint(
        current_evidence_readiness,
        checked_at=assessment.checked_at,
    )
    if (
        assessment.evidence_readiness_fingerprint.lower()
        != replayed_current_fingerprint.lower()
    ):
        blockers.append("EVIDENCE_READINESS_FINGERPRINT_MISMATCH")

    state = "converged" if not blockers else "blocked"
    fingerprint = _fingerprint(
        repository=assessment.repository,
        candidate_sha=assessment.candidate_sha,
        target_environment=assessment.target_environment,
        organization_scope=scope,
        organization_scope_id=scope_id,
        checked_at=checked_at,
        persisted_verification_fingerprint=verification.fingerprint,
        persisted_evidence_readiness_fingerprint=assessment.evidence_readiness_fingerprint,
        current_evidence_readiness_fingerprint=replayed_current_fingerprint,
        state=state,
        blockers=tuple(blockers),
    )
    return ScopeBoundReadinessConvergence(
        convergence_version=1,
        repository=assessment.repository,
        candidate_sha=assessment.candidate_sha.lower(),
        target_environment=assessment.target_environment,
        organization_scope=scope,
        organization_scope_id=scope_id,
        checked_at=checked_at,
        persisted_verification_fingerprint=verification.fingerprint,
        persisted_evidence_readiness_fingerprint=assessment.evidence_readiness_fingerprint.lower(),
        current_evidence_readiness_fingerprint=replayed_current_fingerprint.lower(),
        state=state,
        blockers=tuple(blockers),
        fingerprint=fingerprint,
    )


def _normalize_scope(scope: str, scope_id: str) -> tuple[str, str]:
    try:
        return normalize_readiness_scope(scope, scope_id)
    except ReadinessScopeBindingError as exc:
        raise ScopeBoundReadinessConvergenceError(str(exc)) from exc


def _fingerprint(
    *,
    repository: str,
    candidate_sha: str,
    target_environment: str,
    organization_scope: str,
    organization_scope_id: str,
    checked_at: datetime,
    persisted_verification_fingerprint: str,
    persisted_evidence_readiness_fingerprint: str,
    current_evidence_readiness_fingerprint: str,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "convergence_version": 1,
        "repository": repository,
        "candidate_sha": candidate_sha.lower(),
        "target_environment": target_environment,
        "organization_scope": organization_scope,
        "organization_scope_id": organization_scope_id,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "persisted_verification_fingerprint": persisted_verification_fingerprint.lower(),
        "persisted_evidence_readiness_fingerprint": (
            persisted_evidence_readiness_fingerprint.lower()
        ),
        "current_evidence_readiness_fingerprint": (
            current_evidence_readiness_fingerprint.lower()
        ),
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
