from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.root_trust_rotation import RootRotationCeremony, RootRotationError
from morva.runtime.signed_trusted_key_registry import SignedTrustedKeyRegistry
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_46_signed_trusted_registry import write_signed_registry
from tools.m3_49_root_trust_rotation import build_ceremony, verify_ceremony, write_ceremony


NOW = datetime(2026, 9, 19, 11, 0, tzinfo=timezone.utc)
EFFECTIVE = NOW + timedelta(hours=1)


def make_signing_record():
    signing = Ed25519PrivateKey.generate()
    return TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(signing.public_key()),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(signing.public_key()),
        status="active",
        valid_from=NOW - timedelta(days=30),
    )


def make_registries():
    signing = make_signing_record()
    previous = TrustedKeyRegistry("morva-signing", 10, (signing,))
    current = TrustedKeyRegistry("morva-signing", 11, (signing,))
    old_root = Ed25519PrivateKey.generate()
    new_root = Ed25519PrivateKey.generate()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(old_root, NOW)
    current_signed = SignedTrustedKeyRegistry(current).sign(
        new_root, NOW + timedelta(minutes=1)
    )
    return previous, current, previous_signed, current_signed, old_root, new_root


def ceremony_from_sources(previous_signed, current_signed, old_root, new_root):
    return RootRotationCeremony.create(
        ceremony_id="root-rotation-010-011",
        registry_id="morva-signing",
        previous=previous_signed,
        current=current_signed,
        old_root_private_key=old_root,
        new_root_private_key=new_root,
        effective_at=EFFECTIVE,
        transition_kind="scheduled_rotation",
        old_root_action="retire",
    )


def test_valid_root_rotation_uses_dual_handoff_signatures():
    previous, current, previous_signed, current_signed, old_root, new_root = (
        make_registries()
    )
    ceremony = ceremony_from_sources(
        previous_signed, current_signed, old_root, new_root
    )

    ceremony.assert_source_bindings(
        previous_signed,
        current_signed,
        old_root.public_key(),
        new_root.public_key(),
    )
    assert ceremony.old_root_key_id != ceremony.new_root_key_id
    assert ceremony.previous_registry_fingerprint == previous.fingerprint
    assert ceremony.new_registry_fingerprint == current.fingerprint


def test_build_and_verify_round_trip(tmp_path: Path):
    previous, current, previous_signed, current_signed, old_root, new_root = (
        make_registries()
    )
    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    old_root_file = tmp_path / "old-root.pem"
    new_root_file = tmp_path / "new-root.pem"
    ceremony_file = tmp_path / "ceremony.json"

    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(current_signed, current_file)
    for key, path in ((old_root, old_root_file), (new_root, new_root_file)):
        path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )

    ceremony = build_ceremony(
        previous_file,
        current_file,
        old_root_file,
        new_root_file,
        "root-rotation-010-011",
        EFFECTIVE,
        "scheduled_rotation",
        "retire",
    )
    write_ceremony(ceremony, ceremony_file)

    old_root_public_file = tmp_path / "old-root-public.pem"
    new_root_public_file = tmp_path / "new-root-public.pem"
    for key, path in (
        (old_root, old_root_public_file),
        (new_root, new_root_public_file),
    ):
        path.write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    loaded = verify_ceremony(
        ceremony_file,
        previous_file,
        current_file,
        old_root_public_file,
        new_root_public_file,
    )
    assert loaded == ceremony


def test_rejects_old_root_on_new_registry():
    _, _, previous_signed, current_signed, old_root, _ = make_registries()
    wrong_current = SignedTrustedKeyRegistry(
        current_signed.registry
    ).sign(old_root, NOW + timedelta(minutes=1))
    ceremony = ceremony_from_sources(
        previous_signed, current_signed, old_root, Ed25519PrivateKey.generate()
    )
    with pytest.raises(RootRotationError, match="new root"):
        ceremony.assert_source_bindings(
            previous_signed,
            wrong_current,
            old_root.public_key(),
            Ed25519PrivateKey.generate().public_key(),
        )


