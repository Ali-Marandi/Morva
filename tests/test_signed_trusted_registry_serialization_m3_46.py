from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.signed_trusted_key_registry import (
    SignedTrustedKeyRegistry,
    SignedTrustedRegistryError,
)
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_46_signed_trusted_registry import load_signed_registry, write_signed_registry


NOW = datetime(2026, 9, 18, 8, 0, tzinfo=timezone.utc)


def make_signed_registry():
    signing = Ed25519PrivateKey.generate()
    public = signing.public_key()
    registry = TrustedKeyRegistry(
        "morva-signing",
        1,
        (
            TrustedSigningKey(
                key_id=TrustedKeyRegistry.key_id_for(public),
                public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public),
                status="active",
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )
    root = Ed25519PrivateKey.generate()
    return SignedTrustedKeyRegistry(registry).sign(root, NOW), root


def test_signed_registry_serializes_and_loads(tmp_path: Path):
    signed, root = make_signed_registry()
    path = tmp_path / "trusted-key-registry.json"

    write_signed_registry(signed, path)
    loaded = load_signed_registry(path)

    loaded.verify_signature(root.public_key())
    assert loaded.registry == signed.registry
    assert loaded.fingerprint == signed.fingerprint


def test_signed_registry_rejects_tampered_serialized_fingerprint(tmp_path: Path):
    signed, root = make_signed_registry()
    path = tmp_path / "trusted-key-registry.json"
    write_signed_registry(signed, path)
    payload = path.read_text(encoding="utf-8").replace(
        signed.registry.registry_id, "tampered-registry"
    )
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(SignedTrustedRegistryError, match="fingerprint"):
        load_signed_registry(path)


def test_signed_registry_rejects_wrong_root_after_serialization(tmp_path: Path):
    signed, _ = make_signed_registry()
    path = tmp_path / "trusted-key-registry.json"
    write_signed_registry(signed, path)
    loaded = load_signed_registry(path)

    with pytest.raises(SignedTrustedRegistryError, match="root public key"):
        loaded.verify_signature(Ed25519PrivateKey.generate().public_key())


def test_signed_registry_root_public_key_is_raw_hash_bound():
    signed, root = make_signed_registry()
    expected = SignedTrustedKeyRegistry.root_key_id_for(root.public_key())

    assert signed.signature is not None
    assert signed.signature.root_key_id == expected
    raw = root.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    assert len(raw) == 32
