from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import inspect
import json
from pathlib import Path

from morva.integrations.ports import (
    AccountingPort,
    BankPort,
    InsurancePort,
    SinaPort,
    TaxPort,
    TreasuryPort,
)
from morva.runtime.integration_contract_manifest import (
    ADAPTER_OPERATIONS,
    IntegrationContractManifestError,
    load_manifest,
)


class IndependentIntegrationContractVerificationError(ValueError):
    """Raised when the integration manifest diverges from implementation ports."""


PORTS = {
    "sina": SinaPort,
    "accounting": AccountingPort,
    "treasury": TreasuryPort,
    "bank": BankPort,
    "tax": TaxPort,
    "insurance": InsurancePort,
}


@dataclass(frozen=True, slots=True)
class IndependentIntegrationContractVerificationReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    manifest_fingerprint: str
    adapters: tuple[str, ...]
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "manifest_fingerprint": self.manifest_fingerprint.lower(),
            "adapters": list(self.adapters),
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
            "manifest_fingerprint": self.manifest_fingerprint,
            "adapters": list(self.adapters),
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _public_port_operations(port: type) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name, value in inspect.getmembers(port)
            if not name.startswith("_") and callable(value)
        )
    )


def verify_integration_contract(
    *,
    manifest_file: Path,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> IndependentIntegrationContractVerificationReceipt:
    try:
        manifest = load_manifest(manifest_file)
    except (IntegrationContractManifestError, ValueError) as exc:
        raise IndependentIntegrationContractVerificationError(
            "integration contract manifest could not be loaded"
        ) from exc

    if manifest.repository != repository:
        raise IndependentIntegrationContractVerificationError(
            "integration manifest repository mismatch"
        )
    if manifest.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentIntegrationContractVerificationError(
            "integration manifest candidate SHA mismatch"
        )
    if checked_at.tzinfo is None:
        raise IndependentIntegrationContractVerificationError(
            "checked_at must be timezone-aware"
        )

    for adapter in manifest.adapters:
        declared = ADAPTER_OPERATIONS[adapter]
        actual = _public_port_operations(PORTS[adapter])
        if actual != tuple(sorted(declared)):
            raise IndependentIntegrationContractVerificationError(
                f"adapter port operation drift detected for {adapter}: "
                f"expected={declared!r} actual={actual!r}"
            )

    return IndependentIntegrationContractVerificationReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        manifest_fingerprint=manifest.fingerprint,
        adapters=manifest.adapters,
        verified_at=checked_at,
    )


def write_receipt(
    receipt: IndependentIntegrationContractVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentIntegrationContractVerificationError(
            "integration contract verification receipt is write-once"
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
