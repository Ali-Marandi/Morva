from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from hashlib import sha256
from pathlib import Path

from morva.runtime.production_release_lineage import (
    ProductionReleaseLineage,
    ReleaseLineageError,
    build_release_lineage,
)


class IndependentLineageVerificationError(ValueError):
    """Raised when a stored release lineage cannot be independently verified."""


@dataclass(frozen=True, slots=True)
class IndependentLineageVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    lineage_fingerprint: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "lineage_fingerprint": self.lineage_fingerprint.lower(),
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
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "lineage_fingerprint": self.lineage_fingerprint,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_lineage(path: Path) -> ProductionReleaseLineage:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        lineage = ProductionReleaseLineage(
            lineage_version=int(payload["lineage_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            technical_readiness_fingerprint=payload[
                "technical_readiness_fingerprint"
            ],
            freshness_gate_fingerprint=payload["freshness_gate_fingerprint"],
            final_readiness_fingerprint=payload[
                "final_readiness_fingerprint"
            ],
            external_evidence_fingerprint=payload[
                "external_evidence_fingerprint"
            ],
            certification_verification_fingerprint=payload[
                "certification_verification_fingerprint"
            ],
            technical_policy_fingerprint=payload[
                "technical_policy_fingerprint"
            ],
            full_policy_fingerprint=payload["full_policy_fingerprint"],
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
        ReleaseLineageError,
    ) as exc:
        raise IndependentLineageVerificationError(
            "release lineage structure is invalid"
        ) from exc
    if payload.get("fingerprint") != lineage.fingerprint:
        raise IndependentLineageVerificationError(
            "release lineage fingerprint mismatch"
        )
    return lineage


def verify_release_lineage(
    *,
    technical_readiness_gate: Path,
    final_readiness_receipt: Path,
    production_certification_receipt: Path,
    external_registry: Path,
    policy_receipt: Path,
    lineage_manifest: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> IndependentLineageVerificationReceipt:
    stored = load_lineage(lineage_manifest)
    try:
        rebuilt = build_release_lineage(
            technical_readiness_gate=technical_readiness_gate,
            final_readiness_receipt=final_readiness_receipt,
            production_certification_receipt=production_certification_receipt,
            external_registry=external_registry,
            policy_receipt=policy_receipt,
            repository=repository,
            tag=tag,
            candidate_sha=candidate_sha,
            verified_at=stored.verified_at,
        )
    except (ReleaseLineageError, ValueError) as exc:
        raise IndependentLineageVerificationError(
            "release lineage reconstruction failed"
        ) from exc

    if stored != rebuilt:
        raise IndependentLineageVerificationError(
            "stored lineage does not match independently rebuilt lineage"
        )

    return IndependentLineageVerificationReceipt(
        verifier_version=1,
        repository=rebuilt.repository,
        release_id=rebuilt.release_id,
        tag=rebuilt.tag,
        candidate_sha=rebuilt.candidate_sha,
        lineage_fingerprint=rebuilt.fingerprint,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentLineageVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentLineageVerificationError(
            "independent lineage receipt is write-once"
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
