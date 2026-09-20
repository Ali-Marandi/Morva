from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.independent_integration_readiness_verifier import (
    IndependentIntegrationReadinessVerificationError,
    IndependentIntegrationReadinessVerificationReceipt,
    verify_integration_readiness,
)
from morva.runtime.integration_execution_evidence import (
    IntegrationExecutionEvidenceError,
    load_execution_evidence,
)
from morva.runtime.integration_readiness_gate import (
    IntegrationReadinessGate,
    IntegrationReadinessGateError,
)


class IndependentIntegrationExecutionVerificationError(ValueError):
    """Raised when M3.84 execution evidence fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentIntegrationExecutionVerificationReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    execution_evidence_fingerprint: str
    readiness_gate_fingerprint: str
    readiness_verification_fingerprint: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "execution_evidence_fingerprint": (
                self.execution_evidence_fingerprint.lower()
            ),
            "readiness_gate_fingerprint": (
                self.readiness_gate_fingerprint.lower()
            ),
            "readiness_verification_fingerprint": (
                self.readiness_verification_fingerprint.lower()
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
            "execution_evidence_fingerprint": (
                self.execution_evidence_fingerprint
            ),
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint,
            "readiness_verification_fingerprint": (
                self.readiness_verification_fingerprint
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
        raise IndependentIntegrationExecutionVerificationError(
            "integration readiness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IndependentIntegrationExecutionVerificationError(
            "integration readiness gate fingerprint mismatch"
        )
    return gate


def _load_readiness_receipt(
    path: Path,
) -> IndependentIntegrationReadinessVerificationReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        receipt = IndependentIntegrationReadinessVerificationReceipt(
            verifier_version=int(payload["verifier_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            adapters=tuple(payload["adapters"]),
            readiness_gate_fingerprint=(
                payload["readiness_gate_fingerprint"]
            ),
            activation_verification_fingerprint=(
                payload["activation_verification_fingerprint"]
            ),
            contract_verification_fingerprint=(
                payload["contract_verification_fingerprint"]
            ),
            verified_at=datetime.fromisoformat(payload["verified_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IndependentIntegrationExecutionVerificationError(
            "M3.83 verification receipt structure is invalid"
        ) from exc
    if payload.get("fingerprint") != receipt.fingerprint:
        raise IndependentIntegrationExecutionVerificationError(
            "M3.83 verification receipt fingerprint mismatch"
        )
    return receipt


def verify_integration_execution(
    *,
    execution_evidence: Path,
    readiness_gate: Path,
    readiness_verification_receipt: Path,
    registry_file: Path,
    activation_gate: Path,
    contract_manifest: Path,
    repository: str,
    candidate_sha: str,
) -> IndependentIntegrationExecutionVerificationReceipt:
    try:
        execution = load_execution_evidence(execution_evidence)
        readiness = _load_readiness_gate(readiness_gate)
        stored_readiness = _load_readiness_receipt(
            readiness_verification_receipt
        )
        current_readiness = verify_integration_readiness(
            registry_file=registry_file,
            activation_gate=activation_gate,
            contract_manifest=contract_manifest,
            readiness_gate=readiness_gate,
            repository=repository,
            candidate_sha=candidate_sha,
        )
    except (
        IntegrationExecutionEvidenceError,
        IndependentIntegrationReadinessVerificationError,
        IntegrationReadinessGateError,
        ValueError,
    ) as exc:
        raise IndependentIntegrationExecutionVerificationError(
            f"underlying execution or readiness evidence failed verification: {exc}"
        ) from exc

    if stored_readiness.fingerprint != current_readiness.fingerprint:
        raise IndependentIntegrationExecutionVerificationError(
            "stored M3.83 receipt does not match current verification"
        )
    if execution.repository != repository:
        raise IndependentIntegrationExecutionVerificationError(
            "execution repository mismatch"
        )
    if execution.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentIntegrationExecutionVerificationError(
            "execution candidate SHA mismatch"
        )
    if execution.target_environment != readiness.target_environment:
        raise IndependentIntegrationExecutionVerificationError(
            "execution target environment mismatch"
        )
    if execution.target_environment != current_readiness.target_environment:
        raise IndependentIntegrationExecutionVerificationError(
            "execution target environment differs from M3.83"
        )
    if execution.evidence_items and datetime.fromisoformat(
        max(item.finished_at for item in execution.evidence_items)
    ) > execution.checked_at:
        raise IndependentIntegrationExecutionVerificationError(
            "execution evidence completion postdates receipt check"
        )
    if execution.checked_at < readiness.checked_at:
        raise IndependentIntegrationExecutionVerificationError(
            "execution evidence predates integration readiness"
        )
    if tuple(item.adapter for item in execution.evidence_items) != readiness.adapters:
        raise IndependentIntegrationExecutionVerificationError(
            "execution adapter set differs from readiness"
        )
    if current_readiness.adapters != readiness.adapters:
        raise IndependentIntegrationExecutionVerificationError(
            "M3.83 adapter set differs from readiness gate"
        )

    return IndependentIntegrationExecutionVerificationReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=execution.target_environment,
        adapters=tuple(
            item.adapter for item in execution.evidence_items
        ),
        execution_evidence_fingerprint=execution.evidence_fingerprint,
        readiness_gate_fingerprint=readiness.fingerprint,
        readiness_verification_fingerprint=current_readiness.fingerprint,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentIntegrationExecutionVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentIntegrationExecutionVerificationError(
            "independent execution verification receipt is write-once"
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
