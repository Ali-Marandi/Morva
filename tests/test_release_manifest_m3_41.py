import json
from pathlib import Path

import pytest

from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest, ReleaseManifestError
from tools.m3_41_release_manifest import build_manifest, load_manifest


SHA = "a" * 40


def test_manifest_hashes_real_artifacts_and_is_deterministic(tmp_path: Path):
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")

    first = build_manifest(tmp_path, "morva-1.0.1", "v1.0.1", SHA)
    second = build_manifest(tmp_path, "morva-1.0.1", "v1.0.1", SHA)

    assert [item.path for item in first.artifacts] == ["a.txt", "b.txt"]
    assert all(len(item.sha256) == 64 for item in first.artifacts)
    assert first.fingerprint == second.fingerprint
    first.verify_files(tmp_path)


def test_manifest_detects_modified_artifact(tmp_path: Path):
    target = tmp_path / "package.whl"
    target.write_bytes(b"original")
    manifest = build_manifest(tmp_path, "morva-1.0.1", "v1.0.1", SHA)

    target.write_bytes(b"tampered")
    with pytest.raises(ReleaseManifestError, match="sha256 mismatch"):
        manifest.verify_files(tmp_path)


def test_manifest_detects_added_artifact(tmp_path: Path):
    target = tmp_path / "package.whl"
    target.write_bytes(b"original")
    manifest = build_manifest(tmp_path, "morva-1.0.1", "v1.0.1", SHA)

    (tmp_path / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(ReleaseManifestError, match="unexpected artifacts"):
        manifest.verify_files(tmp_path)


def test_manifest_serialization_detects_fingerprint_tampering(tmp_path: Path):
    target = tmp_path / "package.whl"
    target.write_bytes(b"original")
    manifest = build_manifest(tmp_path, "morva-1.0.1", "v1.0.1", SHA)
    payload = {
        "release_id": manifest.release_id,
        "tag": manifest.tag,
        "candidate_sha": manifest.candidate_sha,
        "artifacts": [
            {"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes}
            for item in manifest.artifacts
        ],
        "fingerprint": manifest.fingerprint,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_manifest(path).fingerprint == manifest.fingerprint

    payload["tag"] = "v-tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        load_manifest(path)


def test_manifest_requires_exact_candidate_sha():
    manifest = ReleaseManifest(
        release_id="morva-1.0.1",
        tag="v1.0.1",
        candidate_sha=SHA,
        artifacts=(ReleaseArtifact("dist/morva.whl", "b" * 64, 10),),
    )

    manifest.assert_matches(SHA.upper())
    with pytest.raises(ReleaseManifestError, match="expected release commit"):
        manifest.assert_matches("f" * 40)


def test_manifest_rejects_duplicate_and_traversal_paths():
    artifact = ReleaseArtifact("dist/morva.whl", "b" * 64, 10)
    with pytest.raises(ReleaseManifestError, match="paths must be unique"):
        ReleaseManifest(
            release_id="morva-1.0.1",
            tag="v1.0.1",
            candidate_sha=SHA,
            artifacts=(artifact, artifact),
        )

    with pytest.raises(ReleaseManifestError, match="traversal-free"):
        ReleaseArtifact("../morva.whl", "b" * 64, 10)


def test_manifest_rejects_empty_artifact_set():
    with pytest.raises(ReleaseManifestError, match="at least one"):
        ReleaseManifest(
            release_id="morva-1.0.1",
            tag="v1.0.1",
            candidate_sha=SHA,
            artifacts=(),
        )
