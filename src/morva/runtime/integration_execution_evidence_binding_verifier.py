from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.authoritative_evidence_intake import AuthoritativeEvidenceRegistry
from morva.runtime.integration_execution_evidence_bridge import (
    IntegrationExecutionEvidenceBinding,
    IntegrationExecutionEvidenceBridgeError,
    build_integration_execution_evidence_binding,
)


class IntegrationExecutionEvidenceBindingVerificationError(ValueError):
    """Raised when an M4 integration-execution binding cannot be independently verified."""


@dataclass(frozen=True, slots=True)
class IntegrationExecutionEvidenceBindingVerification:
    binding: IntegrationExecutionEvidenceBinding
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.verified_at.tzinfo is None:
            raise IntegrationExecutionEvidenceBindingVerificationError(
                "verified_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_fingerprint": self.binding.fingerprint,
            "verified_at": self.verified_at.astimezone(timezone.utc).isoformat(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


def _load_binding(path: Path) -> IntegrationExecutionEvidenceBinding:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = tuple(
            (
                row["adapter"],
                row["authoritative_evidence_id"],
                row["authoritative_evidence_fingerprint"],
            )
            for row in payload["adapter_evidence_bindings"]
        )
        binding = IntegrationExecutionEvidenceBinding(
            binding_version=int(payload["binding_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            execution_id=payload["execution_id"],
            execution_evidence_fingerprint=payload[
                "execution_evidence_fingerprint"
            ],
            execution_verification_fingerprint=payload[
                "execution_verification_fingerprint"
            ],
            execution_readiness_fingerprint=payload[
                "execution_readiness_fingerprint"
            ],
            registry_fingerprint=payload["registry_fingerprint"],
            adapter_evidence_bindings=rows,
            bound_by=payload["bound_by"],
            bound_at=datetime.fromisoformat(payload["bound_at"]).astimezone(
                timezone.utc
            ),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        IntegrationExecutionEvidenceBridgeError,
    ) as exc:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "integration execution evidence binding structure is invalid"
        ) from exc

    if payload.get("fingerprint") != binding.fingerprint:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "integration execution evidence binding fingerprint mismatch"
        )
    return binding


def verify_integration_execution_evidence_binding(
    binding_path: Path,
    execution_readiness_gate: Path,
    authoritative_registry: AuthoritativeEvidenceRegistry,
    *,
    repository: str,
    candidate_sha: str,
    authoritative_evidence_ids: dict[str, str],
    verified_at: datetime,
) -> IntegrationExecutionEvidenceBindingVerification:
    if verified_at.tzinfo is None:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "verified_at must be timezone-aware"
        )

    binding = _load_binding(binding_path)
    verified_time = verified_at.astimezone(timezone.utc)
    if verified_time < binding.bound_at:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "verification timestamp precedes binding timestamp"
        )
    if binding.registry_fingerprint.lower() != authoritative_registry.fingerprint.lower():
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "integration execution binding registry fingerprint mismatch"
        )
    if binding.repository != repository:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "integration execution binding repository mismatch"
        )
    if binding.candidate_sha.lower() != candidate_sha.lower():
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "integration execution binding candidate SHA mismatch"
        )

    expected = build_integration_execution_evidence_binding(
        execution_readiness_gate,
        authoritative_registry,
        repository=repository,
        candidate_sha=candidate_sha,
        bound_by=binding.bound_by,
        bound_at=binding.bound_at,
        authoritative_evidence_ids=authoritative_evidence_ids,
    )
    if expected != binding:
        raise IntegrationExecutionEvidenceBindingVerificationError(
            "independent reconstruction does not match the recorded binding"
        )

    return IntegrationExecutionEvidenceBindingVerification(
        binding=binding,
        verified_at=verified_at.astimezone(timezone.utc),
    )
