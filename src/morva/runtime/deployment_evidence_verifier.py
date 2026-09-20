from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceGate,
    DeploymentEvidenceGateError,
    load_attestation,
    load_release_receipt,
)


@dataclass(frozen=True, slots=True)
class DeploymentEvidenceVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    deployment_gate_fingerprint: str
    release_receipt_fingerprint: str
    evidence_id: str
    environment: str
    deployment_id: str
    deployed_sha: str
    rollback_target_sha: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "deployment_gate_fingerprint": self.deployment_gate_fingerprint.lower(),
            "release_receipt_fingerprint": self.release_receipt_fingerprint.lower(),
            "evidence_id": self.evidence_id,
            "environment": self.environment,
            "deployment_id": self.deployment_id,
            "deployed_sha": self.deployed_sha.lower(),
            "rollback_target_sha": self.rollback_target_sha.lower(),
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
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "deployment_gate_fingerprint": self.deployment_gate_fingerprint,
            "release_receipt_fingerprint": self.release_receipt_fingerprint,
            "evidence_id": self.evidence_id,
            "environment": self.environment,
            "deployment_id": self.deployment_id,
            "deployed_sha": self.deployed_sha,
            "rollback_target_sha": self.rollback_target_sha,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_gate(path: Path) -> DeploymentEvidenceGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentEvidenceGateError(
            f"cannot load deployment evidence gate: {path}"
        ) from exc
    try:
        gate = DeploymentEvidenceGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            post_publication_fingerprint=payload["post_publication_fingerprint"],
            evidence_id=payload["evidence_id"],
            environment=payload["environment"],
            deployment_id=payload["deployment_id"],
            deployed_sha=payload["deployed_sha"],
            deployed_at=payload["deployed_at"],
            operator=payload["operator"],
            healthcheck_sha256=payload["healthcheck_sha256"],
            rollback_target_sha=payload["rollback_target_sha"],
            rollback_verified=payload["rollback_verified"],
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DeploymentEvidenceGateError(
            "deployment evidence gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise DeploymentEvidenceGateError(
            "deployment evidence gate fingerprint mismatch"
        )
    return gate


def verify_deployment_evidence(
    *,
    gate_file: Path,
    release_receipt_file: Path,
    attestation_file: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> DeploymentEvidenceVerificationReceipt:
    gate = load_gate(gate_file)
    receipt = load_release_receipt(release_receipt_file)
    attestation = load_attestation(attestation_file)

    expected_gate_values = {
        "repository": repository,
        "release_id": receipt.release_id,
        "tag": tag,
        "candidate_sha": candidate_sha.lower(),
        "post_publication_fingerprint": receipt.fingerprint.lower(),
        "evidence_id": attestation.evidence_id,
        "environment": attestation.environment,
        "deployment_id": attestation.deployment_id,
        "deployed_sha": candidate_sha.lower(),
        "deployed_at": attestation.deployed_at,
        "operator": attestation.operator,
        "healthcheck_sha256": attestation.healthcheck_sha256.lower(),
        "rollback_target_sha": attestation.rollback_target_sha.lower(),
        "rollback_verified": True,
    }
    actual_gate_values = {
        "repository": gate.repository,
        "release_id": gate.release_id,
        "tag": gate.tag,
        "candidate_sha": gate.candidate_sha.lower(),
        "post_publication_fingerprint": gate.post_publication_fingerprint.lower(),
        "evidence_id": gate.evidence_id,
        "environment": gate.environment,
        "deployment_id": gate.deployment_id,
        "deployed_sha": gate.deployed_sha.lower(),
        "deployed_at": gate.deployed_at,
        "operator": gate.operator,
        "healthcheck_sha256": gate.healthcheck_sha256.lower(),
        "rollback_target_sha": gate.rollback_target_sha.lower(),
        "rollback_verified": gate.rollback_verified,
    }
    if actual_gate_values != expected_gate_values:
        raise DeploymentEvidenceGateError(
            "deployment evidence gate does not match receipt and attestation"
        )
    if gate.deployed_sha.lower() != candidate_sha.lower():
        raise DeploymentEvidenceGateError(
            "deployment evidence gate deployed SHA mismatch"
        )

    return DeploymentEvidenceVerificationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=receipt.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        deployment_gate_fingerprint=gate.fingerprint,
        release_receipt_fingerprint=receipt.fingerprint,
        evidence_id=attestation.evidence_id,
        environment=attestation.environment,
        deployment_id=attestation.deployment_id,
        deployed_sha=attestation.deployed_sha,
        rollback_target_sha=attestation.rollback_target_sha,
        verified_at=datetime.now(timezone.utc),
    )


def write_verification_receipt(
    receipt: DeploymentEvidenceVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise DeploymentEvidenceGateError(
            "deployment verification receipt already exists; write-once required"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            receipt.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
