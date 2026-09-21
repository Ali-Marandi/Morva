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


def make_registries():
    signing = Ed25519PrivateKey.generate()
    record = TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(signing.public_key()),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(signing.public_key()),
        status="active",
        valid_from=NOW - timedelta(days=30),
    )
    previous = TrustedKeyRegistry("morva-signing", 10, (record,))
    current = TrustedKeyRegistry("morva-signing", 11, (record,))
    old_root = Ed25519PrivateKey.generate()
    new_root = Ed25519PrivateKey.generate()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(old_root, NOW)
    current_signed = SignedTrustedKeyRegistry(current).sign(
        new_root, NOW + timedelta(minutes=1)
    )
    return previous, current, previous_signed, current_signed, old_root, new_root


def make_private_key_file(key: Ed25519PrivateKey, path: Path) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def make_public_key_file(key: Ed25519PrivateKey, path: Path) -> None:
    path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def test_valid_scheduled_rotation_uses_dual_handoff_signatures():
    previous, current, previous_signed, current_signed, old_root, new_root = (
        make_registries()
    )
    ceremony = RootRotationCeremony.create(
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

    ceremony.assert_source_bindings(
        previous_signed,
        current_signed,
        old_root.public_key(),
        new_root.public_key(),
    )
    assert ceremony.old_root_signature_b64 is not None
    assert ceremony.recovery_signature_b64 is None
    assert ceremony.previous_registry_fingerprint == previous.fingerprint
    assert ceremony.new_registry_fingerprint == current.fingerprint


def test_build_and_verify_round_trip(tmp_path: Path):
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    previous_file = tmp_path / "previous.json"
    current_file = tmp_path / "current.json"
    old_root_file = tmp_path / "old-root.pem"
    new_root_file = tmp_path / "new-root.pem"
    ceremony_file = tmp_path / "ceremony.json"

    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(current_signed, current_file)
    make_private_key_file(old_root, old_root_file)
    make_private_key_file(new_root, new_root_file)

    ceremony = build_ceremony(
        previous_file,
        current_file,
        new_root_file,
        "root-rotation-010-011",
        EFFECTIVE,
        "scheduled_rotation",
        "retire",
        old_root_file,
    )
    write_ceremony(ceremony, ceremony_file)

    old_public_file = tmp_path / "old-root-public.pem"
    new_public_file = tmp_path / "new-root-public.pem"
    make_public_key_file(old_root, old_public_file)
    make_public_key_file(new_root, new_public_file)

    loaded = verify_ceremony(
        ceremony_file,
        previous_file,
        current_file,
        old_public_file,
        new_public_file,
    )
    assert loaded == ceremony


def test_emergency_recovery_works_without_old_root_signature():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    recovery = Ed25519PrivateKey.generate()
    ceremony = RootRotationCeremony.create(
        ceremony_id="root-recovery-010-011",
        registry_id="morva-signing",
        previous=previous_signed,
        current=current_signed,
        new_root_private_key=new_root,
        recovery_anchor_private_key=recovery,
        effective_at=EFFECTIVE,
        transition_kind="emergency_recovery",
        old_root_action="revoke",
    )

    ceremony.assert_source_bindings(
        previous_signed,
        current_signed,
        old_root.public_key(),
        new_root.public_key(),
        recovery.public_key(),
    )
    assert ceremony.old_root_signature_b64 is None
    assert ceremony.recovery_signature_b64 is not None
    assert ceremony.recovery_anchor_key_id == (
        TrustedKeyRegistry.key_id_for(recovery.public_key())
    )


def test_rejects_old_root_on_new_registry():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    wrong_current = SignedTrustedKeyRegistry(
        current_signed.registry
    ).sign(old_root, NOW + timedelta(minutes=1))
    ceremony = RootRotationCeremony.create(
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
    with pytest.raises(RootRotationError, match="root public keys"):
        ceremony.assert_source_bindings(
            previous_signed,
            wrong_current,
            old_root.public_key(),
            Ed25519PrivateKey.generate().public_key(),
        )


def test_rejects_tampered_handoff_signature():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    ceremony = RootRotationCeremony.create(
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
    tampered = RootRotationCeremony(
        ceremony.ceremony_id,
        ceremony.registry_id,
        ceremony.from_version,
        ceremony.to_version,
        ceremony.old_root_key_id,
        ceremony.new_root_key_id,
        ceremony.effective_at,
        ceremony.transition_kind,
        ceremony.old_root_action,
        ceremony.previous_registry_fingerprint,
        ceremony.new_registry_fingerprint,
        ("A" * 86 + "=="),
        ceremony.new_root_signature_b64,
    )
    with pytest.raises(RootRotationError, match="authorization signatures"):
        tampered.assert_source_bindings(
            previous_signed,
            current_signed,
            old_root.public_key(),
            new_root.public_key(),
        )


def test_emergency_recovery_requires_recovery_anchor():
    _, _, previous_signed, current_signed, _, new_root = make_registries()
    with pytest.raises(RootRotationError, match="recovery-anchor private key"):
        RootRotationCeremony.create(
            ceremony_id="recovery",
            registry_id="morva-signing",
            previous=previous_signed,
            current=current_signed,
            new_root_private_key=new_root,
            effective_at=EFFECTIVE,
            transition_kind="emergency_recovery",
            old_root_action="revoke",
        )


def test_scheduled_rotation_requires_retirement():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    with pytest.raises(RootRotationError, match="requires retirement"):
        RootRotationCeremony.create(
            ceremony_id="rotation",
            registry_id="morva-signing",
            previous=previous_signed,
            current=current_signed,
            old_root_private_key=old_root,
            new_root_private_key=new_root,
            effective_at=EFFECTIVE,
            transition_kind="scheduled_rotation",
            old_root_action="revoke",
        )


def test_rejects_registry_signed_after_effective_time():
    previous, current, _, _, old_root, new_root = make_registries()
    previous_signed = SignedTrustedKeyRegistry(previous).sign(
        old_root, EFFECTIVE + timedelta(seconds=1)
    )
    current_signed = SignedTrustedKeyRegistry(current).sign(new_root, EFFECTIVE)
    ceremony = RootRotationCeremony.create(
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
    with pytest.raises(RootRotationError, match="signed after"):
        ceremony.assert_source_bindings(
            previous_signed,
            current_signed,
            old_root.public_key(),
            new_root.public_key(),
        )


def test_serialized_ceremony_fingerprint_is_fail_closed(tmp_path: Path):
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    ceremony = RootRotationCeremony.create(
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
    make_public_key_file(old_root, old_public_file)
    make_public_key_file(new_root, new_public_file)

    with pytest.raises(RootRotationError):
        verify_ceremony(
            ceremony_file,
            previous_file,
            current_file,
            old_public_file,
            new_public_file,
        )


def test_consecutive_version_contract():
    previous, _, previous_signed, _, old_root, new_root = make_registries()
    bad_current = TrustedKeyRegistry("morva-signing", 13, previous.keys)
    bad_signed = SignedTrustedKeyRegistry(bad_current).sign(new_root, NOW)
    with pytest.raises(RootRotationError, match="consecutive"):
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


def test_fingerprint_is_deterministic():
    _, _, previous_signed, current_signed, old_root, new_root = make_registries()
    first = RootRotationCeremony.create(
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
    second = RootRotationCeremony.create(
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
    assert first.fingerprint == second.fingerprint
