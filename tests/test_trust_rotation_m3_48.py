from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.signed_trusted_key_registry import SignedTrustedKeyRegistry
from morva.runtime.trust_rotation import (
    TrustRegistryRotationCeremony,
    TrustRotationError,
)
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_46_signed_trusted_registry import write_signed_registry
from tools.m3_48_trust_rotation import build_ceremony, verify_ceremony, write_ceremony


NOW = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
EFFECTIVE = NOW + timedelta(hours=1)


def make_record(public_key, valid_from):
    return TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(public_key),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public_key),
        status="active",
        valid_from=valid_from,
    )


def make_rotation():
    old = Ed25519PrivateKey.generate()
    new = Ed25519PrivateKey.generate()
    previous = TrustedKeyRegistry(
        "morva-signing",
        7,
        (make_record(old.public_key(), NOW - timedelta(days=30)),),
    )
    replacement = TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(new.public_key()),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(new.public_key()),
        status="active",
        valid_from=EFFECTIVE,
    )
    current = previous.rotate_key(
        TrustedKeyRegistry.key_id_for(old.public_key()),
        replacement,
    )
    return previous, current, old, new


def make_ceremony(previous, current, old, new, root):
    return TrustRegistryRotationCeremony(
        ceremony_id="rotation-007-008",
        registry_id="morva-signing",
        from_version=7,
        to_version=8,
        old_key_id=TrustedKeyRegistry.key_id_for(old.public_key()),
        new_key_id=TrustedKeyRegistry.key_id_for(new.public_key()),
        effective_at=EFFECTIVE,
        previous_registry_fingerprint=previous.fingerprint,
        new_registry_fingerprint=current.fingerprint,
        root_key_id=TrustedKeyRegistry.key_id_for(root.public_key()),
    )


def test_ceremony_matches_valid_rotation():
    previous, current, old, new = make_rotation()
    root = Ed25519PrivateKey.generate()
    make_ceremony(previous, current, old, new, root).assert_matches(previous, current)


def test_build_and_verify_round_trip(tmp_path: Path):
    previous, current, old, new = make_rotation()
    root = Ed25519PrivateKey.generate()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(root, NOW)
    current_signed = SignedTrustedKeyRegistry(current).sign(root, NOW + timedelta(minutes=1))
    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    root_file = tmp_path / "root.pem"
    ceremony_file = tmp_path / "ceremony.json"
    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(current_signed, current_file)
    root_file.write_bytes(
        root.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    ceremony = build_ceremony(
        previous_file,
        current_file,
        root_file,
        "rotation-007-008",
        TrustedKeyRegistry.key_id_for(old.public_key()),
        TrustedKeyRegistry.key_id_for(new.public_key()),
        EFFECTIVE,
    )
    write_ceremony(ceremony, ceremony_file)
    loaded = verify_ceremony(ceremony_file, previous_file, current_file, root_file)
    assert loaded == ceremony


def test_rejects_non_consecutive_versions():
    with pytest.raises(TrustRotationError, match="consecutive"):
        TrustRegistryRotationCeremony(
            "rotation",
            "morva-signing",
            7,
            9,
            "old",
            "new",
            EFFECTIVE,
            "a" * 64,
            "b" * 64,
            "root",
        )


def test_rejects_wrong_effective_time():
    previous, current, old, new = make_rotation()
    root = Ed25519PrivateKey.generate()
    ceremony = make_ceremony(previous, current, old, new, root)
    wrong = TrustRegistryRotationCeremony(
        ceremony.ceremony_id,
        ceremony.registry_id,
        ceremony.from_version,
        ceremony.to_version,
        ceremony.old_key_id,
        ceremony.new_key_id,
        EFFECTIVE + timedelta(minutes=1),
        ceremony.previous_registry_fingerprint,
        ceremony.new_registry_fingerprint,
        ceremony.root_key_id,
    )
    with pytest.raises(TrustRotationError, match="valid_from"):
        wrong.assert_matches(previous, current)


def test_rejects_changed_non_rotation_key():
    old = Ed25519PrivateKey.generate()
    new = Ed25519PrivateKey.generate()
    other = Ed25519PrivateKey.generate()
    previous = TrustedKeyRegistry(
        "morva-signing",
        7,
        (
            make_record(old.public_key(), NOW - timedelta(days=30)),
            make_record(other.public_key(), NOW - timedelta(days=10)),
        ),
    )
    replacement = TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(new.public_key()),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(new.public_key()),
        status="active",
        valid_from=EFFECTIVE,
    )
    rotated = previous.rotate_key(
        TrustedKeyRegistry.key_id_for(old.public_key()),
        replacement,
    )
    other_changed = TrustedSigningKey(
        key_id=rotated.keys[1].key_id,
        public_key_sha256=rotated.keys[1].public_key_sha256,
        status="active",
        valid_from=NOW,
    )
    malformed = TrustedKeyRegistry(
        "morva-signing",
        8,
        (rotated.keys[0], other_changed, rotated.keys[2]),
    )
    root = Ed25519PrivateKey.generate()
    ceremony = TrustRegistryRotationCeremony(
        "rotation",
        "morva-signing",
        7,
        8,
        TrustedKeyRegistry.key_id_for(old.public_key()),
        TrustedKeyRegistry.key_id_for(new.public_key()),
        EFFECTIVE,
        previous.fingerprint,
        malformed.fingerprint,
        TrustedKeyRegistry.key_id_for(root.public_key()),
    )
    with pytest.raises(TrustRotationError, match="non-rotated key"):
        ceremony.assert_matches(previous, malformed)


