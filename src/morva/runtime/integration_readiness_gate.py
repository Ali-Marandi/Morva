from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationError,
    IndependentAdapterActivationVerificationReceipt,
    verify_adapter_activation,
)
from morva.runtime.independent_integration_contract_verifier import (
    IndependentIntegrationContractVerificationError,
    IndependentIntegrationContractVerificationReceipt,
    verify_integration_contract,
)
from morva.runtime.integration_contract_manifest import (
    IntegrationContractManifestError,
    load_manifest,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    OfficialAdapterEvidenceError,
    load_registry,
)


class IntegrationReadinessGateError(ValueError):
    """Raised when adapter integration readiness is inconsistent."""


@dataclass(frozen=True, slots=True)
class IntegrationReadinessGate:
    gate_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    adapter_registry_fingerprint: str
    activation_gate_fingerprint: str
    activation_verification_fingerprint: str
    contract_manifest_fingerprint: str
    contract_verification_fingerprint: str
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise IntegrationReadinessGateError(
                "unsupported integration readiness gate version"
            )
        if not self.repository.strip():
            raise IntegrationReadinessGateError("repository is required")
        if len(self.candidate_sha) != 40 or any(
            c not in "0123456789abcdef" for c in self.candidate_sha.lower()
        ):
            raise IntegrationReadinessGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IntegrationReadinessGateError(
                "target_environment must be staging or pilot"
            )
        if self.adapters != REQUIRED_ADAPTERS:
            raise IntegrationReadinessGateError(
                "readiness gate must cover the canonical adapter set"
            )
        for name, value in (
            ("adapter_registry_fingerprint", self.adapter_registry_fingerprint),
            ("activation_gate_fingerprint", self.activation_gate_fingerprint),
            (
                "activation_verification_fingerprint",
                self.activation_verification_fingerprint,
            ),
            ("contract_manifest_fingerprint", self.contract_manifest_fingerprint),
            (
                "contract_verification_fingerprint",
                self.contract_verification_fingerprint,
            ),
        ):
            if len(value) != 64 or any(
                c not in "0123456789abcdef" for c in value.lower()
            ):
                raise IntegrationReadinessGateError(
                    f"{name} must be SHA-256"
                )
        if self.checked_at.tzinfo is None:
            raise IntegrationReadinessGateError(
                "checked_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "adapter_registry_fingerprint": (
                self.adapter_registry_fingerprint.lower()
            ),
            "activation_gate_fingerprint": (
                self.activation_gate_fingerprint.lower()
            ),
            "activation_verification_fingerprint": (
                self.activation_verification_fingerprint.lower()
            ),
            "contract_manifest_fingerprint": (
                self.contract_manifest_fingerprint.lower()
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
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "adapter_registry_fingerprint": self.adapter_registry_fingerprint,
            "activation_gate_fingerprint": self.activation_gate_fingerprint,
            "activation_verification_fingerprint": (
                self.activation_verification_fingerprint
            ),
            "contract_manifest_fingerprint": self.contract_manifest_fingerprint,
            "contract_verification_fingerprint": (
                self.contract_verification_fingerprint
            ),
            "checked_at": self.checked_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_activation_receipt(
    path: Path,
) -> IndependentAdapterActivationVerificationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = IndependentAdapterActivationVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            adapters=tuple(payload["adapters"]),
            activation_gate_fingerprint=payload["activation_gate_fingerprint"],
            registry_fingerprint=payload["registry_fingerprint"],
            authorization_id=payload["authorization_id"],
            approver=payload["approver"],
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IntegrationReadinessGateError(
            "M3.78 activation verification receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise IntegrationReadinessGateError(
            "M3.78 activation verification receipt fingerprint mismatch"
        )
    return receipt


def _load_contract_receipt(
    path: Path,
) -> IndependentIntegrationContractVerificationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = IndependentIntegrationContractVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            manifest_fingerprint=payload["manifest_fingerprint"],
            adapters=tuple(payload["adapters"]),
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IntegrationReadinessGateError(
            "M3.81 contract verification receipt is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise IntegrationReadinessGateError(
            "M3.81 contract verification receipt fingerprint mismatch"
        )
    return receipt


def build_integration_readiness_gate(
    *,
    registry_file: Path,
    activation_gate: Path,
    activation_verification_receipt: Path,
    contract_manifest: Path,
    contract_verification_receipt: Path,
    repository: str,
    candidate_sha: str,
    target_environment: str,
    checked_at: datetime,
) -> IntegrationReadinessGate:
    if checked_at.tzinfo is None:
        raise IntegrationReadinessGateError(
            "checked_at must be timezone-aware"
        )
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
        raise IntegrationReadinessGateError(
            "adapter activation or contract verification failed"
        ) from exc

    stored_activation = _load_activation_receipt(
        activation_verification_receipt
    )
    stored_contract = _load_contract_receipt(
        contract_verification_receipt
    )

    if activation.target_environment != target_environment:
        raise IntegrationReadinessGateError(
            "activation target environment mismatch"
        )
    if stored_activation != activation:
        raise IntegrationReadinessGateError(
            "stored M3.78 receipt does not match current verification"
        )
    if stored_contract != contract:
        raise IntegrationReadinessGateError(
            "stored M3.81 receipt does not match current verification"
        )
    if registry.fingerprint.lower() != activation.registry_fingerprint.lower():
        raise IntegrationReadinessGateError(
            "adapter registry fingerprint mismatch"
        )
    if manifest.fingerprint.lower() != contract.manifest_fingerprint.lower():
        raise IntegrationReadinessGateError(
            "contract manifest fingerprint mismatch"
        )
    if activation.adapters != REQUIRED_ADAPTERS:
        raise IntegrationReadinessGateError(
            "activation verification adapter set is not canonical"
        )
    if contract.adapters != REQUIRED_ADAPTERS:
        raise IntegrationReadinessGateError(
            "contract verification adapter set is not canonical"
        )
    if stored_activation.repository != repository:
        raise IntegrationReadinessGateError(
            "activation receipt repository mismatch"
        )
    if stored_activation.candidate_sha.lower() != candidate_sha.lower():
        raise IntegrationReadinessGateError(
            "activation receipt candidate SHA mismatch"
        )

    return IntegrationReadinessGate(
        gate_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=target_environment,
        adapters=REQUIRED_ADAPTERS,
        adapter_registry_fingerprint=registry.fingerprint,
        activation_gate_fingerprint=activation.activation_gate_fingerprint,
        activation_verification_fingerprint=activation.fingerprint,
        contract_manifest_fingerprint=manifest.fingerprint,
        contract_verification_fingerprint=contract.fingerprint,
        checked_at=checked_at,
    )


def write_gate(gate: IntegrationReadinessGate, path: Path) -> None:
    if path.exists():
        raise IntegrationReadinessGateError(
            "integration readiness gate is write-once"
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
