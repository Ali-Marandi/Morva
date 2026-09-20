from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.external_certification_evidence import (
    ExternalCertificationEvidenceError,
)
from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationError,
    FinalReadinessVerificationReceipt,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGateError,
)
from morva.runtime.production_promotion_gate import (
    ProductionPromotionGateError,
)
from morva.runtime.technical_readiness_gate import (
    TechnicalReadinessGate,
    TechnicalReadinessGateError,
    load_policy_receipt,
)


class ReleaseLineageError(ValueError):
    """Raised when production release evidence lineage is inconsistent."""


@dataclass(frozen=True, slots=True)
class ProductionReleaseLineage:
    lineage_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_fingerprint: str
    technical_readiness_fingerprint: str
    freshness_gate_fingerprint: str
    final_readiness_fingerprint: str
    external_evidence_fingerprint: str
    certification_verification_fingerprint: str
    policy_fingerprint: str
    source_environment: str
    target_environment: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.lineage_version != 2:
            raise ReleaseLineageError("unsupported lineage version")
        if not self.repository.strip() or not self.release_id.strip():
            raise ReleaseLineageError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise ReleaseLineageError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef" for c in self.candidate_sha.lower()
        ):
            raise ReleaseLineageError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("bundle_fingerprint", self.bundle_fingerprint),
            (
                "technical_readiness_fingerprint",
                self.technical_readiness_fingerprint,
            ),
            (
                "freshness_gate_fingerprint",
                self.freshness_gate_fingerprint,
            ),
            (
                "final_readiness_fingerprint",
                self.final_readiness_fingerprint,
            ),
            (
                "external_evidence_fingerprint",
                self.external_evidence_fingerprint,
            ),
            (
                "certification_verification_fingerprint",
                self.certification_verification_fingerprint,
            ),
            ("policy_fingerprint", self.policy_fingerprint),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value.lower()
            ):
                raise ReleaseLineageError(f"{name} must be SHA-256")
        if self.source_environment not in {"staging", "pilot"}:
            raise ReleaseLineageError(
                "source_environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise ReleaseLineageError(
                "target_environment must be production"
            )
        if self.verified_at.tzinfo is None:
            raise ReleaseLineageError(
                "verified_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "lineage_version": self.lineage_version,
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
            "final_readiness_fingerprint": (
                self.final_readiness_fingerprint.lower()
            ),
            "external_evidence_fingerprint": (
                self.external_evidence_fingerprint.lower()
            ),
            "certification_verification_fingerprint": (
                self.certification_verification_fingerprint.lower()
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
            "lineage_version": self.lineage_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "bundle_fingerprint": self.bundle_fingerprint,
            "technical_readiness_fingerprint": (
                self.technical_readiness_fingerprint
            ),
            "freshness_gate_fingerprint": self.freshness_gate_fingerprint,
            "final_readiness_fingerprint": self.final_readiness_fingerprint,
            "external_evidence_fingerprint": (
                self.external_evidence_fingerprint
            ),
            "certification_verification_fingerprint": (
                self.certification_verification_fingerprint
            ),
            "policy_fingerprint": self.policy_fingerprint,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_technical_gate(path: Path) -> TechnicalReadinessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
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
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        TechnicalReadinessGateError,
    ) as exc:
        raise ReleaseLineageError(
            "technical readiness gate is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise ReleaseLineageError(
            "technical readiness gate fingerprint mismatch"
        )
    return gate


def _load_final_receipt(path: Path) -> FinalReadinessVerificationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = FinalReadinessVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            technical_gate_fingerprint=payload[
                "technical_gate_fingerprint"
            ],
            freshness_gate_fingerprint=payload[
                "freshness_gate_fingerprint"
            ],
            final_gate_fingerprint=payload["final_gate_fingerprint"],
            policy_fingerprint=payload["policy_fingerprint"],
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        FinalReadinessVerificationError,
    ) as exc:
        raise ReleaseLineageError(
            "final readiness receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise ReleaseLineageError(
            "final readiness receipt fingerprint mismatch"
        )
    return receipt


def _load_certification_receipt(path: Path):
    try:
        from morva.runtime.independent_certification_verifier import (
            IndependentCertificationVerificationReceipt,
        )

        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = IndependentCertificationVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            final_readiness_fingerprint=payload[
                "final_readiness_fingerprint"
            ],
            external_evidence_fingerprint=payload[
                "external_evidence_fingerprint"
            ],
            certification_gate_fingerprint=payload[
                "certification_gate_fingerprint"
            ],
            verified_roles=tuple(payload["verified_roles"]),
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        ProductionCertificationGateError,
    ) as exc:
        raise ReleaseLineageError(
            "production certification receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise ReleaseLineageError(
            "production certification receipt fingerprint mismatch"
        )
    return receipt


