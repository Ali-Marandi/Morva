from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.independent_adapter_evidence_verifier import (
    IndependentAdapterEvidenceVerificationError,
    verify_official_adapter_evidence,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    OfficialAdapterEvidenceError,
    assert_activation_ready,
    load_registry,
)


class AdapterActivationGateError(ValueError):
    """Raised when official-adapter activation is not safely authorized."""


@dataclass(frozen=True, slots=True)
class AdapterActivationAuthorization:
    authorization_id: str
    registry_fingerprint: str
    approved: bool
    approved_at: str
    approver: str
    target_environment: str
    scope: str = "official_adapter_activation"

    def __post_init__(self) -> None:
        if not self.authorization_id.strip() or not self.approver.strip():
            raise AdapterActivationGateError(
                "authorization identity is required"
            )
        if len(self.registry_fingerprint) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.registry_fingerprint.lower()
        ):
            raise AdapterActivationGateError(
                "registry_fingerprint must be SHA-256"
            )
        if not isinstance(self.approved, bool):
            raise AdapterActivationGateError("approved must be Boolean")
        if self.scope != "official_adapter_activation":
            raise AdapterActivationGateError("unsupported activation scope")
        if self.target_environment not in {"staging", "pilot"}:
            raise AdapterActivationGateError(
                "target_environment must be staging or pilot"
            )
        timestamp = datetime.fromisoformat(self.approved_at)
        if timestamp.tzinfo is None:
            raise AdapterActivationGateError(
                "approved_at must include a timezone"
            )


@dataclass(frozen=True, slots=True)
class AdapterActivationGate:
    gate_version: int
    repository: str
    candidate_sha: str
    registry_fingerprint: str
    authorization_id: str
    approver: str
    target_environment: str
    adapters: tuple[str, ...]
    approved_at: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise AdapterActivationGateError(
                "unsupported activation gate version"
            )
        if not self.repository.strip():
            raise AdapterActivationGateError("repository is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef"
            for c in self.candidate_sha.lower()
        ):
            raise AdapterActivationGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if len(self.registry_fingerprint) != 64 or any(
            c not in "0123456789abcdef"
            for c in self.registry_fingerprint.lower()
        ):
            raise AdapterActivationGateError(
                "registry_fingerprint must be SHA-256"
            )
        if tuple(self.adapters) != REQUIRED_ADAPTERS:
            raise AdapterActivationGateError(
                "activation gate must cover the canonical adapter set"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise AdapterActivationGateError(
                "target_environment must be staging or pilot"
            )
        if not self.authorization_id.strip() or not self.approver.strip():
            raise AdapterActivationGateError(
                "authorization identity is required"
            )
        approved = datetime.fromisoformat(self.approved_at)
        if approved.tzinfo is None or self.checked_at.tzinfo is None:
            raise AdapterActivationGateError(
                "activation timestamps must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "authorization_id": self.authorization_id,
            "approver": self.approver,
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "approved_at": self.approved_at,
            "checked_at": self.checked_at.isoformat(),
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
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "registry_fingerprint": self.registry_fingerprint,
            "authorization_id": self.authorization_id,
            "approver": self.approver,
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "approved_at": self.approved_at,
            "checked_at": self.checked_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_activation_gate(
    *,
    registry_file: Path,
    authorization: AdapterActivationAuthorization,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> AdapterActivationGate:
    if checked_at.tzinfo is None:
        raise AdapterActivationGateError(
            "checked_at must be timezone-aware"
        )
    try:
        verification = verify_official_adapter_evidence(
            registry_file=registry_file,
            repository=repository,
            candidate_sha=candidate_sha,
            checked_at=checked_at,
        )
        registry = load_registry(registry_file)
        assert_activation_ready(
            registry,
            repository=repository,
            candidate_sha=candidate_sha,
            checked_at=checked_at,
        )
    except (
        IndependentAdapterEvidenceVerificationError,
        OfficialAdapterEvidenceError,
        ValueError,
    ) as exc:
        raise AdapterActivationGateError(
            "official adapter evidence is not independently verified"
        ) from exc

    if registry.fingerprint.lower() != verification.registry_fingerprint.lower():
        raise AdapterActivationGateError(
            "registry fingerprint changed during activation check"
        )
    if authorization.registry_fingerprint.lower() != registry.fingerprint.lower():
        raise AdapterActivationGateError(
            "activation authorization does not match adapter registry"
        )
    if not authorization.approved:
        raise AdapterActivationGateError(
            "adapter activation authorization is not approved"
        )
    approved_at = datetime.fromisoformat(authorization.approved_at)
    if approved_at > checked_at:
        raise AdapterActivationGateError(
            "activation authorization is future-dated"
        )

    return AdapterActivationGate(
        gate_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        registry_fingerprint=registry.fingerprint,
        authorization_id=authorization.authorization_id,
        approver=authorization.approver,
        target_environment=authorization.target_environment,
        adapters=REQUIRED_ADAPTERS,
        approved_at=authorization.approved_at,
        checked_at=checked_at,
    )


def write_gate(gate: AdapterActivationGate, path: Path) -> None:
    if path.exists():
        raise AdapterActivationGateError(
            "adapter activation gate is write-once"
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
