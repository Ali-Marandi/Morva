from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.production_promotion_verifier import (
    ProductionPromotionGateError,
    verify_production_promotion,
)
from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceGateError,
    load_attestation,
    load_release_receipt,
)


class EvidenceFreshnessGateError(ValueError):
    """Raised when release, approval or deployment evidence is stale."""


@dataclass(frozen=True, slots=True)
class EvidenceFreshnessGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_fingerprint: str
    promotion_verification_fingerprint: str
    published_at: str
    approved_at: str
    deployed_at: str
    checked_at: datetime
    max_release_age_hours: int
    max_approval_age_hours: int
    max_deployment_age_hours: int

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise EvidenceFreshnessGateError(
                "unsupported freshness gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise EvidenceFreshnessGateError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise EvidenceFreshnessGateError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise EvidenceFreshnessGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            (
                "promotion_verification_fingerprint",
                self.promotion_verification_fingerprint,
            ),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef"
                for c in value.lower()
            ):
                raise EvidenceFreshnessGateError(
                    f"{name} must be SHA-256"
                )
        for name, value in (
            ("published_at", self.published_at),
            ("approved_at", self.approved_at),
            ("deployed_at", self.deployed_at),
        ):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as exc:
                raise EvidenceFreshnessGateError(
                    f"{name} must be ISO-8601"
                ) from exc
            if parsed.tzinfo is None:
                raise EvidenceFreshnessGateError(
                    f"{name} must include a timezone"
                )
        if self.checked_at.tzinfo is None:
            raise EvidenceFreshnessGateError(
                "checked_at must be timezone-aware"
            )
        for name, value in (
            ("max_release_age_hours", self.max_release_age_hours),
            ("max_approval_age_hours", self.max_approval_age_hours),
            ("max_deployment_age_hours", self.max_deployment_age_hours),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise EvidenceFreshnessGateError(
                    f"{name} must be a positive integer"
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
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint.lower()
            ),
            "published_at": self.published_at,
            "approved_at": self.approved_at,
            "deployed_at": self.deployed_at,
            "checked_at": self.checked_at.isoformat(),
            "max_release_age_hours": self.max_release_age_hours,
            "max_approval_age_hours": self.max_approval_age_hours,
            "max_deployment_age_hours": self.max_deployment_age_hours,
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
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint
            ),
            "published_at": self.published_at,
            "approved_at": self.approved_at,
            "deployed_at": self.deployed_at,
            "checked_at": self.checked_at.isoformat(),
            "max_release_age_hours": self.max_release_age_hours,
            "max_approval_age_hours": self.max_approval_age_hours,
            "max_deployment_age_hours": self.max_deployment_age_hours,
            "fingerprint": self.fingerprint,
        }


def _age_hours(occurred_at: str, checked_at: datetime) -> float:
    occurred = datetime.fromisoformat(occurred_at)
    if occurred > checked_at:
        raise EvidenceFreshnessGateError(
            "evidence timestamp cannot be in the future"
        )
    return (checked_at - occurred).total_seconds() / 3600


def build_evidence_freshness_gate(
    *,
    bundle_archive: Path,
    bundle_metadata: Path,
    promotion_gate: Path,
    authorization: Path,
    deployment_attestation: Path,
    release_receipt: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
    checked_at: datetime,
    max_release_age_hours: int,
    max_approval_age_hours: int,
    max_deployment_age_hours: int,
) -> EvidenceFreshnessGate:
    try:
        verification = verify_production_promotion(
            bundle_archive=bundle_archive,
            bundle_metadata=bundle_metadata,
            promotion_gate=promotion_gate,
            authorization=authorization,
            deployment_attestation=deployment_attestation,
            repository=repository,
            tag=tag,
            candidate_sha=candidate_sha,
        )
        release = load_release_receipt(release_receipt)
        attestation = load_attestation(deployment_attestation)
    except (ProductionPromotionGateError, DeploymentEvidenceGateError, ValueError) as exc:
        raise EvidenceFreshnessGateError(
            "promotion and deployment evidence verification failed"
        ) from exc

    if release.repository != repository or release.tag != tag:
        raise EvidenceFreshnessGateError(
            "release receipt repository/tag mismatch"
        )
    if release.candidate_sha.lower() != candidate_sha.lower():
        raise EvidenceFreshnessGateError(
            "release receipt candidate SHA mismatch"
        )
    if release.release_id != verification.release_id:
        raise EvidenceFreshnessGateError(
            "release id mismatch"
        )
    if verification.target_environment != "production":
        raise EvidenceFreshnessGateError(
            "production target is required"
        )

    _age_hours(release.published_at, checked_at)
    _age_hours(verification.approved_at, checked_at)
    _age_hours(attestation.deployed_at, checked_at)

    release_age = _age_hours(release.published_at, checked_at)
    approval_age = _age_hours(verification.approved_at, checked_at)
    deployment_age = _age_hours(attestation.deployed_at, checked_at)

    if release_age > max_release_age_hours:
        raise EvidenceFreshnessGateError(
            "release evidence is stale"
        )
    if approval_age > max_approval_age_hours:
        raise EvidenceFreshnessGateError(
            "promotion approval is stale"
        )
    if deployment_age > max_deployment_age_hours:
        raise EvidenceFreshnessGateError(
            "deployment evidence is stale"
        )

    return EvidenceFreshnessGate(
        gate_version=1,
        repository=repository,
        release_id=release.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_fingerprint=verification.bundle_fingerprint,
        promotion_verification_fingerprint=verification.fingerprint,
        published_at=release.published_at,
        approved_at=verification.approved_at,
        deployed_at=attestation.deployed_at,
        checked_at=checked_at,
        max_release_age_hours=max_release_age_hours,
        max_approval_age_hours=max_approval_age_hours,
        max_deployment_age_hours=max_deployment_age_hours,
    )


def write_gate(gate: EvidenceFreshnessGate, path: Path) -> None:
    if path.exists():
        raise EvidenceFreshnessGateError(
            "freshness gate is write-once"
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