def _load_registry_fingerprint(path: Path):
    try:
        from morva.runtime.production_certification_gate import load_registry

        registry = load_registry(path)
    except (
        OSError,
        ValueError,
        ExternalCertificationEvidenceError,
        ProductionCertificationGateError,
    ) as exc:
        raise ReleaseLineageError(
            "external evidence registry is invalid"
        ) from exc
    return registry


def build_release_lineage(
    *,
    technical_readiness_gate: Path,
    final_readiness_receipt: Path,
    production_certification_receipt: Path,
    external_registry: Path,
    policy_receipt: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
    verified_at: datetime,
) -> ProductionReleaseLineage:
    technical = _load_technical_gate(technical_readiness_gate)
    final = _load_final_receipt(final_readiness_receipt)
    certification = _load_certification_receipt(
        production_certification_receipt
    )
    registry = _load_registry_fingerprint(external_registry)
    try:
        policy = load_policy_receipt(policy_receipt)
    except (OSError, ValueError, TechnicalReadinessGateError) as exc:
        raise ReleaseLineageError("policy receipt is invalid") from exc

    expected_identity = (repository, tag, candidate_sha.lower())
    actual_identities = {
        "technical": (
            technical.repository,
            technical.tag,
            technical.candidate_sha.lower(),
        ),
        "final": (
            final.repository,
            final.tag,
            final.candidate_sha.lower(),
        ),
        "certification": (
            certification.repository,
            certification.tag,
            certification.candidate_sha.lower(),
        ),
        "registry": (
            registry.repository,
            None,
            registry.candidate_sha.lower(),
        ),
        "policy": (policy.repository, None, None),
    }
    if actual_identities["technical"] != expected_identity:
        raise ReleaseLineageError("technical readiness identity mismatch")
    if actual_identities["final"] != expected_identity:
        raise ReleaseLineageError("final readiness identity mismatch")
    if actual_identities["certification"] != expected_identity:
        raise ReleaseLineageError("certification identity mismatch")
    if actual_identities["registry"][0] != repository:
        raise ReleaseLineageError("registry repository mismatch")
    if actual_identities["registry"][2] != candidate_sha.lower():
        raise ReleaseLineageError("registry candidate SHA mismatch")
    if policy.repository != repository or not policy.passed:
        raise ReleaseLineageError("production-boundary policy did not pass")

    if final.technical_gate_fingerprint.lower() != technical.fingerprint.lower():
        raise ReleaseLineageError(
            "final receipt does not bind technical readiness gate"
        )
    if (
        certification.final_readiness_fingerprint.lower()
        != final.fingerprint.lower()
    ):
        raise ReleaseLineageError(
            "certification receipt does not bind final readiness"
        )
    if (
        certification.external_evidence_fingerprint.lower()
        != registry.fingerprint.lower()
    ):
        raise ReleaseLineageError(
            "certification receipt does not bind external registry"
        )
    if final.policy_fingerprint.lower() != technical.policy_fingerprint.lower():
        raise ReleaseLineageError(
            "final and technical policy fingerprints differ"
        )
    if policy.fingerprint.lower() != technical.policy_fingerprint.lower():
        raise ReleaseLineageError(
            "policy receipt does not bind technical readiness"
        )
    if certification.verified_roles != tuple(
        registry_item.role for registry_item in registry.items
    ):
        raise ReleaseLineageError(
            "certification roles do not match external registry"
        )
    if technical.source_environment != final.source_environment:
        raise ReleaseLineageError(
            "source environment mismatch"
        )
    if final.source_environment != certification.source_environment if hasattr(certification, "source_environment") else False:
        raise ReleaseLineageError("certification source environment mismatch")
    if final.target_environment != "production":
        raise ReleaseLineageError(
            "lineage target environment must be production"
        )
    if verified_at.tzinfo is None:
        raise ReleaseLineageError(
            "verified_at must be timezone-aware"
        )
    if verified_at < final.verified_at:
        raise ReleaseLineageError(
            "lineage verification precedes final readiness verification"
        )

    return ProductionReleaseLineage(
        lineage_version=2,
        repository=repository,
        release_id=final.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_fingerprint=technical.bundle_fingerprint,
        technical_readiness_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=final.freshness_gate_fingerprint,
        final_readiness_fingerprint=final.fingerprint,
        external_evidence_fingerprint=registry.fingerprint,
        certification_verification_fingerprint=certification.fingerprint,
        policy_fingerprint=policy.fingerprint,
        source_environment=final.source_environment,
        target_environment=final.target_environment,
        verified_at=verified_at,
    )


def write_lineage(
    lineage: ProductionReleaseLineage,
    path: Path,
) -> None:
    if path.exists():
        raise ReleaseLineageError(
            "release lineage manifest is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            lineage.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
