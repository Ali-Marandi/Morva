from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.external_certification_evidence import REQUIRED_ROLES
from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationError,
    verify_final_readiness,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGate,
    ProductionCertificationGateError,
    load_registry,
)


class IndependentCertificationVerificationError(ValueError):
    """Raised when certification evidence fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentCertificationVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    final_readiness_fingerprint: str
    external_evidence_fingerprint: str
    certification_gate_fingerprint: str
    verified_roles: tuple[str, ...]
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "final_readiness_fingerprint": self.final_readiness_fingerprint.lower(),
            "external_evidence_fingerprint": (
                self.external_evidence_fingerprint.lower()
            ),
            "certification_gate_fingerprint": (
                self.certification_gate_fingerprint.lower()
            ),
            "verified_roles": list(self.verified_roles),
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
            "final_readiness_fingerprint": self.final_readiness_fingerprint,
            "external_evidence_fingerprint": (
                self.external_evidence_fingerprint
            ),
            "certification_gate_fingerprint": (
                self.certification_gate_fingerprint
            ),
            "verified_roles": list(self.verified_roles),
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_certification_gate(path: Path) -> ProductionCertificationGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = ProductionCertificationGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            final_readiness_fingerprint=(
                payload["final_readiness_fingerprint"]
            ),
            external_evidence_fingerprint=(
                payload["external_evidence_fingerprint"]
            ),
            required_roles=tuple(payload["required_roles"]),
            verified_roles=tuple(payload["verified_roles"]),
            certified_at=datetime.fromisoformat(payload["certified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IndependentCertificationVerificationError(
            "production certification gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IndependentCertificationVerificationError(
            "production certification gate fingerprint mismatch"
        )
    return gate


def verify_production_certification(
    *,
    final_technical_gate: Path,
    final_freshness_gate: Path,
    final_gate: Path,
    external_registry: Path,
    certification_gate: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> IndependentCertificationVerificationReceipt:
    try:
        readiness = verify_final_readiness(
            technical_gate=final_technical_gate,
            freshness_gate=final_freshness_gate,
            final_gate=final_gate,
            repository=repository,
            tag=tag,
            candidate_sha=candidate_sha,
        )
        registry = load_registry(external_registry)
    except (
        FinalReadinessVerificationError,
        ProductionCertificationGateError,
        ValueError,
    ) as exc:
        raise IndependentCertificationVerificationError(
            "final readiness or external evidence verification failed"
        ) from exc

    gate = _load_certification_gate(certification_gate)
    if gate.repository != repository or gate.tag != tag:
        raise IndependentCertificationVerificationError(
            "certification repository/tag mismatch"
        )
    if gate.release_id != readiness.release_id:
        raise IndependentCertificationVerificationError(
            "certification release id mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentCertificationVerificationError(
            "certification candidate SHA mismatch"
        )
    if (
        gate.final_readiness_fingerprint.lower()
        != readiness.fingerprint.lower()
    ):
        raise IndependentCertificationVerificationError(
            "final readiness fingerprint mismatch"
        )
    if (
        gate.external_evidence_fingerprint.lower()
        != registry.fingerprint.lower()
    ):
        raise IndependentCertificationVerificationError(
            "external evidence fingerprint mismatch"
        )
    if gate.required_roles != REQUIRED_ROLES:
        raise IndependentCertificationVerificationError(
            "certification required role set is incomplete"
        )
    if gate.verified_roles != REQUIRED_ROLES:
        raise IndependentCertificationVerificationError(
            "certification verified role set is incomplete"
        )
    if registry.repository != repository:
        raise IndependentCertificationVerificationError(
            "external registry repository mismatch"
        )
    if registry.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentCertificationVerificationError(
            "external registry candidate SHA mismatch"
        )
    if gate.certified_at.tzinfo is None:
        raise IndependentCertificationVerificationError(
            "certification timestamp must be timezone-aware"
        )
    if gate.certified_at < readiness.verified_at:
        raise IndependentCertificationVerificationError(
            "certification timestamp precedes readiness verification"
        )

    for item in registry.items:
        verified_at = datetime.fromisoformat(item.verified_at)
        if verified_at > gate.certified_at:
            raise IndependentCertificationVerificationError(
                f"evidence is future-dated for role {item.role}"
            )
        if item.expires_at is not None:
            expires_at = datetime.fromisoformat(item.expires_at)
            if expires_at <= gate.certified_at:
                raise IndependentCertificationVerificationError(
                    f"evidence is expired for role {item.role}"
                )

    return IndependentCertificationVerificationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=gate.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        final_readiness_fingerprint=readiness.fingerprint,
        external_evidence_fingerprint=registry.fingerprint,
        certification_gate_fingerprint=gate.fingerprint,
        verified_roles=REQUIRED_ROLES,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentCertificationVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentCertificationVerificationError(
            "independent certification receipt is write-once"
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
