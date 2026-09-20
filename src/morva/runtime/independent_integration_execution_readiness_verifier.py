from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.independent_integration_execution_verifier import (
    IndependentIntegrationExecutionVerificationError,
    verify_integration_execution,
)
from morva.runtime.integration_execution_evidence import (
    IntegrationExecutionEvidenceError,
)
from morva.runtime.integration_execution_readiness_gate import (
    IntegrationExecutionReadinessGate,
    IntegrationExecutionReadinessGateError,
    build_integration_execution_readiness_gate,
)


class IndependentIntegrationExecutionReadinessVerificationError(ValueError):
    """Raised when M3.86 execution readiness fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentIntegrationExecutionReadinessVerificationReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    execution_readiness_gate_fingerprint: str
    execution_verification_fingerprint: str
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
            "execution_readiness_gate_fingerprint": (
                self.execution_readiness_gate_fingerprint.lower()
            ),
            "execution_verification_fingerprint": (
                self.execution_verification_fingerprint.lower()
            ),
            "execution_evidence_fingerprint": (
                self.execution_evidence_fingerprint.lower()
            ),
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint.lower(),
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
            "execution_readiness_gate_fingerprint": (
                self.execution_readiness_gate_fingerprint
            ),
            "execution_verification_fingerprint": (
                self.execution_verification_fingerprint
            ),
            "execution_evidence_fingerprint": self.execution_evidence_fingerprint,
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint,
            "readiness_verification_fingerprint": (
                self.readiness_verification_fingerprint
            ),
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_gate(path: Path) -> IntegrationExecutionReadinessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = IntegrationExecutionReadinessGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            adapters=tuple(payload["adapters"]),
            execution_id=payload["execution_id"],
            execution_evidence_fingerprint=(
                payload["execution_evidence_fingerprint"]
            ),
            execution_verification_fingerprint=(
                payload["execution_verification_fingerprint"]
            ),
            readiness_gate_fingerprint=payload["readiness_gate_fingerprint"],
            readiness_verification_fingerprint=(
                payload["readiness_verification_fingerprint"]
            ),
            latest_execution_finished_at=payload["latest_execution_finished_at"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
            max_execution_age_hours=int(payload["max_execution_age_hours"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        IntegrationExecutionReadinessGateError,
    ) as exc:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "M3.86 gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "M3.86 gate fingerprint mismatch"
        )
    return gate


def verify_execution_readiness(
    *,
    execution_evidence: Path,
    readiness_gate: Path,
    readiness_verification_receipt: Path,
    registry_file: Path,
    activation_gate: Path,
    contract_manifest: Path,
    execution_readiness_gate: Path,
    repository: str,
    candidate_sha: str,
) -> IndependentIntegrationExecutionReadinessVerificationReceipt:
    gate = _load_gate(execution_readiness_gate)
    if gate.repository != repository:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution readiness repository mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution readiness candidate SHA mismatch"
        )

    try:
        execution_verification = verify_integration_execution(
            execution_evidence=execution_evidence,
            readiness_gate=readiness_gate,
            readiness_verification_receipt=readiness_verification_receipt,
            registry_file=registry_file,
            activation_gate=activation_gate,
            contract_manifest=contract_manifest,
            repository=repository,
            candidate_sha=candidate_sha,
        )
        rebuilt = build_integration_execution_readiness_gate(
            execution_evidence=execution_evidence,
            readiness_gate=readiness_gate,
            readiness_verification_receipt=readiness_verification_receipt,
            registry_file=registry_file,
            activation_gate=activation_gate,
            contract_manifest=contract_manifest,
            repository=repository,
            candidate_sha=candidate_sha,
            checked_at=gate.checked_at,
            max_execution_age_hours=gate.max_execution_age_hours,
        )
    except (
        IntegrationExecutionEvidenceError,
        IndependentIntegrationExecutionVerificationError,
        IntegrationExecutionReadinessGateError,
        ValueError,
    ) as exc:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "M3.84/M3.85/M3.86 evidence could not be independently rebuilt"
        ) from exc

    if rebuilt != gate:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "stored M3.86 gate does not match independently rebuilt gate"
        )
    if execution_verification.execution_evidence_fingerprint.lower() != (
        gate.execution_evidence_fingerprint.lower()
    ):
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution evidence fingerprint mismatch"
        )
    if execution_verification.fingerprint.lower() != (
        gate.execution_verification_fingerprint.lower()
    ):
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution verification fingerprint mismatch"
        )
    if execution_verification.readiness_gate_fingerprint.lower() != (
        gate.readiness_gate_fingerprint.lower()
    ):
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "readiness gate fingerprint mismatch"
        )
    if execution_verification.readiness_verification_fingerprint.lower() != (
        gate.readiness_verification_fingerprint.lower()
    ):
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "readiness verification fingerprint mismatch"
        )
    if execution_verification.target_environment != gate.target_environment:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution target environment mismatch"
        )
    if execution_verification.adapters != gate.adapters:
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "execution adapter set mismatch"
        )

    return IndependentIntegrationExecutionReadinessVerificationReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=gate.target_environment,
        adapters=gate.adapters,
        execution_readiness_gate_fingerprint=gate.fingerprint,
        execution_verification_fingerprint=execution_verification.fingerprint,
        execution_evidence_fingerprint=execution_verification.execution_evidence_fingerprint,
        readiness_gate_fingerprint=execution_verification.readiness_gate_fingerprint,
        readiness_verification_fingerprint=(
            execution_verification.readiness_verification_fingerprint
        ),
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentIntegrationExecutionReadinessVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentIntegrationExecutionReadinessVerificationError(
            "M3.88 verification receipt is write-once"
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
