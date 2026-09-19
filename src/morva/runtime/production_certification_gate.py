from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.external_certification_evidence import (
    REQUIRED_ROLES,
    ExternalCertificationEvidenceError,
    ExternalCertificationEvidenceRegistry,
)
from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationError,
    verify_final_readiness,
)


class ProductionCertificationGateError(ValueError):
    """Raised when production-certification evidence is incomplete."""


@dataclass(frozen=True, slots=True)
class ProductionCertificationGate:
    gate_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    final_readiness_fingerprint: str
    external_evidence_fingerprint: str
    required_roles: tuple[str, ...]
    verified_roles: tuple[str, ...]
    certified_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise ProductionCertificationGateError(
                "unsupported production certification gate version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise ProductionCertificationGateError(
                "repository and release_id are required"
            )
        if not self.tag.strip():
            raise ProductionCertificationGateError("tag is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef" for c in self.candidate_sha.lower()
        ):
            raise ProductionCertificationGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("final_readiness_fingerprint", self.final_readiness_fingerprint),
            ("external_evidence_fingerprint", self.external_evidence_fingerprint),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value.lower()
            ):
                raise ProductionCertificationGateError(
                    f"{name} must be SHA-256"
                )
        if tuple(self.required_roles) != REQUIRED_ROLES:
            raise ProductionCertificationGateError(
                "required role set is not canonical"
            )
        if tuple(self.verified_roles) != REQUIRED_ROLES:
            raise ProductionCertificationGateError(
                "not all required certification roles are verified"
            )
        if self.certified_at.tzinfo is None:
            raise ProductionCertificationGateError(
                "certified_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "final_readiness_fingerprint": (
                self.final_readiness_fingerprint.lower()
            ),
            "external_evidence_fingerprint": (
                self.external_evidence_fingerprint.lower()
            ),
            "required_roles": list(self.required_roles),
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
            "gate_version": self.gate_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "final_readiness_fingerprint": self.final_readiness_fingerprint,
            "external_evidence_fingerprint": self.external_evidence_fingerprint,
            "required_roles": list(self.required_roles),
            "verified_roles": list(self.verified_roles),
            "certified_at": self.certified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_production_certification_gate(
    *,
    final_technical_gate: Path,
    final_freshness_gate: Path,
    final_gate: Path,
    external_registry: ExternalCertificationEvidenceRegistry,
    final_readiness_repository: str,
    tag: str,
    candidate_sha: str,
    certified_at: datetime,
) -> ProductionCertificationGate:
    try:
        readiness = verify_final_readiness(
            technical_gate=final_technical_gate,
            freshness_gate=final_freshness_gate,
            final_gate=final_gate,
            repository=final_readiness_repository,
            tag=tag,
            candidate_sha=candidate_sha,
        )
    except (FinalReadinessVerificationError, ValueError) as exc:
        raise ProductionCertificationGateError(
            "M3.65 final readiness verification failed"
        ) from exc

    if external_registry.repository != final_readiness_repository:
        raise ProductionCertificationGateError(
            "external evidence repository does not match final readiness"
        )
    if external_registry.candidate_sha.lower() != candidate_sha.lower():
        raise ProductionCertificationGateError(
            "external evidence candidate SHA does not match final readiness"
        )
    if tuple(item.role for item in external_registry.items) != REQUIRED_ROLES:
        raise ProductionCertificationGateError(
            "external evidence does not contain the canonical role set"
        )
    if certified_at.tzinfo is None:
        raise ProductionCertificationGateError(
            "certified_at must be timezone-aware"
        )
    if certified_at < readiness.verified_at:
        raise ProductionCertificationGateError(
            "certification time precedes final readiness verification"
        )

    return ProductionCertificationGate(
        gate_version=1,
        repository=final_readiness_repository,
        release_id=readiness.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        final_readiness_fingerprint=readiness.fingerprint,
        external_evidence_fingerprint=external_registry.fingerprint,
        required_roles=REQUIRED_ROLES,
        verified_roles=tuple(item.role for item in external_registry.items),
        certified_at=certified_at,
    )


def load_registry(path: Path) -> ExternalCertificationEvidenceRegistry:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionCertificationGateError(
            "external certification registry is invalid"
        ) from exc
    try:
        from morva.runtime.external_certification_evidence import (
            ExternalCertificationEvidence,
        )

        items = tuple(
            ExternalCertificationEvidence(
                evidence_version=int(item["evidence_version"]),
                role=item["role"],
                evidence_id=item["evidence_id"],
                repository=item["repository"],
                candidate_sha=item["candidate_sha"],
                issuer=item["issuer"],
                status=item["status"],
                digest_sha256=item["digest_sha256"],
                verified_at=item["verified_at"],
                expires_at=item.get("expires_at"),
            )
            for item in payload["items"]
        )
        registry = ExternalCertificationEvidenceRegistry(
            registry_version=int(payload["registry_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            items=items,
            registered_at=datetime.fromisoformat(payload["registered_at"]),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        ExternalCertificationEvidenceError,
    ) as exc:
        raise ProductionCertificationGateError(
            "external certification registry structure is invalid"
        ) from exc
    if payload.get("fingerprint") != registry.fingerprint:
        raise ProductionCertificationGateError(
            "external certification registry fingerprint mismatch"
        )
    return registry


def write_gate(gate: ProductionCertificationGate, path: Path) -> None:
    if path.exists():
        raise ProductionCertificationGateError(
            "production certification gate is write-once"
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
