from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.production_promotion_verifier import (
    ProductionPromotionGateError,
    verify_production_promotion,
)
from morva.runtime.production_promotion_gate import (
    ProductionPromotionGateError as PromotionGateError,
)


REQUIRED_POLICY_PATHS = (
    ".github/workflows/m3-54-release-publication-executor.yml",
    ".github/workflows/m3-55-release-post-publication-integrity.yml",
    ".github/workflows/m3-56-deployment-evidence-gate.yml",
    ".github/workflows/m3-57-independent-deployment-evidence-verifier.yml",
    ".github/workflows/m3-58-deployment-evidence-bundle.yml",
    ".github/workflows/m3-59-production-promotion-gate.yml",
    ".github/workflows/m3-60-independent-production-promotion-verifier.yml",
    ".github/workflows/m3-61-production-boundary-policy.yml",
)


class TechnicalReadinessGateError(ValueError):
    """Raised when technical production readiness cannot be established."""


@dataclass(frozen=True, slots=True)
class TechnicalReadinessPolicyReceipt:
    policy_version: int
    repository: str
    scanned_paths: tuple[str, ...]
    passed: bool
    fingerprint: str


@dataclass(frozen=True, slots=True)
class TechnicalReadinessGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_fingerprint: str
    promotion_gate_fingerprint: str
    promotion_verification_fingerprint: str
    policy_fingerprint: str
    policy_passed: bool
    source_environment: str
    target_environment: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise TechnicalReadinessGateError(
                "unsupported technical readiness gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise TechnicalReadinessGateError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise TechnicalReadinessGateError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise TechnicalReadinessGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            ("promotion_gate_fingerprint", self.promotion_gate_fingerprint),
            (
                "promotion_verification_fingerprint",
                self.promotion_verification_fingerprint,
            ),
            ("policy_fingerprint", self.policy_fingerprint),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef"
                for c in value.lower()
            ):
                raise TechnicalReadinessGateError(
                    f"{name} must be SHA-256"
                )
        if not self.policy_passed:
            raise TechnicalReadinessGateError(
                "policy gate must be passed"
            )
        if self.source_environment not in {"staging", "pilot"}:
            raise TechnicalReadinessGateError(
                "source environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise TechnicalReadinessGateError(
                "target environment must be production"
            )
        if self.checked_at.tzinfo is None:
            raise TechnicalReadinessGateError(
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
            "promotion_gate_fingerprint": (
                self.promotion_gate_fingerprint.lower()
            ),
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint.lower()
            ),
            "policy_fingerprint": self.policy_fingerprint.lower(),
            "policy_passed": self.policy_passed,
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
            "promotion_gate_fingerprint": self.promotion_gate_fingerprint,
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint
            ),
            "policy_fingerprint": self.policy_fingerprint,
            "policy_passed": self.policy_passed,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "checked_at": self.checked_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_policy_receipt(path: Path) -> TechnicalReadinessPolicyReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TechnicalReadinessGateError(
            "technical readiness policy receipt is invalid"
        ) from exc

    try:
        version = int(payload["policy_version"])
        repository = payload["repository"]
        scanned_paths = tuple(sorted(set(payload["scanned_paths"])))
        passed = payload["passed"]
        fingerprint = payload["fingerprint"]
        findings = payload["findings"]
    except (KeyError, TypeError, ValueError) as exc:
        raise TechnicalReadinessGateError(
            "technical readiness policy receipt structure is invalid"
        ) from exc

    if version != 1 or not isinstance(repository, str):
        raise TechnicalReadinessGateError(
            "unsupported policy receipt"
        )
    if not scanned_paths or not isinstance(passed, bool):
        raise TechnicalReadinessGateError(
            "policy receipt fields are invalid"
        )
    canonical = {
        "policy_version": version,
        "repository": repository,
        "scanned_paths": list(scanned_paths),
        "findings": findings,
    }
    expected = sha256(
        json.dumps(
            canonical,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if fingerprint != expected:
        raise TechnicalReadinessGateError(
            "policy receipt fingerprint mismatch"
        )
    return TechnicalReadinessPolicyReceipt(
        policy_version=version,
        repository=repository,
        scanned_paths=scanned_paths,
        passed=passed,
        fingerprint=fingerprint,
    )


def build_technical_readiness_gate(
    *,
    bundle_archive: Path,
    bundle_metadata: Path,
    promotion_gate: Path,
    authorization: Path,
    deployment_attestation: Path,
    policy_receipt: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> TechnicalReadinessGate:
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
    except (ProductionPromotionGateError, PromotionGateError, ValueError) as exc:
        raise TechnicalReadinessGateError(
            "M3.59/M3.60 promotion chain verification failed"
        ) from exc

    policy = load_policy_receipt(policy_receipt)
    if policy.repository != repository:
        raise TechnicalReadinessGateError(
            "policy receipt repository mismatch"
        )
    if not policy.passed:
        raise TechnicalReadinessGateError(
            "production-boundary policy has findings"
        )
    if tuple(policy.scanned_paths) != REQUIRED_POLICY_PATHS:
        raise TechnicalReadinessGateError(
            "policy receipt does not cover the complete M3.54-M3.61 workflow set"
        )

    return TechnicalReadinessGate(
        gate_version=1,
        repository=repository,
        release_id=verification.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_fingerprint=verification.bundle_fingerprint,
        promotion_gate_fingerprint=verification.promotion_gate_fingerprint,
        promotion_verification_fingerprint=verification.fingerprint,
        policy_fingerprint=policy.fingerprint,
        policy_passed=policy.passed,
        source_environment=verification.source_environment,
        target_environment=verification.target_environment,
        checked_at=datetime.now(timezone.utc),
    )


def write_gate(gate: TechnicalReadinessGate, path: Path) -> None:
    if path.exists():
        raise TechnicalReadinessGateError(
            "technical readiness gate is write-once"
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
