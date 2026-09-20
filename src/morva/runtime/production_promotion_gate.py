from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.deployment_evidence_bundle import (
    DeploymentEvidenceBundleError,
    verify_deployment_evidence_bundle,
)
from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceGateError,
    load_attestation,
)


class ProductionPromotionGateError(ValueError):
    """Raised when production-promotion evidence cannot be accepted."""


@dataclass(frozen=True, slots=True)
class ProductionPromotionAuthorization:
    authorization_version: int
    authorization_id: str
    bundle_fingerprint: str
    source_environment: str
    target_environment: str
    approved: bool
    approved_at: str
    approver: str
    scope: str = "github_production_promotion"

    def __post_init__(self) -> None:
        if self.authorization_version != 1:
            raise ProductionPromotionGateError(
                "unsupported production promotion authorization version"
            )
        if not self.authorization_id.strip():
            raise ProductionPromotionGateError(
                "promotion authorization id is required"
            )
        if len(self.bundle_fingerprint) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.bundle_fingerprint.lower()
        ):
            raise ProductionPromotionGateError(
                "bundle_fingerprint must be SHA-256"
            )
        if self.source_environment not in {"staging", "pilot"}:
            raise ProductionPromotionGateError(
                "source_environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise ProductionPromotionGateError(
                "target_environment must be production"
            )
        if not isinstance(self.approved, bool):
            raise ProductionPromotionGateError("approved must be Boolean")
        if not self.approved:
            raise ProductionPromotionGateError(
                "production promotion authorization is not approved"
            )
        if not self.approved_at.strip():
            raise ProductionPromotionGateError("approved_at is required")
        try:
            approved_at = datetime.fromisoformat(self.approved_at)
        except ValueError as exc:
            raise ProductionPromotionGateError(
                "approved_at must be ISO-8601"
            ) from exc
        if approved_at.tzinfo is None:
            raise ProductionPromotionGateError(
                "approved_at must include a timezone"
            )
        if not self.approver.strip():
            raise ProductionPromotionGateError("approver is required")
        if self.scope != "github_production_promotion":
            raise ProductionPromotionGateError("invalid promotion scope")


