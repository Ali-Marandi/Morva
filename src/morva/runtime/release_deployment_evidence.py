from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.release_post_publication import (
    ReleasePostPublicationError,
    ReleasePostPublicationReceipt,
)


class DeploymentEvidenceGateError(ValueError):
    """Raised when deployment evidence cannot be accepted."""


@dataclass(frozen=True, slots=True)
class DeploymentEvidenceAttestation:
    attestation_version: int
    evidence_id: str
    release_receipt_fingerprint: str
    environment: str
    deployment_id: str
    deployment_status: str
    deployed_sha: str
    deployed_at: str
    operator: str
    healthcheck_sha256: str
    rollback_target_sha: str
    rollback_verified: bool

    def __post_init__(self) -> None:
        if self.attestation_version != 1:
            raise DeploymentEvidenceGateError(
                "unsupported deployment attestation version"
            )
        if not self.evidence_id.strip():
            raise DeploymentEvidenceGateError("evidence_id is required")
        if (
            len(self.release_receipt_fingerprint) != 64
            or any(
                c not in "0123456789abcdef"
                for c in self.release_receipt_fingerprint.lower()
            )
        ):
            raise DeploymentEvidenceGateError(
                "release_receipt_fingerprint must be SHA-256"
            )
        if self.environment not in {"staging", "pilot", "production"}:
            raise DeploymentEvidenceGateError("unsupported deployment environment")
        if not self.deployment_id.strip():
            raise DeploymentEvidenceGateError("deployment_id is required")
        if self.deployment_status != "succeeded":
            raise DeploymentEvidenceGateError(
                "deployment_status must be succeeded"
            )
        if len(self.deployed_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.deployed_sha.lower()
        ):
            raise DeploymentEvidenceGateError(
                "deployed_sha must be a Git commit SHA-1"
            )
        if not self.deployed_at.strip():
            raise DeploymentEvidenceGateError("deployed_at is required")
        if not self.operator.strip():
            raise DeploymentEvidenceGateError("operator is required")
        if len(self.healthcheck_sha256) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.healthcheck_sha256.lower()
        ):
            raise DeploymentEvidenceGateError(
                "healthcheck_sha256 must be SHA-256"
            )
        if len(self.rollback_target_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.rollback_target_sha.lower()
        ):
            raise DeploymentEvidenceGateError(
                "rollback_target_sha must be a Git commit SHA-1"
            )
        if not isinstance(self.rollback_verified, bool):
            raise DeploymentEvidenceGateError(
                "rollback_verified must be Boolean"
            )


@dataclass(frozen=True, slots=True)
class DeploymentEvidenceGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    post_publication_fingerprint: str
    evidence_id: str
    environment: str
    deployment_id: str
    deployed_sha: str
    deployed_at: str
    operator: str
    healthcheck_sha256: str
    rollback_target_sha: str
    rollback_verified: bool
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise DeploymentEvidenceGateError(
                "unsupported deployment evidence gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise DeploymentEvidenceGateError(
                "repository and release_id are required"
            )
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise DeploymentEvidenceGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("post_publication_fingerprint", self.post_publication_fingerprint),
            ("healthcheck_sha256", self.healthcheck_sha256),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef"
                for c in value.lower()
            ):
                raise DeploymentEvidenceGateError(
                    f"{name} must be SHA-256"
                )
        if len(self.deployed_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.deployed_sha.lower()
        ):
            raise DeploymentEvidenceGateError(
                "deployed_sha must be a Git commit SHA-1"
            )
        if len(self.rollback_target_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.rollback_target_sha.lower()
        ):
            raise DeploymentEvidenceGateError(
                "rollback_target_sha must be a Git commit SHA-1"
            )
        if self.environment not in {"staging", "pilot", "production"}:
            raise DeploymentEvidenceGateError(
                "unsupported deployment environment"
            )
        if not self.evidence_id.strip() or not self.deployment_id.strip():
            raise DeploymentEvidenceGateError(
                "evidence_id and deployment_id are required"
            )
        if not self.operator.strip() or not self.deployed_at.strip():
            raise DeploymentEvidenceGateError(
                "operator and deployed_at are required"
            )
        if not isinstance(self.rollback_verified, bool):
            raise DeploymentEvidenceGateError(
                "rollback_verified must be Boolean"
            )
        if not self.rollback_verified:
            raise DeploymentEvidenceGateError(
                "rollback verification is required"
            )
        if self.verified_at.tzinfo is None:
            raise DeploymentEvidenceGateError(
                "verified_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "post_publication_fingerprint": self.post_publication_fingerprint.lower(),
            "evidence_id": self.evidence_id,
            "environment": self.environment,
            "deployment_id": self.deployment_id,
            "deployed_sha": self.deployed_sha.lower(),
            "deployed_at": self.deployed_at,
            "operator": self.operator,
            "healthcheck_sha256": self.healthcheck_sha256.lower(),
            "rollback_target_sha": self.rollback_target_sha.lower(),
            "rollback_verified": self.rollback_verified,
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
            "post_publication_fingerprint": self.post_publication_fingerprint,
            "evidence_id": self.evidence_id,
            "environment": self.environment,
            "deployment_id": self.deployment_id,
            "deployed_sha": self.deployed_sha,
            "deployed_at": self.deployed_at,
            "operator": self.operator,
            "healthcheck_sha256": self.healthcheck_sha256,
            "rollback_target_sha": self.rollback_target_sha,
            "rollback_verified": self.rollback_verified,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_release_receipt(path: Path) -> ReleasePostPublicationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceGateError(
            f"cannot load release verification receipt: {path}"
        ) from exc
    try:
        assets = tuple(
            {
                "name": item["name"],
                "size_bytes": int(item["size_bytes"]),
                "digest": item["digest"],
            }
            for item in payload["assets"]
        )
        from morva.runtime.release_post_publication import ReleaseAssetIntegrity

        asset_objects = tuple(ReleaseAssetIntegrity(**asset) for asset in assets)
        verified_at = datetime.fromisoformat(payload["verified_at"])
        receipt = ReleasePostPublicationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            artifact_id=payload["artifact_id"],
            artifact_fingerprint=payload["artifact_fingerprint"],
            archive_sha256=payload["archive_sha256"],
            archive_size_bytes=int(payload["archive_size_bytes"]),
            gate_fingerprint=payload["gate_fingerprint"],
            github_release_id=int(payload["github_release_id"]),
            github_release_url=payload["github_release_url"],
            github_release_name=payload["github_release_name"],
            github_target_commitish=payload["github_target_commitish"],
            published_at=payload["published_at"],
            assets=asset_objects,
            verified_at=verified_at,
        )
    except (KeyError, TypeError, ValueError, ReleasePostPublicationError) as exc:
        raise DeploymentEvidenceGateError(
            "release verification receipt structure is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise DeploymentEvidenceGateError(
            "release verification receipt fingerprint mismatch"
        )
    return receipt


