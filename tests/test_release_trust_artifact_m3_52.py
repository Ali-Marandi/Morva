from __future__ import annotations

from hashlib import sha256
import gzip
import io
from pathlib import Path
import tarfile

import pytest

from morva.runtime.release_trust_artifact import (
    ReleaseTrustArtifact,
    ReleaseTrustArtifactError,
    create_deterministic_archive,
    verify_archive_member_safety,
)
from tests.test_release_trust_pack_m3_51 import build_test_pack
from tests.test_trust_chain_m3_50 import SHA
from tools.m3_52_release_trust_artifact import build_artifact, verify_artifact


def test_build_and_verify_release_trust_artifact(tmp_path: Path):
    _, pack, pack_dir = build_test_pack(tmp_path, "pack")
    archive = tmp_path / "morva-trust-evidence.tar.gz"
    metadata = tmp_path / "artifact.json"
    artifact = build_artifact(
        pack_directory=pack_dir,
        output_archive=archive,
        metadata_file=metadata,
        expected_sha=SHA,
    )

    verified = verify_artifact(
        archive_path=archive,
        metadata_file=metadata,
        expected_sha=SHA,
    )
    assert verified.fingerprint == artifact.fingerprint
    assert verified.pack_fingerprint == pack.fingerprint
    assert verify_archive_member_safety(archive)


def test_artifact_archive_is_deterministic(tmp_path: Path):
    _, _, pack_dir = build_test_pack(tmp_path, "pack")
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    first_hash = create_deterministic_archive(pack_dir, first)
    second_hash = create_deterministic_archive(pack_dir, second)
    assert first_hash == second_hash
    assert first.read_bytes() == second.read_bytes()


def test_artifact_rejects_tampered_archive(tmp_path: Path):
    _, _, pack_dir = build_test_pack(tmp_path, "pack")
    archive = tmp_path / "artifact.tar.gz"
    metadata = tmp_path / "artifact.json"
    build_artifact(
        pack_directory=pack_dir,
        output_archive=archive,
        metadata_file=metadata,
        expected_sha=SHA,
    )
    data = bytearray(archive.read_bytes())
    data[-1] ^= 0x01
    archive.write_bytes(data)

    with pytest.raises(ReleaseTrustArtifactError, match="sha256 mismatch"):
        verify_artifact(archive_path=archive, metadata_file=metadata, expected_sha=SHA)


def test_artifact_rejects_unsafe_tar_member(tmp_path: Path):
    archive = tmp_path / "unsafe.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        data = b"forbidden"
        info = tarfile.TarInfo("../escape.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    archive.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))

    with pytest.raises(ReleaseTrustArtifactError, match="unsafe"):
        verify_archive_member_safety(archive)


def test_artifact_rejects_symlink_member(tmp_path: Path):
    archive = tmp_path / "symlink.tar.gz"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "pack.json"
        tar.addfile(info)
    archive.write_bytes(gzip.compress(buffer.getvalue(), mtime=0))

    with pytest.raises(ReleaseTrustArtifactError, match="non-regular"):
        verify_archive_member_safety(archive)


def test_artifact_id_is_bound_to_pack_fingerprint():
    fingerprint = sha256(b"pack").hexdigest()
    artifact_id = ReleaseTrustArtifact.artifact_id_for(fingerprint)
    assert artifact_id.endswith(fingerprint)
    assert artifact_id.startswith("morva-trust-evidence-v1-")