@dataclass(frozen=True, slots=True)
class ProductionPromotionGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_id: str
    bundle_fingerprint: str
    release_receipt_fingerprint: str
    deployment_gate_fingerprint: str
    deployment_verification_fingerprint: str
    source_environment: str
    target_environment: str
    deployment_id: str
    deployment_operator: str
    authorization_id: str
    approver: str
    approved_at: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise ProductionPromotionGateError(
                "unsupported production promotion gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise ProductionPromotionGateError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise ProductionPromotionGateError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise ProductionPromotionGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if not self.bundle_id.startswith("morva-deployment-evidence-v1-"):
            raise ProductionPromotionGateError("invalid bundle_id")
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            ("release_receipt_fingerprint", self.release_receipt_fingerprint),
            ("deployment_gate_fingerprint", self.deployment_gate_fingerprint),
            (
                "deployment_verification_fingerprint",
                self.deployment_verification_fingerprint,
            ),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef"
                for c in value.lower()
            ):
                raise ProductionPromotionGateError(
                    f"{name} must be SHA-256"
                )
        if self.source_environment not in {"staging", "pilot"}:
            raise ProductionPromotionGateError(
                "source_environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise ProductionPromotionGateError(
                "target_environment must be production"
            )
        if not self.deployment_id.strip() or not self.deployment_operator.strip():
            raise ProductionPromotionGateError(
                "deployment identity is required"
            )
        if not self.authorization_id.strip() or not self.approver.strip():
            raise ProductionPromotionGateError(
                "promotion authorization identity is required"
            )
        if self.deployment_operator.strip() == self.approver.strip():
            raise ProductionPromotionGateError(
                "approver and deployment operator must be distinct"
            )
        if not self.approved_at.strip():
            raise ProductionPromotionGateError("approved_at is required")
        try:
            approved_at = datetime.fromisoformat(self.approved_at)
        except ValueError as exc:
            raise ProductionPromotionGateError(
                "approved_at must be ISO-8601"
            ) from exc
        if approved_at.tzinfo is None:
            raise ProductionPromotionGateError(
                "approved_at must include a timezone"
            )
        if self.verified_at.tzinfo is None:
            raise ProductionPromotionGateError(
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
            "bundle_id": self.bundle_id,
            "bundle_fingerprint": self.bundle_fingerprint.lower(),
            "release_receipt_fingerprint": self.release_receipt_fingerprint.lower(),
            "deployment_gate_fingerprint": self.deployment_gate_fingerprint.lower(),
            "deployment_verification_fingerprint": (
                self.deployment_verification_fingerprint.lower()
            ),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "deployment_id": self.deployment_id,
            "deployment_operator": self.deployment_operator,
            "authorization_id": self.authorization_id,
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
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "bundle_id": self.bundle_id,
            "bundle_fingerprint": self.bundle_fingerprint,
            "release_receipt_fingerprint": self.release_receipt_fingerprint,
            "deployment_gate_fingerprint": self.deployment_gate_fingerprint,
            "deployment_verification_fingerprint": (
                self.deployment_verification_fingerprint
            ),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "deployment_id": self.deployment_id,
            "deployment_operator": self.deployment_operator,
            "authorization_id": self.authorization_id,
            "approver": self.approver,
            "approved_at": self.approved_at,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_authorization(path: Path) -> ProductionPromotionAuthorization:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionPromotionGateError(
            f"cannot load promotion authorization: {path}"
        ) from exc
    try:
        return ProductionPromotionAuthorization(
            authorization_version=int(payload["authorization_version"]),
            authorization_id=payload["authorization_id"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            approved=payload["approved"],
            approved_at=payload["approved_at"],
            approver=payload["approver"],
            scope=payload.get("scope", "github_production_promotion"),
        )
    except (KeyError, TypeError) as exc:
        raise ProductionPromotionGateError(
            "promotion authorization structure is invalid"
        ) from exc


def _bundle_json(archive: Path) -> dict[str, object]:
    import tarfile

    with tarfile.open(archive, mode="r:gz") as tar:
        gate = tar.extractfile("deployment_evidence_gate.json")
        receipt = tar.extractfile("release_post_publication_receipt.json")
        verification = tar.extractfile(
            "deployment_evidence_verification_receipt.json"
        )
        if gate is None or receipt is None or verification is None:
            raise ProductionPromotionGateError(
                "required bundle evidence source is missing"
            )
        attestation = tar.extractfile("deployment_attestation.json")
        if attestation is None:
            raise ProductionPromotionGateError(
                "deployment attestation is missing from bundle"
            )
        return {
            "gate": json.load(gate),
            "receipt": json.load(receipt),
            "verification": json.load(verification),
            "attestation": json.load(attestation),
        }


def _bundle_fingerprint(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionPromotionGateError(
            "bundle metadata is invalid"
        ) from exc
    value = payload.get("bundle_fingerprint")
    if not isinstance(value, str):
        raise ProductionPromotionGateError(
            "bundle metadata fingerprint is missing"
        )
    return value


def _bundle_evidence_fingerprint(
    archive: Path,
    key: str,
) -> str:
    value = _bundle_json(archive)[key].get("fingerprint")
    if not isinstance(value, str):
        raise ProductionPromotionGateError(
            f"bundle {key} fingerprint is missing"
        )
    return value


def build_production_promotion_gate(
    *,
    bundle_archive: Path,
    bundle_metadata: Path,
    authorization_file: Path,
    deployment_attestation: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ProductionPromotionGate:
    try:
        bundle = verify_deployment_evidence_bundle(
            archive_path=bundle_archive,
            metadata_file=bundle_metadata,
            expected_repository=repository,
            expected_tag=tag,
            expected_sha=candidate_sha,
        )
    except (
        DeploymentEvidenceBundleError,
        DeploymentEvidenceGateError,
        ValueError,
    ) as exc:
        raise ProductionPromotionGateError(
            "M3.58 deployment evidence bundle verification failed"
        ) from exc

    authorization = load_authorization(authorization_file)
    bundle_fingerprint = _bundle_fingerprint(bundle_metadata)
    if bundle_fingerprint.lower() != bundle.bundle_fingerprint.lower():
        raise ProductionPromotionGateError(
            "bundle metadata fingerprint does not match verified bundle"
        )
    if authorization.bundle_fingerprint.lower() != bundle.bundle_fingerprint.lower():
        raise ProductionPromotionGateError(
            "promotion authorization is not bound to the evidence bundle"
        )
    if authorization.source_environment != bundle.environment:
        raise ProductionPromotionGateError(
            "promotion source environment does not match evidence bundle"
        )

    attestation = load_attestation(deployment_attestation)
    payload = _bundle_json(bundle_archive)
    embedded = payload["attestation"]
    embedded_values = {
        "attestation_version": embedded.get("attestation_version"),
        "evidence_id": embedded.get("evidence_id"),
        "release_receipt_fingerprint": embedded.get(
            "release_receipt_fingerprint"
        ),
        "environment": embedded.get("environment"),
        "deployment_id": embedded.get("deployment_id"),
        "deployment_status": embedded.get("deployment_status"),
        "deployed_sha": embedded.get("deployed_sha"),
        "deployed_at": embedded.get("deployed_at"),
        "operator": embedded.get("operator"),
        "healthcheck_sha256": embedded.get("healthcheck_sha256"),
        "rollback_target_sha": embedded.get("rollback_target_sha"),
        "rollback_verified": embedded.get("rollback_verified"),
    }
    attestation_values = {
        "attestation_version": attestation.attestation_version,
        "evidence_id": attestation.evidence_id,
        "release_receipt_fingerprint": attestation.release_receipt_fingerprint,
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
    if embedded_values != attestation_values:
        raise ProductionPromotionGateError(
            "external deployment attestation does not match bundle attestation"
        )
    if attestation.environment != bundle.environment:
        raise ProductionPromotionGateError(
            "deployment attestation environment does not match bundle"
        )
    if attestation.deployed_sha.lower() != candidate_sha.lower():
        raise ProductionPromotionGateError(
            "deployment attestation SHA does not match candidate"
        )
    if attestation.operator.strip() == authorization.approver.strip():
        raise ProductionPromotionGateError(
            "promotion approver and deployment operator must be distinct"
        )
    if payload["receipt"].get("fingerprint") is None:
        raise ProductionPromotionGateError("release receipt fingerprint missing")
    if payload["gate"].get("fingerprint") is None:
        raise ProductionPromotionGateError("deployment gate fingerprint missing")
    if payload["verification"].get("fingerprint") is None:
        raise ProductionPromotionGateError(
            "deployment verification fingerprint missing"
        )

    return ProductionPromotionGate(
        gate_version=1,
        repository=repository,
        release_id=bundle.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_id=bundle.bundle_id,
        bundle_fingerprint=bundle.bundle_fingerprint,
        release_receipt_fingerprint=_bundle_evidence_fingerprint(
            bundle_archive,
            "receipt",
        ),
        deployment_gate_fingerprint=_bundle_evidence_fingerprint(
            bundle_archive,
            "gate",
        ),
        deployment_verification_fingerprint=_bundle_evidence_fingerprint(
            bundle_archive,
            "verification",
        ),
        source_environment=bundle.environment,
        target_environment=authorization.target_environment,
        deployment_id=attestation.deployment_id,
        deployment_operator=attestation.operator,
        authorization_id=authorization.authorization_id,
        approver=authorization.approver,
        approved_at=authorization.approved_at,
        verified_at=datetime.now(timezone.utc),
    )


def write_gate(gate: ProductionPromotionGate, path: Path) -> None:
    if path.exists():
        raise ProductionPromotionGateError(
            "production promotion gate is write-once"
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
