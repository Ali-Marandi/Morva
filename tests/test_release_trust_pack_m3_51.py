from __future__ import annotations

import json
from pathlib import Path

import pytest

from morva.runtime.release_trust_pack import (
    ReleaseTrustEvidencePack,
    ReleaseTrustPackError,
    TrustPackSource,
)
from tests.test_trust_chain_m3_50 import make_fixture, SHA, VERIFY_AT
from tools.m3_51_release_trust_pack import build_pack, verify_pack


def build_test_pack(tmp_path: Path, name: str = "pack"):
    fixture = make_fixture(tmp_path)
    manifest, gate, rehearsal, bundle, bundle_public = fixture["files"]
    previous, intermediate, current = fixture["registry_files"]
    signing_rotation, root_rotation = fixture["ceremony_files"]
    old_root, new_root = fixture["root_public_files"]
    output = tmp_path / name
    pack = build_pack(
        output=output,
        root=tmp_path,
        bundle_file=bundle,
        manifest_file=manifest,
        gate_file=gate,
        rehearsal_file=rehearsal,
        public_key_file=bundle_public,
        previous_registry_file=previous,
        intermediate_registry_file=intermediate,
        current_registry_file=current,
        signing_key_rotation_file=signing_rotation,
        root_rotation_file=root_rotation,
        old_root_public_key_file=old_root,
        new_root_public_key_file=new_root,
        expected_sha=SHA,
        verified_at=VERIFY_AT,
        pack_id="morva-m3-51-test-pack",
    )
    return fixture, pack, output


def test_build_and_verify_release_trust_pack(tmp_path: Path):
    _, pack, output = build_test_pack(tmp_path)

    verified = verify_pack(
        pack_directory=output,
        expected_sha=SHA,
    )

    assert verified.fingerprint == pack.fingerprint
    assert verified.chain_fingerprint == pack.chain_fingerprint
    assert len(verified.sources) == len(ReleaseTrustEvidencePack.REQUIRED_ROLES)


def test_pack_is_deterministic_for_same_sources(tmp_path: Path):
    fixture = make_fixture(tmp_path)
    output_a = tmp_path / "pack-a"
    output_b = tmp_path / "pack-b"
    manifest, gate, rehearsal, bundle, bundle_public = fixture["files"]
    previous, intermediate, current = fixture["registry_files"]
    signing_rotation, root_rotation = fixture["ceremony_files"]
    old_root, new_root = fixture["root_public_files"]

    kwargs = {
        "root": tmp_path,
        "bundle_file": bundle,
        "manifest_file": manifest,
        "gate_file": gate,
        "rehearsal_file": rehearsal,
        "public_key_file": bundle_public,
        "previous_registry_file": previous,
        "intermediate_registry_file": intermediate,
        "current_registry_file": current,
        "signing_key_rotation_file": signing_rotation,
        "root_rotation_file": root_rotation,
        "old_root_public_key_file": old_root,
        "new_root_public_key_file": new_root,
        "expected_sha": SHA,
        "verified_at": VERIFY_AT,
        "pack_id": "morva-m3-51-test-pack",
    }
    first = build_pack(output=output_a, **kwargs)
    second = build_pack(output=output_b, **kwargs)

    assert first.fingerprint == second.fingerprint


def test_pack_rejects_missing_source_file(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)
    source = next(output.glob("sources/manifest.json"))
    source.unlink()

    with pytest.raises(ReleaseTrustPackError, match="file set mismatch"):
        verify_pack(pack_directory=output, expected_sha=SHA)


def test_pack_rejects_unexpected_source_file(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)
    extra = output / "sources" / "unexpected.txt"
    extra.write_text("unexpected", encoding="utf-8")

    with pytest.raises(ReleaseTrustPackError, match="file set mismatch"):
        verify_pack(pack_directory=output, expected_sha=SHA)


def test_pack_rejects_tampered_source_hash(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)
    source = output / "sources" / "manifest.json"
    source.write_text(source.read_text(encoding="utf-8") + "tamper", encoding="utf-8")

    with pytest.raises(ReleaseTrustPackError, match="sha256 mismatch"):
        verify_pack(pack_directory=output, expected_sha=SHA)


def test_pack_rejects_wrong_expected_sha(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)

    with pytest.raises(Exception, match="candidate_sha"):
        verify_pack(
            pack_directory=output,
            expected_sha="b" * 40,
        )


def test_pack_rejects_tampered_chain_fingerprint(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)
    pack_file = output / "pack.json"
    payload = json.loads(pack_file.read_text(encoding="utf-8"))
    payload["chain_fingerprint"] = "0" * 64
    pack_file.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ReleaseTrustPackError, match="fingerprint"):
        verify_pack(pack_directory=output, expected_sha=SHA)


def test_duplicate_roles_are_rejected():
    source = TrustPackSource("manifest", "sources/manifest.json", "a" * 64, 1)
    duplicate = TrustPackSource(
        "manifest",
        "sources/manifest-copy.json",
        "b" * 64,
        1,
    )
    common = {
        "pack_id": "pack",
        "release_id": "release",
        "tag": "v1",
        "candidate_sha": "a" * 40,
        "verified_at": VERIFY_AT,
        "bundle_fingerprint": "c" * 64,
        "signing_key_rotation_fingerprint": "d" * 64,
        "root_rotation_fingerprint": "e" * 64,
        "chain_fingerprint": "f" * 64,
        "previous_registry_fingerprint": "1" * 64,
        "intermediate_registry_fingerprint": "2" * 64,
        "current_registry_fingerprint": "3" * 64,
    }
    sources = [
        TrustPackSource(
            role,
            f"sources/{role}.json",
            "a" * 64,
            1,
        )
        for role in ReleaseTrustEvidencePack.REQUIRED_ROLES
    ]
    sources[-1] = duplicate
    sources.append(source)
    with pytest.raises(ReleaseTrustPackError, match="exactly one source"):
        ReleaseTrustEvidencePack(
            sources=tuple(sources),
            **common,
        )


def test_pack_rejects_private_key_material(tmp_path: Path):
    _, _, output = build_test_pack(tmp_path)
    private_key = output / "sources" / "private.key"
    private_key.write_text(
        "-----BEGIN PRIVATE KEY-----\\nforbidden\\n-----END PRIVATE KEY-----\\n",
        encoding="utf-8",
    )
    pack_file = output / "pack.json"
    payload = json.loads(pack_file.read_text(encoding="utf-8"))
    payload["sources"].append(
        {
            "role": "forbidden_private_material",
            "path": "sources/private.key",
            "sha256": "0" * 64,
            "size_bytes": private_key.stat().st_size,
        }
    )
    pack_file.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleaseTrustPackError):
        verify_pack(pack_directory=output, expected_sha=SHA)