def test_rejects_wrong_root_binding():
    previous, current, old, new = make_rotation()
    root = Ed25519PrivateKey.generate()
    other_root = Ed25519PrivateKey.generate()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(root, NOW)
    current_signed = SignedTrustedKeyRegistry(current).sign(other_root, NOW)
    ceremony = make_ceremony(previous, current, old, new, root)
    with pytest.raises(TrustRotationError, match="new registry root key"):
        ceremony.assert_signed_registries(previous_signed, current_signed)


def test_ceremony_fingerprint_is_deterministic():
    root = Ed25519PrivateKey.generate()
    values = dict(
        ceremony_id="rotation-007-008",
        registry_id="morva-signing",
        from_version=7,
        to_version=8,
        old_key_id="old",
        new_key_id="new",
        effective_at=EFFECTIVE,
        previous_registry_fingerprint="a" * 64,
        new_registry_fingerprint="b" * 64,
        root_key_id=TrustedKeyRegistry.key_id_for(root.public_key()),
    )
    first = TrustRegistryRotationCeremony(**values)
    second = TrustRegistryRotationCeremony(**values)
    assert first.fingerprint == second.fingerprint


def test_serialized_ceremony_is_fail_closed(tmp_path: Path):
    previous, current, old, new = make_rotation()
    root = Ed25519PrivateKey.generate()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(root, NOW)
    current_signed = SignedTrustedKeyRegistry(current).sign(root, NOW + timedelta(minutes=1))
    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    root_file = tmp_path / "root.pem"
    ceremony_file = tmp_path / "ceremony.json"
    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(current_signed, current_file)
    root_file.write_bytes(
        root.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    ceremony = build_ceremony(
        previous_file,
        current_file,
        root_file,
        "rotation-007-008",
        TrustedKeyRegistry.key_id_for(old.public_key()),
        TrustedKeyRegistry.key_id_for(new.public_key()),
        EFFECTIVE,
    )
    write_ceremony(ceremony, ceremony_file)
    payload = json.loads(ceremony_file.read_text(encoding="utf-8"))
    payload["effective_at"] = (EFFECTIVE + timedelta(minutes=1)).isoformat()
    ceremony_file.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(TrustRotationError, match="valid_from"):
        verify_ceremony(ceremony_file, previous_file, current_file, root_file)



def test_rotation_policy_matches_versioned_key_trust():
    previous, current, old, new = make_rotation()
    old_id = TrustedKeyRegistry.key_id_for(old.public_key())
    new_id = TrustedKeyRegistry.key_id_for(new.public_key())
    before_effective = EFFECTIVE - timedelta(seconds=1)

    previous.assert_trusted(old_id, old.public_key(), before_effective)
    with pytest.raises(Exception, match="retired|not registered"):
        current.assert_trusted(old_id, old.public_key(), EFFECTIVE)
    current.assert_trusted(new_id, new.public_key(), EFFECTIVE)
    with pytest.raises(Exception, match="not registered"):
        previous.assert_trusted(new_id, new.public_key(), EFFECTIVE)


def test_previous_and_new_registry_fingerprints_are_distinct():
    previous, current, old, new = make_rotation()
    assert previous.fingerprint != current.fingerprint
