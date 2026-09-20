from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationReceipt,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS
from morva.integrations.ports import FailClosedAdapter, IntegrationNotConfigured


class IntegrationRuntimeActivationError(ValueError):
    """Raised when an external adapter cannot be activated safely."""


@dataclass(frozen=True, slots=True)
class VerifiedAdapterRuntime:
    repository: str
    candidate_sha: str
    target_environment: str
    adapters: tuple[str, ...]
    activation_gate_fingerprint: str
    verification_fingerprint: str
    verified_at: datetime

    @classmethod
    def from_verification(
        cls,
        verification: IndependentAdapterActivationVerificationReceipt,
    ) -> "VerifiedAdapterRuntime":
        if verification.adapters != REQUIRED_ADAPTERS:
            raise IntegrationRuntimeActivationError(
                "verification does not cover the canonical adapter set"
            )
        if verification.target_environment not in {"staging", "pilot"}:
            raise IntegrationRuntimeActivationError(
                "verified adapter target environment is not activation-safe"
            )
        return cls(
            repository=verification.repository,
            candidate_sha=verification.candidate_sha,
            target_environment=verification.target_environment,
            adapters=verification.adapters,
            activation_gate_fingerprint=verification.activation_gate_fingerprint,
            verification_fingerprint=verification.fingerprint,
            verified_at=verification.verified_at,
        )


class IntegrationAdapterRuntime:
    """Resolves external adapters only after independent activation verification."""

    def __init__(
        self,
        *,
        verification: VerifiedAdapterRuntime | None,
        implementations: Mapping[str, object] | None = None,
    ) -> None:
        self._verification = verification
        self._implementations = dict(implementations or {})

    def resolve(self, adapter: str) -> object:
        if adapter not in REQUIRED_ADAPTERS:
            raise IntegrationRuntimeActivationError(
                f"unsupported adapter: {adapter}"
            )
        implementation = self._implementations.get(adapter)
        if implementation is None:
            return FailClosedAdapter()
        if self._verification is None:
            return FailClosedAdapter()
        if adapter not in self._verification.adapters:
            return FailClosedAdapter()
        return implementation

    def assert_configured(self, adapter: str) -> None:
        resolved = self.resolve(adapter)
        if isinstance(resolved, FailClosedAdapter):
            raise IntegrationNotConfigured(
                f"external integration is not activated for: {adapter}"
            )

    @property
    def activated_adapters(self) -> tuple[str, ...]:
        if self._verification is None:
            return ()
        return self._verification.adapters
