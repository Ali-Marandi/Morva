from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from morva.runtime.release_publication_executor import (
    PublicationAuthorization,
    ReleasePublicationExecutorError,
    _remote_tag_sha,
    execute_publication,
    prepare_publication,
)
from tests.test_release_publication_gate_m3_53 import build_test_gate


SHA = "a" * 40
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def ready_run(command):
    if command[0] == "git":
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=f"{SHA} refs/tags/{TAG}\n{SHA} refs/tags/{TAG}^{{}}\n",
            stderr="",
        )
    return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")


def test_annotated_remote_tag_uses_peeled_commit(monkeypatch):
    monkeypatch.setattr(
        "morva.runtime.release_publication_executor._run",
        ready_run,
    )
    assert _remote_tag_sha(REPOSITORY, TAG) == SHA


def test_prepare_rejects_wrong_remote_tag(monkeypatch, tmp_path: Path):
    _, _, gate_file, archive, metadata = build_test_gate(tmp_path)

    def run(command):
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{'b' * 40} refs/tags/{TAG}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")

    monkeypatch.setattr("morva.runtime.release_publication_executor._run", run)
    with pytest.raises(ReleasePublicationExecutorError, match="does not point"):
        prepare_publication(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_prepare_rejects_existing_release(monkeypatch, tmp_path: Path):
    _, _, gate_file, archive, metadata = build_test_gate(tmp_path)

    def run(command):
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{SHA} refs/tags/{TAG}\n{SHA} refs/tags/{TAG}^{{}}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="existing release",
            stderr="",
        )

    monkeypatch.setattr("morva.runtime.release_publication_executor._run", run)
    with pytest.raises(ReleasePublicationExecutorError, match="already exists"):
        prepare_publication(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_prepare_fails_closed_on_release_lookup_error(monkeypatch, tmp_path: Path):
    _, _, gate_file, archive, metadata = build_test_gate(tmp_path)

    def run(command):
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{SHA} refs/tags/{TAG}\\n",
                stderr="",
            )
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="authentication failed",
        )

    monkeypatch.setattr("morva.runtime.release_publication_executor._run", run)
    with pytest.raises(
        ReleasePublicationExecutorError,
        match="unable to inspect existing GitHub Release",
    ):
        prepare_publication(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_execute_requires_matching_authorization(monkeypatch, tmp_path: Path):
    artifact, gate, gate_file, archive, metadata = build_test_gate(tmp_path)

    def run(command):
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{SHA} refs/tags/{TAG}\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")

    monkeypatch.setattr("morva.runtime.release_publication_executor._run", run)
    auth = tmp_path / "authorization.json"
    auth.write_text(
        json.dumps(
            {
                "authorization_version": 1,
                "authorization_id": "AUTH-001",
                "gate_fingerprint": "0" * 64,
                "approved": True,
                "approved_at": "2026-09-19T22:00:00+00:00",
                "approver": "operator",
                "scope": "github_release",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ReleasePublicationExecutorError, match="does not match"):
        execute_publication(
            gate_file=gate_file,
            archive_path=archive,
            artifact_metadata=metadata,
            authorization_file=auth,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=artifact.candidate_sha,
        )
    assert gate.fingerprint != "0" * 64


def test_execute_runs_only_after_gate_and_authorization(monkeypatch, tmp_path: Path):
    artifact, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    commands = []

    def run(command):
        commands.append(command)
        if command[0] == "git":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=f"{SHA} refs/tags/{TAG}\n",
                stderr="",
            )
        if command[:4] == ("gh", "release", "view", TAG):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="not found")
        return subprocess.CompletedProcess(command, 0, stdout="https://example/release", stderr="")

    monkeypatch.setattr("morva.runtime.release_publication_executor._run", run)
    auth = tmp_path / "authorization.json"
    auth.write_text(
        json.dumps(
            {
                "authorization_version": 1,
                "authorization_id": "AUTH-002",
                "gate_fingerprint": gate.fingerprint,
                "approved": True,
                "approved_at": "2026-09-19T22:00:00+00:00",
                "approver": "authorized-operator",
                "scope": "github_release",
            }
        ),
        encoding="utf-8",
    )

    plan = execute_publication(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        authorization_file=auth,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=artifact.candidate_sha,
    )

    assert plan.candidate_sha == SHA
    assert plan.gate_fingerprint == gate.fingerprint
    assert commands[-1][:3] == ("gh", "release", "create")


def test_authorization_rejects_unapproved_gate(tmp_path: Path):
    _, gate, *_ = build_test_gate(tmp_path)
    authorization = PublicationAuthorization(
        authorization_id="AUTH-003",
        gate_fingerprint=gate.fingerprint,
        approved=False,
        approved_at="2026-09-19T22:00:00+00:00",
        approver="operator",
    )
    with pytest.raises(ReleasePublicationExecutorError, match="not approved"):
        authorization.assert_matches(gate)


def test_authorization_requires_timezone_aware_timestamp(tmp_path: Path):
    _, gate, *_ = build_test_gate(tmp_path)
    for value, expected in [
        ("not-a-timestamp", "ISO-8601"),
        ("2026-09-19T22:00:00", "timezone"),
    ]:
        authorization = PublicationAuthorization(
            authorization_id="AUTH-005",
            gate_fingerprint=gate.fingerprint,
            approved=True,
            approved_at=value,
            approver="operator",
        )
        with pytest.raises(ReleasePublicationExecutorError, match=expected):
            authorization.assert_matches(gate)


def test_authorization_requires_boolean_value(tmp_path: Path):
    _, _, _, _, metadata = build_test_gate(tmp_path)
    del metadata
    from morva.runtime.release_publication_executor import load_authorization

    auth = tmp_path / "authorization.json"
    auth.write_text(
        json.dumps(
            {
                "authorization_version": 1,
                "authorization_id": "AUTH-004",
                "gate_fingerprint": "a" * 64,
                "approved": "false",
                "approved_at": "2026-09-19T22:00:00+00:00",
                "approver": "operator",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ReleasePublicationExecutorError, match="Boolean"):
        load_authorization(auth)