def load_attestation(path: Path) -> DeploymentEvidenceAttestation:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceGateError(
            f"cannot load deployment attestation: {path}"
        ) from exc
    try:
        return DeploymentEvidenceAttestation(
            attestation_version=int(payload["attestation_version"]),
            evidence_id=payload["evidence_id"],
            release_receipt_fingerprint=payload["release_receipt_fingerprint"],
            environment=payload["environment"],
            deployment_id=payload["deployment_id"],
            deployment_status=payload["deployment_status"],
            deployed_sha=payload["deployed_sha"],
            deployed_at=payload["deployed_at"],
            operator=payload["operator"],
            healthcheck_sha256=payload["healthcheck_sha256"],
            rollback_target_sha=payload["rollback_target_sha"],
            rollback_verified=payload["rollback_verified"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentEvidenceGateError(
            "deployment attestation structure is invalid"
        ) from exc


def build_deployment_evidence_gate(
    *,
    receipt: ReleasePostPublicationReceipt,
    attestation: DeploymentEvidenceAttestation,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> DeploymentEvidenceGate:
    if (
        receipt.repository != repository
        or receipt.tag != tag
        or receipt.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise DeploymentEvidenceGateError(
            "release receipt does not match expected repository/tag/SHA"
        )
    if (
        attestation.release_receipt_fingerprint.lower()
        != receipt.fingerprint.lower()
    ):
        raise DeploymentEvidenceGateError(
            "deployment attestation is not bound to release verification receipt"
        )
    if attestation.deployed_sha.lower() != candidate_sha.lower():
        raise DeploymentEvidenceGateError(
            "deployed SHA does not match candidate SHA"
        )
    try:
        datetime.fromisoformat(attestation.deployed_at)
    except ValueError as exc:
        raise DeploymentEvidenceGateError(
            "deployed_at must be an ISO-8601 timestamp"
        ) from exc
    return DeploymentEvidenceGate(
        gate_version=1,
        repository=repository,
        release_id=receipt.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        post_publication_fingerprint=receipt.fingerprint,
        evidence_id=attestation.evidence_id,
        environment=attestation.environment,
        deployment_id=attestation.deployment_id,
        deployed_sha=attestation.deployed_sha,
        deployed_at=attestation.deployed_at,
        operator=attestation.operator,
        healthcheck_sha256=attestation.healthcheck_sha256,
        rollback_target_sha=attestation.rollback_target_sha,
        rollback_verified=attestation.rollback_verified,
        verified_at=datetime.now(timezone.utc),
    )


def write_gate(gate: DeploymentEvidenceGate, path: Path) -> None:
    if path.exists():
        raise DeploymentEvidenceGateError(
            "deployment evidence gate output already exists; write-once required"
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
