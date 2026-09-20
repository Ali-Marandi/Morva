from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path


class ReleaseLineageError(ValueError):
    """Raised when the production release evidence lineage is inconsistent."""


@dataclass(frozen=True, slots=True)
class ProductionReleaseLineage:
    lineage_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    bundle_fingerprint: str
    promotion_verification_fingerprint: str
    final_readiness_fingerprint: str
    external_evidence_fingerprint: str
    certification_verification_fingerprint: str
    policy_fingerprint: str
    source_environment: str
    target_environment: str
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.lineage_version != 1:
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
                "promotion_verification_fingerprint",
                self.promotion_verification_fingerprint,
            ),
            ("final_readiness_fingerprint", self.final_readiness_fingerprint),
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
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint.lower()
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
            "promotion_verification_fingerprint": (
                self.promotion_verification_fingerprint
            ),
            "final_readiness_fingerprint": self.final_readiness_fingerprint,
            "external_evidence_fingerprint": self.external_evidence_fingerprint,
            "certification_verification_fingerprint": (
                self.certification_verification_fingerprint
            ),
            "policy_fingerprint": self.policy_fingerprint,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_payload(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseLineageError(f"{label} is invalid") from exc
    if not isinstance(payload, dict):
        raise ReleaseLineageError(f"{label} must be an object")
    return payload


def build_release_lineage(
    *,
    final_readiness_receipt: Path,
    production_certification_receipt: Path,
    external_registry: Path,
    policy_receipt: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
    verified_at: datetime,
) -> ProductionReleaseLineage:
    final_payload = _load_payload(
        final_readiness_receipt,
        "final readiness receipt",
    )
    certification_payload = _load_payload(
        production_certification_receipt,
        "production certification receipt",
    )
    registry_payload = _load_payload(
        external_registry,
        "external evidence registry",
    )
    policy_payload = _load_payload(
        policy_receipt,
        "policy receipt",
    )

    if final_payload.get("repository") != repository:
        raise ReleaseLineageError(
            "final readiness repository mismatch"
        )
    if final_payload.get("tag") != tag:
        raise ReleaseLineageError("final readiness tag mismatch")
    if str(final_payload.get("candidate_sha", "")).lower() != candidate_sha.lower():
        raise ReleaseLineageError(
            "final readiness candidate SHA mismatch"
        )
    if certification_payload.get("repository") != repository:
        raise ReleaseLineageError(
            "certification repository mismatch"
        )
    if certification_payload.get("tag") != tag:
        raise ReleaseLineageError("certification tag mismatch")
    if (
        str(certification_payload.get("candidate_sha", "")).lower()
        != candidate_sha.lower()
    ):
        raise ReleaseLineageError(
            "certification candidate SHA mismatch"
        )
    if registry_payload.get("repository") != repository:
        raise ReleaseLineageError("registry repository mismatch")
    if str(registry_payload.get("candidate_sha", "")).lower() != candidate_sha.lower():
        raise ReleaseLineageError(
            "registry candidate SHA mismatch"
        )
    if policy_payload.get("repository") != repository:
        raise ReleaseLineageError("policy repository mismatch")
    if policy_payload.get("passed") is not True:
        raise ReleaseLineageError(
            "production-boundary policy did not pass"
        )

    final_fp = final_payload.get("fingerprint")
    certification_fp = certification_payload.get("fingerprint")
    bundle_fp = final_payload.get("bundle_fingerprint")
    external_fp = certification_payload.get("external_evidence_fingerprint")
    policy_fp = policy_payload.get("fingerprint")
    promotion_fp = final_payload.get("freshness_gate_fingerprint")

    for name, value in (
        ("final readiness fingerprint", final_fp),
        (
            "certification verification fingerprint",
            certification_fp,
        ),
        ("bundle fingerprint", bundle_fp),
        ("external evidence fingerprint", external_fp),
        ("policy fingerprint", policy_fp),
        (
            "promotion verification fingerprint",
            promotion_fp,
        ),
    ):
        if not isinstance(value, str):
            raise ReleaseLineageError(f"{name} is missing")

    source_environment = final_payload.get("source_environment")
    target_environment = final_payload.get("target_environment")
    if source_environment not in {"staging", "pilot"}:
        raise ReleaseLineageError(
            "invalid lineage source environment"
        )
    if target_environment != "production":
        raise ReleaseLineageError(
            "lineage target environment must be production"
        )
    if verified_at.tzinfo is None:
        raise ReleaseLineageError(
            "verified_at must be timezone-aware"
        )

    return ProductionReleaseLineage(
        lineage_version=1,
        repository=repository,
        release_id=str(final_payload.get("release_id", "")),
        tag=tag,
        candidate_sha=candidate_sha,
        bundle_fingerprint=bundle_fp,
        promotion_verification_fingerprint=promotion_fp,
        final_readiness_fingerprint=final_fp,
        external_evidence_fingerprint=external_fp,
        certification_verification_fingerprint=certification_fp,
        policy_fingerprint=policy_fp,
        source_environment=source_environment,
        target_environment=target_environment,
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
        + "
",
        encoding="utf-8",
    )
