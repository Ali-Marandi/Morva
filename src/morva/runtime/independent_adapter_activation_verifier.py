from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.adapter_activation_gate import (
    AdapterActivationGate,
    AdapterActivationGateError,
)
from morva.runtime.independent_adapter_evidence_verifier import (
    IndependentAdapterEvidenceVerificationError,
    verify_official_adapter_evidence,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    OfficialAdapterEvidenceError,
    load_registry,
)


class IndependentAdapterActivationVerificationError(ValueError):
    """Raised when adapter activation evidence fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentAdapterActivationVerificationReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    activation_gate_fingerprint: str
    registry_fingerprint: str
    authorization_id: str
    approver: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "activation_gate_fingerprint": (
                self.activation_gate_fingerprint.lower()
            ),
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "authorization_id": self.authorization_id,
            "approver": self.approver,
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
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "activation_gate_fingerprint": (
                self.activation_gate_fingerprint
            ),
            "registry_fingerprint": self.registry_fingerprint,
            "authorization_id": self.authorization_id,
            "approver": self.approver,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def load_gate(path: Path) -> AdapterActivationGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = AdapterActivationGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            registry_fingerprint=payload["registry_fingerprint"],
            authorization_id=payload["authorization_id"],
            approver=payload["approver"],
            target_environment=payload["target_environment"],
            adapters=tuple(payload["adapters"]),
            approved_at=payload["approved_at"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        AdapterActivationGateError,
    ) as exc:
        raise IndependentAdapterActivationVerificationError(
            "adapter activation gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IndependentAdapterActivationVerificationError(
            "adapter activation gate fingerprint mismatch"
        )
    return gate


def verify_adapter_activation(
    *,
    registry_file: Path,
    activation_gate: Path,
    repository: str,
    candidate_sha: str,
) -> IndependentAdapterActivationVerificationReceipt:
    gate = load_gate(activation_gate)
    try:
        registry = load_registry(registry_file)
        verification = verify_official_adapter_evidence(
            registry_file=registry_file,
            repository=repository,
            candidate_sha=candidate_sha,
            checked_at=gate.checked_at,
        )
    except (
        IndependentAdapterEvidenceVerificationError,
        OfficialAdapterEvidenceError,
        ValueError,
    ) as exc:
        raise IndependentAdapterActivationVerificationError(
            "official adapter evidence could not be independently verified"
        ) from exc

    if gate.repository != repository:
        raise IndependentAdapterActivationVerificationError(
            "activation repository mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentAdapterActivationVerificationError(
            "activation candidate SHA mismatch"
        )
    if gate.registry_fingerprint.lower() != registry.fingerprint.lower():
        raise IndependentAdapterActivationVerificationError(
            "activation gate registry fingerprint mismatch"
        )
    if verification.registry_fingerprint.lower() != registry.fingerprint.lower():
        raise IndependentAdapterActivationVerificationError(
            "independent registry fingerprint mismatch"
        )
    if gate.target_environment not in {"staging", "pilot"}:
        raise IndependentAdapterActivationVerificationError(
            "activation target environment is invalid"
        )
    if gate.adapters != REQUIRED_ADAPTERS:
        raise IndependentAdapterActivationVerificationError(
            "activation adapter set is not canonical"
        )
    approved_at = datetime.fromisoformat(gate.approved_at)
    if approved_at > gate.checked_at:
        raise IndependentAdapterActivationVerificationError(
            "activation authorization is future-dated"
        )
    if (
        registry.repository != repository
        or registry.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise IndependentAdapterActivationVerificationError(
            "adapter registry identity mismatch"
        )

    return IndependentAdapterActivationVerificationReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=gate.target_environment,
        adapters=REQUIRED_ADAPTERS,
        activation_gate_fingerprint=gate.fingerprint,
        registry_fingerprint=registry.fingerprint,
        authorization_id=gate.authorization_id,
        approver=gate.approver,
        verified_at=gate.checked_at,
    )


def write_receipt(
    receipt: IndependentAdapterActivationVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentAdapterActivationVerificationError(
            "adapter activation verification receipt is write-once"
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
