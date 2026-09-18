from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.signed_trusted_key_registry import (
    SignedTrustedKeyRegistry,
    SignedTrustedRegistryError,
)
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey


NOW = datetime(2026, 9, 18, 7, 0, tzinfo=timezone.utc)


def make_registry():
    signing = Ed25519PrivateKey.generate()
    public = signing.public_key()
    record = TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(public),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public),
        status="active",
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    return TrustedKeyRegistry("morva-signing", 1, (record,)), signing


def test_signed_registry_round_trips_and_is_deterministic():
    registry, root = make_registry()
    first = SignedTrustedKeyRegistry(registry).sign(root, NOW)
    second = SignedTrustedKeyRegistry(registry).sign(root, NOW)

    first.verify_signature(root.public_key())
    first.assert_signed()
    assert first.fingerprint == second.fingerprint


def test_signed_registry_rejects_wrong_root_key():
    registry, root = make_registry()
    signed = SignedTrustedKeyRegistry(registry).sign(root, NOW)

    with pytest.raises(SignedTrustedRegistryError, match="root public key"):
        signed.verify_signature(Ed25519PrivateKey.generate().public_key())


def test_signed_registry_rejects_tampered_registry():
    registry, root = make_registry()
    signed = SignedTrustedKeyRegistry(registry).sign(root, NOW)
    changed = TrustedKeyRegistry(registry.registry_id, registry.version + 1, registry.keys)
    tampered = SignedTrustedKeyRegistry(changed, signed.signature)

    with pytest.raises(SignedTrustedRegistryError, match="verification failed"):
        tampered.verify_signature(root.public_key())


def test_signed_registry_requires_timezone_aware_signature():
    registry, root = make_registry()

    with pytest.raises(SignedTrustedRegistryError, match="timezone-aware"):
        SignedTrustedKeyRegistry(registry).sign(
            root,
            datetime(2026, 9, 18, 7, 0),
        )
