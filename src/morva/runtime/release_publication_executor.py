from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from morva.runtime.release_publication_gate import ReleasePublicationGate
from tools.m3_53_release_publication_gate import verify_gate


class ReleasePublicationExecutorError(ValueError):
    """Raised when release publication cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class PublicationAuthorization:
    authorization_id: str
    gate_fingerprint: str
    approved: bool
    approved_at: str
    approver: str
    scope: str = "github_release"

    def assert_matches(self, gate: ReleasePublicationGate) -> None:
        if not self.approved:
            raise ReleasePublicationExecutorError("publication authorization is not approved")
        if self.gate_fingerprint.lower() != gate.fingerprint.lower():
            raise ReleasePublicationExecutorError(
                "publication authorization does not match publication gate"
            )
        if self.scope != gate.publication_target:
            raise ReleasePublicationExecutorError(
                "publication authorization scope does not match target"
            )
        if not self.authorization_id.strip() or not self.approver.strip():
            raise ReleasePublicationExecutorError(
                "publication authorization identity is required"
            )
        if not self.approved_at.strip():
            raise ReleasePublicationExecutorError("publication authorization timestamp is required")


@dataclass(frozen=True, slots=True)
class ReleasePublicationPlan:
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    gate_fingerprint: str
    archive_sha256: str
    archive_path: str
    gate_path: str
    artifact_metadata_path: str

    def command(self) -> tuple[str, ...]:
        return (
            "gh",
            "release",
            "create",
            self.tag,
            self.archive_path,
            self.artifact_metadata_path,
            self.gate_path,
            "--repo",
            self.repository,
            "--verify-tag",
            "--target",
            self.candidate_sha,
            "--title",
            self.release_id,
            "--notes",
            (
                f"Morva release {self.release_id}

"
                f"candidate_sha={self.candidate_sha}
"
                f"trust_gate={self.gate_fingerprint}\\n"
                f"trust_artifact_sha256={self.archive_sha256}"
            ),
        )


def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ReleasePublicationExecutorError(
            f"failed to execute command: {command[0]}"
        ) from exc


def _remote_tag_sha(repository: str, tag: str) -> str | None:
    result = _run(
        (
            "git",
            "ls-remote",
            repository_to_remote(repository),
            f"refs/tags/{tag}",
            f"refs/tags/{tag}^{{}}",
        )
    )
    if result.returncode != 0:
        raise ReleasePublicationExecutorError(
            f"unable to inspect remote tag: {result.stderr.strip()}"
        )
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    candidates: list[str] = []
    for line in lines:
        fields = line.split()
        if len(fields) != 2:
            raise ReleasePublicationExecutorError(
                "unexpected git ls-remote output"
            )
        if fields[1] == f"refs/tags/{tag}^{{}}":
            candidates.insert(0, fields[0])
        elif fields[1] == f"refs/tags/{tag}":
            candidates.append(fields[0])
        else:
            raise ReleasePublicationExecutorError(
                "unexpected git ls-remote tag reference"
            )
    return candidates[0] if candidates else None


def repository_to_remote(repository: str) -> str:
    if repository.count("/") != 1 or not all(repository.split("/")):
        raise ReleasePublicationExecutorError(
            "repository must be in OWNER/REPO form"
        )
    return f"https://github.com/{repository}.git"


def _assert_no_existing_release(repository: str, tag: str) -> None:
    result = _run(("gh", "release", "view", tag, "--repo", repository))
    if result.returncode == 0:
        raise ReleasePublicationExecutorError("a GitHub Release already exists for the tag")
    if result.returncode != 1:
        raise ReleasePublicationExecutorError(
            f"unable to inspect existing GitHub Release: {result.stderr.strip()}"
        )


def load_authorization(path: Path) -> PublicationAuthorization:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("authorization_version", 0)) != 1:
        raise ReleasePublicationExecutorError(
            "unsupported publication authorization version"
        )
    if not isinstance(payload.get("approved"), bool):
        raise ReleasePublicationExecutorError(
            "publication authorization approved must be a Boolean"
        )
    return PublicationAuthorization(
        authorization_id=payload["authorization_id"],
        gate_fingerprint=payload["gate_fingerprint"],
        approved=bool(payload["approved"]),
        approved_at=payload["approved_at"],
        approver=payload["approver"],
        scope=payload.get("scope", "github_release"),
    )


def verify_publication_inputs(
    *,
    gate_file: Path,
    archive_path: Path,
    artifact_metadata: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ReleasePublicationGate:
    gate = verify_gate(
        gate_file=gate_file,
        archive_path=archive_path,
        artifact_metadata=artifact_metadata,
        expected_repository=repository,
        expected_tag=tag,
        expected_sha=candidate_sha,
    )
    if gate.candidate_sha.lower() != candidate_sha.lower():
        raise ReleasePublicationExecutorError("candidate SHA mismatch")
    remote_sha = _remote_tag_sha(repository, tag)
    if remote_sha is None:
        raise ReleasePublicationExecutorError("required release tag does not exist remotely")
    if remote_sha.lower() != candidate_sha.lower():
        raise ReleasePublicationExecutorError("remote release tag does not point to candidate SHA")
    _assert_no_existing_release(repository, tag)
    return gate


def execute_publication(
    *,
    gate_file: Path,
    archive_path: Path,
    artifact_metadata: Path,
    authorization_file: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ReleasePublicationPlan:
    gate = verify_publication_inputs(
        gate_file=gate_file,
        archive_path=archive_path,
        artifact_metadata=artifact_metadata,
        repository=repository,
        tag=tag,
        candidate_sha=candidate_sha,
    )
    authorization = load_authorization(authorization_file)
    authorization.assert_matches(gate)
    plan = ReleasePublicationPlan(
        repository=repository,
        release_id=gate.release_id,
        tag=gate.tag,
        candidate_sha=gate.candidate_sha,
        gate_fingerprint=gate.fingerprint,
        archive_sha256=gate.archive_sha256,
        archive_path=str(archive_path),
        gate_path=str(gate_file),
        artifact_metadata_path=str(artifact_metadata),
    )
    result = _run(plan.command())
    if result.returncode != 0:
        raise ReleasePublicationExecutorError(
            f"GitHub Release publication failed: {result.stderr.strip()}"
        )
    return plan


def prepare_publication(
    *,
    gate_file: Path,
    archive_path: Path,
    artifact_metadata: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ReleasePublicationPlan:
    gate = verify_publication_inputs(
        gate_file=gate_file,
        archive_path=archive_path,
        artifact_metadata=artifact_metadata,
        repository=repository,
        tag=tag,
        candidate_sha=candidate_sha,
    )
    return ReleasePublicationPlan(
        repository=repository,
        release_id=gate.release_id,
        tag=gate.tag,
        candidate_sha=gate.candidate_sha,
        gate_fingerprint=gate.fingerprint,
        archive_sha256=gate.archive_sha256,
        archive_path=str(archive_path),
        gate_path=str(gate_file),
        artifact_metadata_path=str(artifact_metadata),
    )