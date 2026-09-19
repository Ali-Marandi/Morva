from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from morva.runtime.deployment_evidence_bundle import (
    DeploymentEvidenceBundleError,
    verify_deployment_evidence_bundle,
)
from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceAttestation,
    DeploymentEvidenceGateError,
    load_attestation,
)
from morva.runtime.production_promotion_gate import (
    ProductionPromotionGate,
    ProductionPromotionGateError,
    load_authorization,
)


@dataclass(frozen=True, slots=True)
class ProductionPromotionVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_id: str
    bundle_fingerprint: str
    promotion_gate_fingerprint: str
    authorization_id: str
    source_environment: str
    target_environment: str
    deployment_id: str
    deployment_operator: str
    approver: str
    approved_at: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "bundle_id": self.bundle_id,
            "bundle_fingerprint": self.bundle_fingerprint.lower(),
            "promotion_gate_fingerprint": (
                self.promotion_gate_fingerprint.lower()
            ),
            "authorization_id": self.authorization_id,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "deployment_id": self.deployment_id,
            "deployment_operator": self.deployment_operator,
            "approver": self.approver,
            "approved_at": self.approved_at,
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
            "bundle_id": self.bundle_id,
            "bundle_fingerprint": self.bundle_fingerprint,
            "promotion_gate_fingerprint": self.promotion_gate_fingerprint,
            "authorization_id": self.authorization_id,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "deployment_id": self.deployment_id,
            "deployment_operator": self.deployment_operator,
            "approver": self.approver,
            "approved_at": self.approved_at,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_gate(path: Path) -> ProductionPromotionGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionPromotionGateError(
            f"cannot load production promotion gate: {path}"
        ) from exc
    try:
        gate = ProductionPromotionGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            bundle_id=payload["bundle_id"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            release_receipt_fingerprint=payload[
                "release_receipt_fingerprint"
            ],
            deployment_gate_fingerprint=payload[
                "deployment_gate_fingerprint"
            ],
            deployment_verification_fingerprint=payload[
                "deployment_verification_fingerprint"
            ],
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            deployment_id=payload["deployment_id"],
            deployment_operator=payload["deployment_operator"],
            authorization_id=payload["authorization_id"],
            approver=payload["approver"],
            approved_at=payload["approved_at"],
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductionPromotionGateError(
            "production promotion gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise ProductionPromotionGateError(
            "production promotion gate fingerprint mismatch"
        )
    return gate


def _embedded_attestation(bundle_archive: Path) -> dict[str, object]:
    with tarfile.open(bundle_archive, mode="r:gz") as archive:
        member = archive.extractfile("deployment_attestation.json")
        if member is None:
            raise ProductionPromotionGateError(
                "deployment attestation is missing from evidence bundle"
            )
        payload = json.load(member)
    if not isinstance(payload, dict):
        raise ProductionPromotionGateError(
            "embedded deployment attestation must be an object"
        )
    return payload


def _attestation_payload(
    attestation: DeploymentEvidenceAttestation,
) -> dict[str, object]:
    return {
        "attestation_version": attestation.attestation_version,
        "evidence_id": attestation.evidence_id,
        "release_receipt_fingerprint": (
            attestation.release_receipt_fingerprint
        ),
        "environment": attestation.environment,
        "deployment_id": attestation.deployment_id,
        "deployment_status": attestation.deployment_status,
        "deployed_sha": attestation.deployed_sha,
        "deployed_at": attestation.deployed_at,
        "operator": attestation.operator,
        "healthcheck_sha256": attestation.healthcheck_sha256,
        "rollback_target_sha": attestation.rollback_target_sha,
        "rollback_verified": attestation.rollback_verified,
    }


def verify_production_promotion(
    *,
    bundle_archive: Path,
    bundle_metadata: Path,
    promotion_gate: Path,
    authorization: Path,
    deployment_attestation: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ProductionPromotionVerificationReceipt:
    try:
        bundle = verify_deployment_evidence_bundle(
            archive_path=bundle_archive,
            metadata_file=bundle_metadata,
            expected_repository=repository,
            expected_tag=tag,
            expected_sha=candidate_sha,
        )
    except (DeploymentEvidenceBundleError, DeploymentEvidenceGateError) as exc:
        raise ProductionPromotionGateError(
            "M3.58 evidence bundle verification failed"
        ) from exc

    gate = _load_gate(promotion_gate)
    auth = load_authorization(authorization)
    external_attestation = load_attestation(deployment_attestation)
    embedded = _embedded_attestation(bundle_archive)

    if gate.bundle_id != bundle.bundle_id:
        raise ProductionPromotionGateError(
            "promotion gate bundle_id does not match verified bundle"
        )
    if gate.bundle_fingerprint.lower() != bundle.bundle_fingerprint.lower():
        raise ProductionPromotionGateError(
            "promotion gate bundle fingerprint mismatch"
        )
    if gate.repository != repository or gate.tag != tag:
        raise ProductionPromotionGateError(
            "promotion gate repository/tag mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise ProductionPromotionGateError(
            "promotion gate candidate SHA mismatch"
        )
    if gate.release_id != bundle.release_id:
        raise ProductionPromotionGateError(
            "promotion gate release_id mismatch"
        )
    if gate.source_environment != bundle.environment:
        raise ProductionPromotionGateError(
            "promotion gate source environment mismatch"
        )
    if gate.target_environment != "production":
        raise ProductionPromotionGateError(
            "promotion gate target environment is not production"
        )

    if auth.bundle_fingerprint.lower() != bundle.bundle_fingerprint.lower():
        raise ProductionPromotionGateError(
            "authorization bundle fingerprint mismatch"
        )
    if auth.source_environment != gate.source_environment:
        raise ProductionPromotionGateError(
            "authorization source environment mismatch"
        )
    if auth.target_environment != gate.target_environment:
        raise ProductionPromotionGateError(
            "authorization target environment mismatch"
        )
    if auth.authorization_id != gate.authorization_id:
        raise ProductionPromotionGateError("authorization id mismatch")
    if auth.approver != gate.approver or auth.approved_at != gate.approved_at:
        raise ProductionPromotionGateError(
            "authorization approval evidence mismatch"
        )

    if _attestation_payload(external_attestation) != embedded:
        raise ProductionPromotionGateError(
            "external deployment attestation does not match bundle attestation"
        )
    if external_attestation.deployment_id != gate.deployment_id:
        raise ProductionPromotionGateError("deployment id mismatch")
    if external_attestation.operator != gate.deployment_operator:
        raise ProductionPromotionGateError("deployment operator mismatch")
    if gate.deployment_operator == gate.approver:
        raise ProductionPromotionGateError(
            "approver and deployment operator must be distinct"
        )

    return ProductionPromotionVerificationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=gate.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_id=gate.bundle_id,
        bundle_fingerprint=gate.bundle_fingerprint,
        promotion_gate_fingerprint=gate.fingerprint,
        authorization_id=gate.authorization_id,
        source_environment=gate.source_environment,
        target_environment=gate.target_environment,
        deployment_id=gate.deployment_id,
        deployment_operator=gate.deployment_operator,
        approver=gate.approver,
        approved_at=gate.approved_at,
        verified_at=datetime.now(timezone.utc),
    )


def write_verification_receipt(
    receipt: ProductionPromotionVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise ProductionPromotionGateError(
            "production promotion verification receipt is write-once"
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
