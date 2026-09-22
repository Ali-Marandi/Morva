from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.runtime.integration_execution_readiness_gate import (
    IntegrationExecutionReadinessGate,
    IntegrationExecutionReadinessGateError,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


class IntegrationExecutionEvidenceBridgeError(ValueError):
    """Raised when verified integration execution cannot bind into M4 evidence."""


@dataclass(frozen=True, slots=True)
class IntegrationExecutionEvidenceBinding:
    """M4-side binding between M3.86 execution readiness and adapter contracts."""

    binding_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    execution_id: str
    execution_evidence_fingerprint: str
    execution_verification_fingerprint: str
    execution_readiness_fingerprint: str
    registry_fingerprint: str
    adapter_evidence_bindings: tuple[tuple[str, str, str], ...]
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise IntegrationExecutionEvidenceBridgeError(
                "unsupported integration execution evidence binding version"
            )
        if not self.repository.strip() or not self.execution_id.strip():
            raise IntegrationExecutionEvidenceBridgeError(
                "repository and execution_id are required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise IntegrationExecutionEvidenceBridgeError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IntegrationExecutionEvidenceBridgeError(
                "target_environment must be staging or pilot"
            )
        for name, value in (
            ("execution_evidence_fingerprint", self.execution_evidence_fingerprint),
            ("execution_verification_fingerprint", self.execution_verification_fingerprint),
            ("execution_readiness_fingerprint", self.execution_readiness_fingerprint),
            ("registry_fingerprint", self.registry_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IntegrationExecutionEvidenceBridgeError(
                    f"{name} must be SHA-256"
                )
        if tuple(binding[0] for binding in self.adapter_evidence_bindings) != REQUIRED_ADAPTERS:
            raise IntegrationExecutionEvidenceBridgeError(
                "adapter evidence bindings must use the canonical adapter order"
            )
        evidence_ids = tuple(binding[1] for binding in self.adapter_evidence_bindings)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise IntegrationExecutionEvidenceBridgeError(
                "each adapter must bind to a distinct authoritative evidence id"
            )
        for adapter, evidence_id, evidence_fingerprint in self.adapter_evidence_bindings:
            if not adapter.strip() or not evidence_id.strip():
                raise IntegrationExecutionEvidenceBridgeError(
                    "adapter and authoritative evidence id are required"
                )
            if len(evidence_fingerprint) != 64 or any(
                char not in "0123456789abcdef"
                for char in evidence_fingerprint.lower()
            ):
                raise IntegrationExecutionEvidenceBridgeError(
                    "authoritative evidence fingerprint must be SHA-256"
                )
        if not self.bound_by.strip():
            raise IntegrationExecutionEvidenceBridgeError("bound_by is required")
        if self.bound_at.tzinfo is None:
            raise IntegrationExecutionEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "execution_id": self.execution_id,
            "execution_evidence_fingerprint": (
                self.execution_evidence_fingerprint.lower()
            ),
            "execution_verification_fingerprint": (
                self.execution_verification_fingerprint.lower()
            ),
            "execution_readiness_fingerprint": (
                self.execution_readiness_fingerprint.lower()
            ),
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "adapter_evidence_bindings": [
                {
                    "adapter": adapter,
                    "authoritative_evidence_id": evidence_id,
                    "authoritative_evidence_fingerprint": evidence_fingerprint.lower(),
                }
                for adapter, evidence_id, evidence_fingerprint in self.adapter_evidence_bindings
            ],
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
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
            "binding_version": self.binding_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "execution_id": self.execution_id,
            "execution_evidence_fingerprint": self.execution_evidence_fingerprint,
            "execution_verification_fingerprint": self.execution_verification_fingerprint,
            "execution_readiness_fingerprint": self.execution_readiness_fingerprint,
            "registry_fingerprint": self.registry_fingerprint,
            "adapter_evidence_bindings": [
                {
                    "adapter": adapter,
                    "authoritative_evidence_id": evidence_id,
                    "authoritative_evidence_fingerprint": evidence_fingerprint,
                }
                for adapter, evidence_id, evidence_fingerprint in self.adapter_evidence_bindings
            ],
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
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
            execution_evidence_fingerprint=payload["execution_evidence_fingerprint"],
            execution_verification_fingerprint=payload["execution_verification_fingerprint"],
            readiness_gate_fingerprint=payload["readiness_gate_fingerprint"],
            readiness_verification_fingerprint=payload["readiness_verification_fingerprint"],
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
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution readiness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution readiness gate fingerprint mismatch"
        )
    return gate


def _validate_authoritative_evidence(
    registry: AuthoritativeEvidenceRegistry,
    evidence_ids: Mapping[str, str],
    *,
    checked_at: datetime,
) -> tuple[tuple[str, str, str], ...]:
    if tuple(evidence_ids) != REQUIRED_ADAPTERS:
        missing = [adapter for adapter in REQUIRED_ADAPTERS if adapter not in evidence_ids]
        extras = [adapter for adapter in evidence_ids if adapter not in REQUIRED_ADAPTERS]
        if missing:
            raise IntegrationExecutionEvidenceBridgeError(
                f"missing authoritative evidence mapping for adapter: {missing[0]}"
            )
        if extras:
            raise IntegrationExecutionEvidenceBridgeError(
                f"unsupported authoritative evidence adapter: {extras[0]}"
            )
        raise IntegrationExecutionEvidenceBridgeError(
            "authoritative adapter evidence mappings must use the canonical order"
        )

    if checked_at.tzinfo is None:
        raise IntegrationExecutionEvidenceBridgeError(
            "checked_at must be timezone-aware"
        )

    now = checked_at.astimezone(timezone.utc)
    bindings: list[tuple[str, str, str]] = []
    seen_ids: set[str] = set()

    for adapter in REQUIRED_ADAPTERS:
        evidence_id = evidence_ids[adapter].strip()
        if not evidence_id:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence id is required for adapter {adapter}"
            )
        if evidence_id in seen_ids:
            raise IntegrationExecutionEvidenceBridgeError(
                "each adapter must bind to a distinct authoritative evidence id"
            )
        seen_ids.add(evidence_id)

        item = next(
            (entry for entry in registry.items if entry.evidence_id == evidence_id),
            None,
        )
        if item is None:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative adapter evidence is not present in registry: {evidence_id}"
            )
        if item.source_type != "adapter_contract":
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence for adapter {adapter} must use adapter_contract source type"
            )
        if item.status != "accepted":
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence for adapter {adapter} must be accepted"
            )
        if item.approved_at is None:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence approval is required for adapter {adapter}"
            )
        approved_at = datetime.fromisoformat(item.approved_at)
        if approved_at > now:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence approval is future-dated for adapter {adapter}"
            )
        effective_from = datetime.fromisoformat(item.effective_from)
        if effective_from > now:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence is not yet effective for adapter {adapter}"
            )
        if item.effective_to is not None and datetime.fromisoformat(item.effective_to) <= now:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence is no longer effective for adapter {adapter}"
            )
        if item.expires_at is not None and datetime.fromisoformat(item.expires_at) <= now:
            raise IntegrationExecutionEvidenceBridgeError(
                f"authoritative evidence is expired for adapter {adapter}"
            )
        bindings.append((adapter, evidence_id, item.fingerprint))

    return tuple(bindings)


