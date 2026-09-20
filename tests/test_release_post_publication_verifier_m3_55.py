from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest

from morva.runtime.release_post_publication import (
    ReleasePostPublicationError,
    verify_published_release,
    write_receipt,
)
from tests.test_release_publication_gate_m3_53 import build_test_gate


SHA = "a" * 40
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def _asset(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "name": path.name,
        "state": "uploaded",
        "size": len(data),
        "digest": f"sha256:{sha256(data).hexdigest()}",
    }


def _release_payload(
    *,
    gate_file: Path,
    archive: Path,
    metadata: Path,
    tag: str = TAG,
    name: str = "Morva Release",
    target_commitish: str = SHA,
    draft: bool = False,
    prerelease: bool = False,
    assets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": 9001,
        "html_url": f"https://github.com/{REPOSITORY}/releases/tag/{tag}",
        "tag_name": tag,
        "name": name,
        "target_commitish": target_commitish,
        "draft": draft,
        "prerelease": prerelease,
        "published_at": "2026-09-19T23:00:00Z",
        "assets": (
            assets
            if assets is not None
            else [
                _asset(archive),
                _asset(metadata),
                _asset(gate_file),
            ]
        ),
    }


def _mock_runner(
    release: dict[str, object],
    *,
    remote_sha: str = SHA,
):
    commands: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...]):
        commands.append(command)
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{remote_sha} refs/tags/{TAG}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(release),
            stderr="",
        )

    return commands, run


def test_verify_published_release_roundtrip(monkeypatch, tmp_path: Path):
    artifact, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    del artifact
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    commands, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    receipt = verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )

    assert receipt.github_release_id == 9001
    assert receipt.release_id == gate.release_id
    assert {asset.name for asset in receipt.assets} == {
        archive.name,
        metadata.name,
        gate_file.name,
    }
    assert [command[0:2] for command in commands] == [
        ("git", "ls-remote"),
        ("gh", "api"),
    ]


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("tag_name", "wrong-tag", "tag does not match"),
        ("target_commitish", "b" * 40, "target_commitish"),
        ("name", "Wrong Release", "Release name"),
    ],
)
def test_release_identity_mismatch(
    monkeypatch,
    tmp_path: Path,
    field: str,
    value: object,
    match: str,
):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    release[field] = value
    commands, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    with pytest.raises(ReleasePostPublicationError, match=match):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )
    assert all(
        "release create" not in " ".join(command)
        and "release edit" not in " ".join(command)
        and "release delete" not in " ".join(command)
        and "release upload" not in " ".join(command)
        for command in commands
    )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("draft", True, "must be published"),
        ("prerelease", True, "must not be a prerelease"),
    ],
)
def test_release_state_mismatch(
    monkeypatch,
    tmp_path: Path,
    field: str,
    value: bool,
    match: str,
):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
        **{field: value},
    )
    _, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    with pytest.raises(ReleasePostPublicationError, match=match):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_remote_tag_mismatch(monkeypatch, tmp_path: Path):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    _, run = _mock_runner(release, remote_sha="b" * 40)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    with pytest.raises(ReleasePostPublicationError, match="remote release tag"):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


@pytest.mark.parametrize(
    ("asset_mutation", "match"),
    [
        (lambda assets: assets.pop(0), "asset set mismatch"),
        (
            lambda assets: assets.append(
                {
                    "name": "unexpected.txt",
                    "state": "uploaded",
                    "size": 1,
                    "digest": "sha256:" + "0" * 64,
                }
            ),
            "asset set mismatch",
        ),
    ],
)
def test_asset_set_mismatch(
    monkeypatch,
    tmp_path: Path,
    asset_mutation,
    match: str,
):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    assets = list(release["assets"])
    asset_mutation(assets)
    release["assets"] = assets
    _, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    with pytest.raises(ReleasePostPublicationError, match=match):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (
            lambda asset: asset.update(size=asset["size"] + 1),
            "size mismatch",
        ),
        (
            lambda asset: asset.update(digest="sha256:" + "0" * 64),
            "digest mismatch",
        ),
    ],
)
def test_asset_integrity_mismatch(
    monkeypatch,
    tmp_path: Path,
    mutation,
    match: str,
):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    mutation(release["assets"][0])
    _, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    with pytest.raises(ReleasePostPublicationError, match=match):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_release_json_invalid(monkeypatch, tmp_path: Path):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    del gate

    def run(command):
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{SHA} refs/tags/{TAG}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="{", stderr="")

    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)
    with pytest.raises(ReleasePostPublicationError, match="not valid JSON"):
        verify_published_release(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_release_api_is_read_only(monkeypatch, tmp_path: Path):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    commands, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert all(
        len(command) >= 2 and command[0:2] in {
            ("git", "ls-remote"),
            ("gh", "api"),
        }
        for command in commands
    )


def test_receipt_fingerprint_is_stable(monkeypatch, tmp_path: Path):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    _, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    first = verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    second = verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert first.fingerprint == second.fingerprint


def test_receipt_is_write_once(monkeypatch, tmp_path: Path):
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    _, run = _mock_runner(release)
    monkeypatch.setattr("morva.runtime.release_post_publication._run", run)

    receipt = verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "receipt.json"
    write_receipt(receipt, output)
    with pytest.raises(ReleasePostPublicationError, match="write-once"):
        write_receipt(receipt, output)
