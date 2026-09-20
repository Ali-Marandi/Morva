from __future__ import annotations

from datetime import datetime

import pytest

from morva.integrations.ports import FailClosedAdapter, IntegrationNotConfigured
from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationReceipt,
)
from morva.runtime.integration_adapter_runtime import (
    IntegrationAdapterRuntime,
    IntegrationRuntimeActivationError,
    VerifiedAdapterRuntime,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40
GATE_FP = "b" * 64
VERIFIED_AT = datetime.fromisoformat("2026-09-20T03:30:00+00:00")


def _verification() -> IndependentAdapterActivationVerificationReceipt:
    return IndependentAdapterActivationVerificationReceipt(
        verifier_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        target_environment="staging",
        adapters=REQUIRED_ADAPTERS,
        activation_gate_fingerprint=GATE_FP,
        registry_fingerprint="c" * 64,
        authorization_id="AUTH-001",
        approver="external-operator",
        verified_at=VERIFIED_AT,
    )


def test_missing_implementation_fails_closed():
    runtime = IntegrationAdapterRuntime(
        verification=VerifiedAdapterRuntime.from_verification(_verification())
    )
    resolved = runtime.resolve("bank")
    assert isinstance(resolved, FailClosedAdapter)
    with pytest.raises(IntegrationNotConfigured, match="bank"):
        runtime.assert_configured("bank")


def test_missing_verification_fails_closed():
    implementation = object()
    runtime = IntegrationAdapterRuntime(
        verification=None,
        implementations={"bank": implementation},
    )
    assert isinstance(runtime.resolve("bank"), FailClosedAdapter)


def test_verified_implementation_is_resolved():
    implementation = object()
    runtime = IntegrationAdapterRuntime(
        verification=VerifiedAdapterRuntime.from_verification(_verification()),
        implementations={"bank": implementation},
    )
    assert runtime.resolve("bank") is implementation


def test_unsupported_adapter_is_rejected():
    runtime = IntegrationAdapterRuntime(verification=None)
    with pytest.raises(IntegrationRuntimeActivationError, match="unsupported"):
        runtime.resolve("unknown")


def test_noncanonical_verification_is_rejected():
    receipt = _verification()
    tampered = IndependentAdapterActivationVerificationReceipt(
        verifier_version=receipt.verifier_version,
        repository=receipt.repository,
        candidate_sha=receipt.candidate_sha,
        target_environment=receipt.target_environment,
        adapters=("bank",),
        activation_gate_fingerprint=receipt.activation_gate_fingerprint,
        registry_fingerprint=receipt.registry_fingerprint,
        authorization_id=receipt.authorization_id,
        approver=receipt.approver,
        verified_at=receipt.verified_at,
    )
    with pytest.raises(IntegrationRuntimeActivationError, match="canonical"):
        VerifiedAdapterRuntime.from_verification(tampered)
