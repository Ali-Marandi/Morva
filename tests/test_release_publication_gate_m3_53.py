from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from morva.runtime.release_publication_gate import (
    ReleasePublicationGateError,
)
from tests.test_release_trust_artifact_m3_52 import build_test_pack
from tools.m3_52_release_trust_artifact import build_artifact
from tools.m3_53_release_publication_gate import build_gate, verify_gate


NOW = datetime(2026, 9, 19, 17, 30, tzinfo=timezone.utc)
SHA = "a" * 40
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def build_test_gate(tmp_path: Path):
    _, _, pack_dir = build_test_pack(tmp_path, "pack")
    archive = tmp_path / "trust.tar.gz"
    metadata = tmp_path / "artifact.json"
    artifact = build_artifact(
        pack_directory=pack_dir,
        output_archive=archive,
        metadata_file=metadata,
        expected_sha=SHA,
    )
    gate_file = tmp_path / "publication-gate.json"
    gate = build_gate(
        repository=REPOSITORY,
        archive_path=archive,
        artifact_metadata=metadata,
        output_gate=gate_file,
        expected_sha=SHA,
        expected_tag=TAG,
        verified_at=NOW,
    )
    return gate, gate_file, archive, metadata


def test_build_and_verify_publication_gate(tmp_path: Path):
    gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    verified = verify_gate(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        expected_repository=REPOSITORY,
        expected_tag=TAG,
        expected_sha=SHA,
    )
    assert verified.fingerprint == gate.fingerprint
    assert verified.release_ref == "refs/tags/v1.0.1"


def test_gate_rejects_repository_mismatch(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    with pytest.raises(ReleasePublicationGateError, match="repository mismatch"):
        verify_gate(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            expected_repository="other/repository",
            expected_tag=TAG,
            expected_sha=SHA,
        )


def test_gate_rejects_tag_mismatch(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    with pytest.raises(ReleasePublicationGateError, match="tag mismatch"):
        verify_gate(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            expected_repository=REPOSITORY,
            expected_tag="v9.9.9",
            expected_sha=SHA,
        )


def test_gate_rejects_candidate_sha_mismatch(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    with pytest.raises(Exception, match="candidate SHA|candidate_sha"):
        verify_gate(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            expected_repository=REPOSITORY,
            expected_tag=TAG,
            expected_sha="b" * 40,
        )


def test_gate_rejects_tampered_archive(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(Exception, match="archive sha256 mismatch"):
        verify_gate(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            expected_repository=REPOSITORY,
            expected_tag=TAG,
            expected_sha=SHA,
        )


def test_gate_rejects_tampered_release_ref(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    payload = json.loads(gate_file.read_text(encoding="utf-8"))
    payload["release_ref"] = "refs/tags/v1.0.2"
    gate_file.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleasePublicationGateError, match="release_ref"):
        verify_gate(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            expected_repository=REPOSITORY,
            expected_tag=TAG,
            expected_sha=SHA,
        )


def test_gate_is_write_once(tmp_path: Path):
    _, gate_file, archive, metadata = build_test_gate(tmp_path)
    with pytest.raises(ReleasePublicationGateError, match="write-once"):
        build_gate(
            repository=REPOSITORY,
            archive_path=archive,
            artifact_metadata=metadata,
            output_gate=gate_file,
            expected_sha=SHA,
            expected_tag=TAG,
            verified_at=NOW,
        )