from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.external_certification_evidence import REQUIRED_ROLES
from morva.runtime.independent_certification_verifier import (
    IndependentCertificationVerificationError,
)
from morva.runtime.independent_release_lineage_verifier import (
    IndependentLineageVerificationError,
    IndependentLineageVerificationReceipt,
    load_lineage,
    verify_release_lineage,
)
from morva.runtime.production_boundary_policy import (
    PolicyFinding,
    ProductionBoundaryPolicyReceipt,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGateError,
    load_registry,
)


class ProductionReadinessConvergenceError(ValueError):
    """Raised when final production-readiness evidence does not converge."""


@dataclass(frozen=True, slots=True)
class ProductionReadinessConvergence:
    convergence_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    lineage_fingerprint: str
    lineage_verification_fingerprint: str
    full_policy_fingerprint: str
    certification_verification_fingerprint: str
    verified_roles: tuple[str, ...]
    source_environment: str
    target_environment: str
    converged_at: datetime

    def __post_init__(self) -> None:
        if self.convergence_version != 1:
            raise ProductionReadinessConvergenceError(
                "unsupported convergence version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise ProductionReadinessConvergenceError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise ProductionReadinessConvergenceError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise ProductionReadinessConvergenceError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("lineage_fingerprint", self.lineage_fingerprint),
            (
                "lineage_verification_fingerprint",
                self.lineage_verification_fingerprint,
            ),
            ("full_policy_fingerprint", self.full_policy_fingerprint),
            (
                "certification_verification_fingerprint",
                self.certification_verification_fingerprint,
            ),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value.lower()
            ):
                raise ProductionReadinessConvergenceError(
                    f"{name} must be SHA-256"
                )
        if tuple(self.verified_roles) != REQUIRED_ROLES:
            raise ProductionReadinessConvergenceError(
                "verified role set is not canonical"
            )
        if self.source_environment not in {"staging", "pilot"}:
            raise ProductionReadinessConvergenceError(
                "source_environment must be staging or pilot"
            )
        if self.target_environment != "production":
            raise ProductionReadinessConvergenceError(
                "target_environment must be production"
            )
        if self.converged_at.tzinfo is None:
            raise ProductionReadinessConvergenceError(
                "converged_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "convergence_version": self.convergence_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "lineage_fingerprint": self.lineage_fingerprint.lower(),
            "lineage_verification_fingerprint": (
                self.lineage_verification_fingerprint.lower()
            ),
            "full_policy_fingerprint": self.full_policy_fingerprint.lower(),
            "certification_verification_fingerprint": (
                self.certification_verification_fingerprint.lower()
            ),
            "verified_roles": list(self.verified_roles),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "convergence_version": self.convergence_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "lineage_fingerprint": self.lineage_fingerprint,
            "lineage_verification_fingerprint": (
                self.lineage_verification_fingerprint
            ),
            "full_policy_fingerprint": self.full_policy_fingerprint,
            "certification_verification_fingerprint": (
                self.certification_verification_fingerprint
            ),
            "verified_roles": list(self.verified_roles),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "converged_at": self.converged_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_policy(path: Path) -> ProductionBoundaryPolicyReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = ProductionBoundaryPolicyReceipt(
            policy_version=int(payload["policy_version"]),
            repository=payload["repository"],
            scanned_paths=tuple(payload["scanned_paths"]),
            findings=tuple(
                PolicyFinding(**item) for item in payload["findings"]
            ),
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ProductionReadinessConvergenceError(
            "full production-boundary policy receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise ProductionReadinessConvergenceError(
            "full production-boundary policy fingerprint mismatch"
        )
    if not receipt.passed:
        raise ProductionReadinessConvergenceError(
            "full production-boundary policy did not pass"
        )
    return receipt


def _load_lineage_verification_receipt(
    path: Path,
) -> IndependentLineageVerificationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = IndependentLineageVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            lineage_fingerprint=payload["lineage_fingerprint"],
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise ProductionReadinessConvergenceError(
            "M3.71 lineage verification receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise ProductionReadinessConvergenceError(
            "M3.71 lineage verification receipt fingerprint mismatch"
        )
    return receipt


def build_convergence(
    *,
    technical_readiness_gate: Path,
    final_readiness_receipt: Path,
    production_certification_receipt: Path,
    external_registry: Path,
    policy_receipt: Path,
    lineage_manifest: Path,
    lineage_verification_receipt: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
    converged_at: datetime,
) -> ProductionReadinessConvergence:
    try:
        lineage_verification = verify_release_lineage(
            technical_readiness_gate=technical_readiness_gate,
            final_readiness_receipt=final_readiness_receipt,
            production_certification_receipt=production_certification_receipt,
            external_registry=external_registry,
            policy_receipt=policy_receipt,
            lineage_manifest=lineage_manifest,
            repository=repository,
            tag=tag,
            candidate_sha=candidate_sha,
        )
        stored_verification = _load_lineage_verification_receipt(
            lineage_verification_receipt
        )
        registry = load_registry(external_registry)
    except (
        IndependentLineageVerificationError,
        IndependentCertificationVerificationError,
        ProductionCertificationGateError,
        ValueError,
    ) as exc:
        raise ProductionReadinessConvergenceError(
            f"independent lineage/certification evidence verification failed: {exc}"
        ) from exc

    lineage = load_lineage(lineage_manifest)
    policy = _load_policy(policy_receipt)

    if lineage.repository != repository or lineage.tag != tag:
        raise ProductionReadinessConvergenceError(
            "lineage repository/tag mismatch"
        )
    if lineage.candidate_sha.lower() != candidate_sha.lower():
        raise ProductionReadinessConvergenceError(
            "lineage candidate SHA mismatch"
        )
    if (
        lineage_verification.lineage_fingerprint.lower()
        != lineage.fingerprint.lower()
    ):
        raise ProductionReadinessConvergenceError(
            "lineage verification fingerprint mismatch"
        )
    if stored_verification.fingerprint != lineage_verification.fingerprint:
        raise ProductionReadinessConvergenceError(
            "stored M3.71 verification receipt does not match live verification"
        )
    if (
        stored_verification.repository != repository
        or stored_verification.tag != tag
        or stored_verification.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise ProductionReadinessConvergenceError(
            "stored M3.71 verification identity mismatch"
        )
    if lineage.full_policy_fingerprint.lower() != policy.fingerprint.lower():
        raise ProductionReadinessConvergenceError(
            "lineage full-policy fingerprint mismatch"
        )
    if lineage.external_evidence_fingerprint.lower() != registry.fingerprint.lower():
        raise ProductionReadinessConvergenceError(
            "lineage external-evidence fingerprint mismatch"
        )
    if registry.repository != repository:
        raise ProductionReadinessConvergenceError(
            "external registry repository mismatch"
        )
    if registry.candidate_sha.lower() != candidate_sha.lower():
        raise ProductionReadinessConvergenceError(
            "external registry candidate SHA mismatch"
        )
    if tuple(item.role for item in registry.items) != REQUIRED_ROLES:
        raise ProductionReadinessConvergenceError(
            "external registry role set is not canonical"
        )
    if converged_at.tzinfo is None:
        raise ProductionReadinessConvergenceError(
            "convergence time must be timezone-aware"
        )
    if converged_at < lineage_verification.verified_at:
        raise ProductionReadinessConvergenceError(
            "convergence time precedes lineage verification"
        )

    return ProductionReadinessConvergence(
        convergence_version=1,
        repository=repository,
        release_id=lineage.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        lineage_fingerprint=lineage.fingerprint,
        lineage_verification_fingerprint=lineage_verification.fingerprint,
        full_policy_fingerprint=policy.fingerprint,
        certification_verification_fingerprint=(
            lineage.certification_verification_fingerprint
        ),
        verified_roles=tuple(item.role for item in registry.items),
        source_environment=lineage.source_environment,
        target_environment=lineage.target_environment,
        converged_at=converged_at,
    )


def write_convergence(
    convergence: ProductionReadinessConvergence,
    path: Path,
) -> None:
    if path.exists():
        raise ProductionReadinessConvergenceError(
            "production readiness convergence is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            convergence.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