def build_integration_execution_evidence_binding(
    execution_readiness_gate: Path,
    authoritative_registry: AuthoritativeEvidenceRegistry,
    *,
    repository: str,
    candidate_sha: str,
    bound_by: str,
    bound_at: datetime,
    authoritative_evidence_ids: Mapping[str, str],
) -> IntegrationExecutionEvidenceBinding:
    if bound_at.tzinfo is None:
        raise IntegrationExecutionEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )
    gate = _load_gate(execution_readiness_gate)
    if gate.repository != repository:
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution repository mismatch"
        )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution candidate SHA mismatch"
        )
    if gate.target_environment not in {"staging", "pilot"}:
        raise IntegrationExecutionEvidenceBridgeError(
            "production is not an accepted integration execution environment"
        )
    gate_checked_at = gate.checked_at.astimezone(timezone.utc)
    bound_time = bound_at.astimezone(timezone.utc)
    if gate_checked_at > bound_time:
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution readiness check is future-dated"
        )
    if (
        bound_time - gate_checked_at
        > __import__("datetime").timedelta(hours=gate.max_execution_age_hours)
    ):
        raise IntegrationExecutionEvidenceBridgeError(
            "integration execution readiness evidence is stale"
        )

    adapter_bindings = _validate_authoritative_evidence(
        authoritative_registry,
        authoritative_evidence_ids,
        checked_at=bound_at,
    )
    if authoritative_registry.fingerprint != authoritative_registry.fingerprint.lower():
        raise IntegrationExecutionEvidenceBridgeError(
            "authoritative evidence registry fingerprint must be canonical lowercase"
        )

    return IntegrationExecutionEvidenceBinding(
        binding_version=1,
        repository=repository,
        candidate_sha=candidate_sha.lower(),
        target_environment=gate.target_environment,
        execution_id=gate.execution_id,
        execution_evidence_fingerprint=gate.execution_evidence_fingerprint.lower(),
        execution_verification_fingerprint=gate.execution_verification_fingerprint.lower(),
        execution_readiness_fingerprint=gate.fingerprint.lower(),
        registry_fingerprint=authoritative_registry.fingerprint.lower(),
        adapter_evidence_bindings=adapter_bindings,
        bound_by=bound_by.strip(),
        bound_at=bound_time,
    )
