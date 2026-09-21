from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.technical_readiness_gate import (
    TechnicalReadinessGate,
    TechnicalReadinessGateError,
)
from morva.runtime.evidence_freshness_gate import (
    EvidenceFreshnessGate,
    EvidenceFreshnessGateError,
)


class FinalProductionReadinessError(ValueError):
    """Raised when final technical production readiness is inconsistent."""


@dataclass(frozen=True, slots=True)
class FinalProductionReadinessGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_fingerprint: str
    technical_readiness_fingerprint: str
    freshness_gate_fingerprint: str
    policy_fingerprint: str
    source_environment: str
    target_environment: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise FinalProductionReadinessError(
                "unsupported final readiness gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise FinalProductionReadinessError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise FinalProductionReadinessError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise FinalProductionReadinessError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            (
                "technical_readiness_fingerprint",
                self.technical_readiness_fingerprint,
            ),
            ("freshness_gate_fingerprint", self.freshness_gate_fingerprint),
            ("policy_fingerprint", self.policy_fingerprint),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef"
                for c in value.lower()
            ):
                raise FinalProductionReadinessError(
                    f"{name} must be SHA-256"
                )
        if self.source_environment not in {"staging", "pilot"}:
            raise FinalProductionReadinessError(
                "source_environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise FinalProductionReadinessError(
                "target_environment must be production"
            )
        if self.checked_at.tzinfo is None:
            raise FinalProductionReadinessError(
                "checked_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "bundle_fingerprint": self.bundle_fingerprint.lower(),
            "technical_readiness_fingerprint": (
                self.technical_readiness_fingerprint.lower()
            ),
            "freshness_gate_fingerprint": (
                self.freshness_gate_fingerprint.lower()
            ),
            "policy_fingerprint": self.policy_fingerprint.lower(),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "bundle_fingerprint": self.bundle_fingerprint,
            "technical_readiness_fingerprint": (
                self.technical_readiness_fingerprint
            ),
            "freshness_gate_fingerprint": self.freshness_gate_fingerprint,
            "policy_fingerprint": self.policy_fingerprint,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "checked_at": self.checked_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_technical_gate(path: Path) -> TechnicalReadinessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalProductionReadinessError(
            "technical readiness gate is invalid"
        ) from exc
    try:
        gate = TechnicalReadinessGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            promotion_gate_fingerprint=payload["promotion_gate_fingerprint"],
            promotion_verification_fingerprint=(
                payload["promotion_verification_fingerprint"]
            ),
            policy_fingerprint=payload["policy_fingerprint"],
            policy_passed=payload["policy_passed"],
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FinalProductionReadinessError(
            "technical readiness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise FinalProductionReadinessError(
            "technical readiness gate fingerprint mismatch"
        )
    return gate


def _load_freshness_gate(path: Path) -> EvidenceFreshnessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalProductionReadinessError(
            "freshness gate is invalid"
        ) from exc
    try:
        gate = EvidenceFreshnessGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            promotion_verification_fingerprint=(
                payload["promotion_verification_fingerprint"]
            ),
            source_environment=payload["source_environment"],
            published_at=payload["published_at"],
            approved_at=payload["approved_at"],
            deployed_at=payload["deployed_at"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
            max_release_age_hours=int(payload["max_release_age_hours"]),
            max_approval_age_hours=int(payload["max_approval_age_hours"]),
            max_deployment_age_hours=int(
                payload["max_deployment_age_hours"]
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise FinalProductionReadinessError(
            "freshness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise FinalProductionReadinessError(
            "freshness gate fingerprint mismatch"
        )
    return gate


def build_final_readiness_gate(
    *,
    technical_gate: Path,
    freshness_gate: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
    checked_at: datetime,
) -> FinalProductionReadinessGate:
    try:
        technical = _load_technical_gate(technical_gate)
        freshness = _load_freshness_gate(freshness_gate)
    except (
        FinalProductionReadinessError,
        TechnicalReadinessGateError,
        EvidenceFreshnessGateError,
    ) as exc:
        raise FinalProductionReadinessError(str(exc)) from exc

    if not technical.policy_passed:
        raise FinalProductionReadinessError(
            "technical policy gate did not pass"
        )
    if (
        technical.repository != repository
        or technical.tag != tag
        or technical.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise FinalProductionReadinessError(
            "technical readiness identity mismatch"
        )
    if (
        freshness.repository != repository
        or freshness.tag != tag
        or freshness.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise FinalProductionReadinessError(
            "freshness identity mismatch"
        )
    if technical.bundle_fingerprint.lower() != freshness.bundle_fingerprint.lower():
        raise FinalProductionReadinessError(
            "technical and freshness bundle fingerprints differ"
        )
    if (
        technical.promotion_verification_fingerprint.lower()
        != freshness.promotion_verification_fingerprint.lower()
    ):
        raise FinalProductionReadinessError(
            "promotion verification fingerprints differ"
        )
    if technical.source_environment != freshness.source_environment:
        raise FinalProductionReadinessError(
            "source environments differ"
        )
    if technical.target_environment != "production":
        raise FinalProductionReadinessError(
            "technical readiness target is not production"
        )
    if checked_at.tzinfo is None:
        raise FinalProductionReadinessError(
            "checked_at must be timezone-aware"
        )
    if checked_at < technical.checked_at or checked_at < freshness.checked_at:
        raise FinalProductionReadinessError(
            "final check time precedes a preceding readiness check"
        )

    return FinalProductionReadinessGate(
        gate_version=1,
        repository=repository,
        release_id=technical.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_fingerprint=technical.bundle_fingerprint,
        technical_readiness_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=freshness.fingerprint,
        policy_fingerprint=technical.policy_fingerprint,
        source_environment=technical.source_environment,
        target_environment=technical.target_environment,
        checked_at=checked_at,
    )


def write_gate(gate: FinalProductionReadinessGate, path: Path) -> None:
    if path.exists():
        raise FinalProductionReadinessError(
            "final production readiness gate is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            gate.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