def test_rejects_tampered_handoff_signature():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    ceremony = ceremony_from_sources(
        previous_signed, current_signed, old_root, new_root
    )
    tampered = RootRotationCeremony(
        **{
            "ceremony_id": ceremony.ceremony_id,
            "registry_id": ceremony.registry_id,
            "from_version": ceremony.from_version,
            "to_version": ceremony.to_version,
            "old_root_key_id": ceremony.old_root_key_id,
            "new_root_key_id": ceremony.new_root_key_id,
            "effective_at": ceremony.effective_at,
            "transition_kind": ceremony.transition_kind,
            "old_root_action": ceremony.old_root_action,
            "previous_registry_fingerprint": ceremony.previous_registry_fingerprint,
            "new_registry_fingerprint": ceremony.new_registry_fingerprint,
            "old_root_signature_b64": ceremony.old_root_signature_b64[:-4] + "AAAA",
            "new_root_signature_b64": ceremony.new_root_signature_b64,
        }
    )
    with pytest.raises(RootRotationError, match="handoff signatures"):
        tampered.assert_source_bindings(
            previous_signed,
            current_signed,
            old_root.public_key(),
            new_root.public_key(),
        )


def test_emergency_recovery_requires_revoke():
    with pytest.raises(RootRotationError, match="requires revocation"):
        RootRotationCeremony(
            "recovery",
            "morva-signing",
            1,
            2,
            "old",
            "new",
            EFFECTIVE,
            "a" * 64,
            "b" * 64,
            "old-signature",
            "new-signature",
            "invalid-base64",
            "invalid-base64",
        )


def test_scheduled_rotation_requires_retirement():
    with pytest.raises(RootRotationError, match="requires retirement"):
        RootRotationCeremony(
            "rotation",
            "morva-signing",
            1,
            2,
            "old",
            "new",
            EFFECTIVE,
            "scheduled_rotation",
            "revoke",
            "a" * 64,
            "b" * 64,
            "AA==",
            "AA==",
        )


def test_rejects_registry_signed_after_effective_time():
    previous, current, _, _, old_root, new_root = make_registries()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(
        old_root, EFFECTIVE + timedelta(seconds=1)
    )
    current_signed = SignedTrustedKeyRegistry(current).sign(new_root, EFFECTIVE)
    ceremony = ceremony_from_sources(
        previous_signed, current_signed, old_root, new_root
    )
    with pytest.raises(RootRotationError, match="signed after"):
        ceremony.assert_source_bindings(
            previous_signed,
            current_signed,
            old_root.public_key(),
            new_root.public_key(),
        )


def test_fingerprint_changes_when_transition_mode_changes():
    previous, current, previous_signed, current_signed, old_root, new_root = (
        make_registries()
    )
    normal = ceremony_from_sources(
        previous_signed, current_signed, old_root, new_root
    )
    emergency = RootRotationCeremony(
        normal.ceremony_id,
        normal.registry_id,
        normal.from_version,
        normal.to_version,
        normal.old_root_key_id,
        normal.new_root_key_id,
        normal.effective_at,
        "emergency_recovery",
        "revoke",
        normal.previous_registry_fingerprint,
        normal.new_registry_fingerprint,
        normal.old_root_signature_b64,
        normal.new_root_signature_b64,
    )
    assert normal.fingerprint != emergency.fingerprint


def test_serialized_ceremony_fingerprint_is_fail_closed(tmp_path: Path):
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    ceremony = ceremony_from_sources(
        previous_signed, current_signed, old_root, new_root
    )
    ceremony_file = tmp_path / "ceremony.json"
    write_ceremony(ceremony, ceremony_file)
    payload = json.loads(ceremony_file.read_text(encoding="utf-8"))
    payload["new_root_key_id"] = "tampered"
    ceremony_file.write_text(json.dumps(payload), encoding="utf-8")

    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    old_public_file = tmp_path / "old-public.pem"
    new_public_file = tmp_path / "new-public.pem"
    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(current_signed, current_file)
    old_public_file.write_bytes(
        old_root.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    new_public_file.write_bytes(
        new_root.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    with pytest.raises(RootRotationError):
        verify_ceremony(
            ceremony_file,
            previous_file,
            current_file,
            old_public_file,
            new_public_file,
        )


def test_consecutive_version_contract():
    previous, current, previous_signed, current_signed, old_root, new_root = (
        make_registries()
    )
    bad_current = TrustedKeyRegistry(
        "morva-signing",
        13,
        (current.keys[0],),
    )
    bad_signed = SignedTrustedKeyRegistry(bad_current).sign(new_root, NOW)
    with pytest.raises(RootRotationError, match="versions must be consecutive"):
        RootRotationCeremony.create(
            ceremony_id="bad-version",
            registry_id="morva-signing",
            previous=previous_signed,
            current=bad_signed,
            old_root_private_key=old_root,
            new_root_private_key=new_root,
            effective_at=EFFECTIVE,
            transition_kind="scheduled_rotation",
            old_root_action="retire",
        )
