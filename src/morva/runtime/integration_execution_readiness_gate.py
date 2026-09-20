from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.independent_integration_execution_verifier import (
    IndependentIntegrationExecutionVerificationError,
    verify_integration_execution,
)
from morva.runtime.integration_execution_evidence import (
    IntegrationExecutionEvidenceError,
    load_execution_evidence,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


class IntegrationExecutionReadinessGateError(ValueError):
    """Raised when staging/pilot execution readiness is incomplete."""


@dataclass(frozen=True, slots=True)
class IntegrationExecutionReadinessGate:
    gate_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    execution_id: str
    execution_evidence_fingerprint: str
    execution_verification_fingerprint: str
    readiness_gate_fingerprint: str
    readiness_verification_fingerprint: str
    latest_execution_finished_at: str
    checked_at: datetime
    max_execution_age_hours: int

    def __post_init__(self) -> None:
        if self.gate_version != 1:
            raise IntegrationExecutionReadinessGateError(
                "unsupported execution readiness gate version"
            )
        if not self.repository.strip() or not self.execution_id.strip():
            raise IntegrationExecutionReadinessGateError(
                "repository and execution_id are required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise IntegrationExecutionReadinessGateError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IntegrationExecutionReadinessGateError(
                "target_environment must be staging or pilot"
            )
        if self.adapters != REQUIRED_ADAPTERS:
            raise IntegrationExecutionReadinessGateError(
                "gate must cover the canonical adapter set"
            )
        for name, value in (
            ("execution_evidence_fingerprint", self.execution_evidence_fingerprint),
            ("execution_verification_fingerprint", self.execution_verification_fingerprint),
            ("readiness_gate_fingerprint", self.readiness_gate_fingerprint),
            ("readiness_verification_fingerprint", self.readiness_verification_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IntegrationExecutionReadinessGateError(
                    f"{name} must be SHA-256"
                )
        try:
            finished = datetime.fromisoformat(self.latest_execution_finished_at)
        except ValueError as exc:
            raise IntegrationExecutionReadinessGateError(
                "latest_execution_finished_at must be ISO-8601"
            ) from exc
        if finished.tzinfo is None:
            raise IntegrationExecutionReadinessGateError(
                "latest_execution_finished_at must include a timezone"
            )
        if self.checked_at.tzinfo is None:
            raise IntegrationExecutionReadinessGateError(
                "checked_at must be timezone-aware"
            )
        if finished > self.checked_at:
            raise IntegrationExecutionReadinessGateError(
                "latest execution cannot finish after gate check"
            )
        if (
            not isinstance(self.max_execution_age_hours, int)
            or isinstance(self.max_execution_age_hours, bool)
            or self.max_execution_age_hours <= 0
        ):
            raise IntegrationExecutionReadinessGateError(
                "max_execution_age_hours must be a positive integer"
            )
        if self.checked_at - finished > timedelta(hours=self.max_execution_age_hours):
            raise IntegrationExecutionReadinessGateError(
                "integration execution evidence is stale"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "execution_id": self.execution_id,
            "execution_evidence_fingerprint": self.execution_evidence_fingerprint.lower(),
            "execution_verification_fingerprint": self.execution_verification_fingerprint.lower(),
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint.lower(),
            "readiness_verification_fingerprint": self.readiness_verification_fingerprint.lower(),
            "latest_execution_finished_at": self.latest_execution_finished_at,
            "checked_at": self.checked_at.isoformat(),
            "max_execution_age_hours": self.max_execution_age_hours,
        }
        return sha256(
            json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            .encode("utf-8")
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "gate_version": self.gate_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "adapters": list(self.adapters),
            "execution_id": self.execution_id,
            "execution_evidence_fingerprint": self.execution_evidence_fingerprint,
            "execution_verification_fingerprint": self.execution_verification_fingerprint,
            "readiness_gate_fingerprint": self.readiness_gate_fingerprint,
            "readiness_verification_fingerprint": self.readiness_verification_fingerprint,
            "latest_execution_finished_at": self.latest_execution_finished_at,
            "checked_at": self.checked_at.isoformat(),
            "max_execution_age_hours": self.max_execution_age_hours,
            "fingerprint": self.fingerprint,
        }


def build_integration_execution_readiness_gate(
    *,
    execution_evidence: Path,
    readiness_gate: Path,
    readiness_verification_receipt: Path,
    registry_file: Path,
    activation_gate: Path,
    contract_manifest: Path,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
    max_execution_age_hours: int,
) -> IntegrationExecutionReadinessGate:
    if checked_at.tzinfo is None:
        raise IntegrationExecutionReadinessGateError(
            "checked_at must be timezone-aware"
        )
    try:
        execution = load_execution_evidence(execution_evidence)
        verification = verify_integration_execution(
            execution_evidence=execution_evidence,
            readiness_gate=readiness_gate,
            readiness_verification_receipt=readiness_verification_receipt,
            registry_file=registry_file,
            activation_gate=activation_gate,
            contract_manifest=contract_manifest,
            repository=repository,
            candidate_sha=candidate_sha,
        )
    except (
        IntegrationExecutionEvidenceError,
        IndependentIntegrationExecutionVerificationError,
        ValueError,
    ) as exc:
        raise IntegrationExecutionReadinessGateError(
            "M3.84/M3.85 execution evidence verification failed"
        ) from exc

    finished_pairs = [
        (datetime.fromisoformat(item.finished_at), item.finished_at)
        for item in execution.evidence_items
    ]
    latest_finished_dt, latest_finished = max(finished_pairs)
    if execution.repository != repository:
        raise IntegrationExecutionReadinessGateError("execution repository mismatch")
    if execution.candidate_sha.lower() != candidate_sha.lower():
        raise IntegrationExecutionReadinessGateError("execution candidate SHA mismatch")
    if execution.target_environment != verification.target_environment:
        raise IntegrationExecutionReadinessGateError(
            "execution environment differs from independent verification"
        )
    if tuple(item.adapter for item in execution.evidence_items) != REQUIRED_ADAPTERS:
        raise IntegrationExecutionReadinessGateError(
            "execution adapter set is not canonical"
        )
    if (
        verification.execution_evidence_fingerprint.lower()
        != execution.evidence_fingerprint.lower()
    ):
        raise IntegrationExecutionReadinessGateError(
            "execution fingerprint differs from independent verification"
        )
    if latest_finished_dt > checked_at:
        raise IntegrationExecutionReadinessGateError(
            "gate check precedes latest execution completion"
        )

    return IntegrationExecutionReadinessGate(
        gate_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        target_environment=execution.target_environment,
        adapters=REQUIRED_ADAPTERS,
        execution_id=execution.execution_id,
        execution_evidence_fingerprint=execution.evidence_fingerprint,
        execution_verification_fingerprint=verification.fingerprint,
        readiness_gate_fingerprint=verification.readiness_gate_fingerprint,
        readiness_verification_fingerprint=verification.readiness_verification_fingerprint,
        latest_execution_finished_at=latest_finished,
        checked_at=checked_at,
        max_execution_age_hours=max_execution_age_hours,
    )


def write_gate(gate: IntegrationExecutionReadinessGate, path: Path) -> None:
    if path.exists():
        raise IntegrationExecutionReadinessGateError(
            "integration execution readiness gate is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(gate.to_payload(), ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
