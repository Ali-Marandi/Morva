from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.trusted_key_registry import (
    TrustedKeyRegistry,
    TrustedKeyRegistryError,
    TrustedSigningKey,
)


NOW = datetime(2026, 9, 18, 5, 0, tzinfo=timezone.utc)


def record(public_key, status="active", valid_from=NOW, valid_until=None):
    return TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(public_key),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public_key),
        status=status,
        valid_from=valid_from,
        valid_until=valid_until,
    )


def test_registry_accepts_active_matching_key():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    registry = TrustedKeyRegistry("morva-signing", 1, (record(public),))

    registry.assert_trusted(TrustedKeyRegistry.key_id_for(public), public, NOW)


def test_registry_rejects_unknown_revoked_and_expired_keys():
    first = Ed25519PrivateKey.generate().public_key()
    second = Ed25519PrivateKey.generate().public_key()
    registry = TrustedKeyRegistry("morva-signing", 1, (record(first),))
    with pytest.raises(TrustedKeyRegistryError, match="not registered"):
        registry.assert_trusted(TrustedKeyRegistry.key_id_for(second), second, NOW)

    revoked = registry.revoke_key(record(first).key_id)
    with pytest.raises(TrustedKeyRegistryError, match="revoked"):
        revoked.assert_trusted(record(first).key_id, first, NOW)

    expired = TrustedKeyRegistry(
        "morva-signing",
        1,
        (
            record(
                second,
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                valid_until=datetime(2026, 9, 17, tzinfo=timezone.utc),
            ),
        ),
    )
    with pytest.raises(TrustedKeyRegistryError, match="expired"):
        expired.assert_trusted(record(second).key_id, second, NOW)


def test_rotation_retires_old_key_and_versions_registry():
    old = Ed25519PrivateKey.generate().public_key()
    new = Ed25519PrivateKey.generate().public_key()
    registry = TrustedKeyRegistry("morva-signing", 1, (record(old),))

    rotated = registry.rotate_key(record(old).key_id, record(new))
    assert rotated.version == 2
    assert rotated.key(record(old).key_id).status == "retired"
    assert rotated.key(record(old).key_id).replacement_key_id == record(new).key_id
    rotated.assert_trusted(
        record(new).key_id,
        new,
        datetime(2026, 9, 18, 6, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(TrustedKeyRegistryError, match="retired"):
        rotated.assert_trusted(record(old).key_id, old, NOW)


def test_registry_detects_public_key_hash_tampering():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    bad = TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(public),
        public_key_sha256="f" * 64,
        status="active",
        valid_from=NOW,
    )
    registry = TrustedKeyRegistry("morva-signing", 1, (bad,))
    with pytest.raises(TrustedKeyRegistryError, match="hash"):
        registry.assert_trusted(bad.key_id, public, NOW)


def test_registry_fingerprint_changes_after_rotation():
    old = Ed25519PrivateKey.generate().public_key()
    new = Ed25519PrivateKey.generate().public_key()
    registry = TrustedKeyRegistry("morva-signing", 1, (record(old),))

    rotated = registry.rotate_key(record(old).key_id, record(new))
    assert registry.fingerprint != rotated.fingerprint
