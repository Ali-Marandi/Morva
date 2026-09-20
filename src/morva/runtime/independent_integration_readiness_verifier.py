from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.integration_readiness_gate import (
    IntegrationReadinessGate,
    IntegrationReadinessGateError,
)
from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationError,
    verify_adapter_activation,
)
from morva.runtime.independent_integration_contract_verifier import (
    IndependentIntegrationContractVerificationError,
    verify_integration_contract,
)
from morva.runtime.integration_contract_manifest import (
    IntegrationContractManifestError,
    load_manifest,
)
from morva.runtime.official_adapter_evidence import (
    OfficialAdapterEvidenceError,
    load_registry,
)


class IndependentIntegrationReadinessVerificationError(ValueError):
    """Raised when integration readiness cannot be independently reverified."""


@dataclass(frozen=True, slots=True)
class IndependentIntegrationReadinessVerificationReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    readiness_gate_fingerprint: str
    activation_verification_fingerprint: str
    contract_verification_fingerprint: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "readiness_gate_fingerprint": (
                self.readiness_gate_fingerprint.lower()
            ),
            "activation_verification_fingerprint": (
                self.activation_verification_fingerprint.lower()
            ),
            "contract_verification_fingerprint": (
                self.contract_verification_fingerprint.lower()
            ),
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
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint,
            "activation_verification_fingerprint": (
                self.activation_verification_fingerprint
            ),
            "contract_verification_fingerprint": (
                self.contract_verification_fingerprint
            ),
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_readiness_gate(path: Path) -> IntegrationReadinessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = IntegrationReadinessGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            adapters=tuple(payload["adapters"]),
            adapter_registry_fingerprint=(
                payload["adapter_registry_fingerprint"]
            ),
            activation_gate_fingerprint=payload[
                "activation_gate_fingerprint"
            ],
            activation_verification_fingerprint=payload[
                "activation_verification_fingerprint"
            ],
            contract_manifest_fingerprint=payload[
                "contract_manifest_fingerprint"
            ],
            contract_verification_fingerprint=payload[
                "contract_verification_fingerprint"
            ],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        IntegrationReadinessGateError,
    ) as exc:
        raise IndependentIntegrationReadinessVerificationError(
            "integration readiness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IndependentIntegrationReadinessVerificationError(
            "integration readiness gate fingerprint mismatch"
        )
    return gate


def verify_integration_readiness(
    *,
    registry_file: Path,
    activation_gate: Path,
    contract_manifest: Path,
    readiness_gate: Path,
    repository: str,
    candidate_sha: str,
) -> IndependentIntegrationReadinessVerificationReceipt:
    gate = _load_readiness_gate(readiness_gate)
    try:
        activation = verify_adapter_activation(
            registry_file=registry_file,
            activation_gate=activation_gate,
            repository=repository,
            candidate_sha=candidate_sha,
        )
        contract = verify_integration_contract(
            manifest_file=contract_manifest,
            repository=repository,
            candidate_sha=candidate_sha,
        )
        registry = load_registry(registry_file)
        manifest = load_manifest(contract_manifest)
    except (
        IndependentAdapterActivationVerificationError,
        IndependentIntegrationContractVerificationError,
        OfficialAdapterEvidenceError,
        IntegrationContractManifestError,
        ValueError,
    ) as exc:
        raise IndependentIntegrationReadinessVerificationError(
            "underlying adapter readiness evidence failed verification"
        ) from exc

    if gate.repository != repository:
        raise IndependentIntegrationReadinessVerificationError(
            "readiness repository mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentIntegrationReadinessVerificationError(
            "readiness candidate SHA mismatch"
        )
    if gate.target_environment != activation.target_environment:
        raise IndependentIntegrationReadinessVerificationError(
            "readiness target environment mismatch"
        )
    if gate.activation_verification_fingerprint.lower() != activation.fingerprint.lower():
        raise IndependentIntegrationReadinessVerificationError(
            "activation verification fingerprint mismatch"
        )
    if gate.contract_verification_fingerprint.lower() != contract.fingerprint.lower():
        raise IndependentIntegrationReadinessVerificationError(
            "contract verification fingerprint mismatch"
        )
    if gate.adapter_registry_fingerprint.lower() != registry.fingerprint.lower():
        raise IndependentIntegrationReadinessVerificationError(
            "adapter registry fingerprint mismatch"
        )
    if gate.contract_manifest_fingerprint.lower() != manifest.fingerprint.lower():
        raise IndependentIntegrationReadinessVerificationError(
            "contract manifest fingerprint mismatch"
        )
    if gate.adapters != activation.adapters or gate.adapters != contract.adapters:
        raise IndependentIntegrationReadinessVerificationError(
            "readiness adapter set mismatch"
        )
    if gate.checked_at.tzinfo is None:
        raise IndependentIntegrationReadinessVerificationError(
            "readiness checked_at must be timezone-aware"
        )
    if activation.verified_at > gate.checked_at:
        raise IndependentIntegrationReadinessVerificationError(
            "activation verification postdates readiness gate"
        )
    if contract.verified_at > gate.checked_at:
        raise IndependentIntegrationReadinessVerificationError(
            "contract verification postdates readiness gate"
        )

    return IndependentIntegrationReadinessVerificationReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=gate.target_environment,
        adapters=gate.adapters,
        readiness_gate_fingerprint=gate.fingerprint,
        activation_verification_fingerprint=activation.fingerprint,
        contract_verification_fingerprint=contract.fingerprint,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentIntegrationReadinessVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentIntegrationReadinessVerificationError(
            "integration readiness verification receipt is write-once"
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
