from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

from morva.runtime.release_publication_gate import ReleasePublicationGate
from morva.runtime.release_trust_artifact import ReleaseTrustArtifact
from tools.m3_52_release_trust_artifact import verify_artifact
from tools.m3_53_release_publication_gate import verify_gate


class ReleasePostPublicationError(ValueError):
    """Raised when a published GitHub Release fails integrity verification."""


@dataclass(frozen=True, slots=True)
class ReleaseAssetIntegrity:
    name: str
    size_bytes: int
    digest: str

    def __post_init__(self) -> None:
        if not self.name.strip() or Path(self.name).name != self.name:
            raise ReleasePostPublicationError(
                "release asset name must be a plain file name"
            )
        if self.size_bytes <= 0:
            raise ReleasePostPublicationError(
                "release asset size must be positive"
            )
        if (
            len(self.digest) != 71
            or not self.digest.startswith("sha256:")
            or any(
                char not in "0123456789abcdef"
                for char in self.digest[7:].lower()
            )
        ):
            raise ReleasePostPublicationError(
                "release asset digest must be sha256:<64 hex characters>"
            )

    @property
    def normalized_digest(self) -> str:
        return f"sha256:{self.digest[7:].lower()}"

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "size_bytes": self.size_bytes,
            "digest": self.normalized_digest,
        }


@dataclass(frozen=True, slots=True)
class ReleasePostPublicationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    artifact_id: str
    artifact_fingerprint: str
    archive_sha256: str
    archive_size_bytes: int
    gate_fingerprint: str
    github_release_id: int
    github_release_url: str
    github_release_name: str
    github_target_commitish: str
    published_at: str
    assets: tuple[ReleaseAssetIntegrity, ...]
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.verifier_version != 1:
            raise ReleasePostPublicationError(
                "unsupported post-publication verifier version"
            )
        if not self.repository.strip() or not self.release_id.strip():
            raise ReleasePostPublicationError(
                "repository and release_id are required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise ReleasePostPublicationError(
                "candidate_sha must be a Git commit SHA-1"
            )
        for name, value in (
            ("artifact_fingerprint", self.artifact_fingerprint),
            ("archive_sha256", self.archive_sha256),
            ("gate_fingerprint", self.gate_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef"
                for char in value.lower()
            ):
                raise ReleasePostPublicationError(
                    f"{name} must be a SHA-256 hex digest"
                )
        if self.github_release_id <= 0:
            raise ReleasePostPublicationError(
                "github_release_id must be positive"
            )
        if not self.github_release_url.strip():
            raise ReleasePostPublicationError("github_release_url is required")
        if not self.github_release_name.strip():
            raise ReleasePostPublicationError("github_release_name is required")
        if not self.github_target_commitish.strip():
            raise ReleasePostPublicationError(
                "github_target_commitish is required"
            )
        if not self.published_at.strip():
            raise ReleasePostPublicationError("published_at is required")
        if self.archive_size_bytes <= 0:
            raise ReleasePostPublicationError(
                "archive_size_bytes must be positive"
            )
        if self.verified_at.tzinfo is None:
            raise ReleasePostPublicationError(
                "verified_at must be timezone-aware"
            )
        if not self.assets:
            raise ReleasePostPublicationError(
                "at least one release asset is required"
            )
        names = [asset.name for asset in self.assets]
        if len(names) != len(set(names)):
            raise ReleasePostPublicationError(
                "receipt cannot contain duplicate asset names"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint.lower(),
            "archive_sha256": self.archive_sha256.lower(),
            "archive_size_bytes": self.archive_size_bytes,
            "gate_fingerprint": self.gate_fingerprint.lower(),
            "github_release_id": self.github_release_id,
            "github_release_url": self.github_release_url,
            "github_release_name": self.github_release_name,
            "github_target_commitish": self.github_target_commitish.lower(),
            "published_at": self.published_at,
            "assets": [asset.to_payload() for asset in self.assets],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "artifact_id": self.artifact_id,
            "artifact_fingerprint": self.artifact_fingerprint,
            "archive_sha256": self.archive_sha256,
            "archive_size_bytes": self.archive_size_bytes,
            "gate_fingerprint": self.gate_fingerprint,
            "github_release_id": self.github_release_id,
            "github_release_url": self.github_release_url,
            "github_release_name": self.github_release_name,
            "github_target_commitish": self.github_target_commitish,
            "published_at": self.published_at,
            "assets": [asset.to_payload() for asset in self.assets],
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _run(command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ReleasePostPublicationError(
            f"failed to execute command: {command[0]}"
        ) from exc


def _remote_tag_sha(repository: str, tag: str) -> str | None:
    result = _run(
        (
            "git",
            "ls-remote",
            f"https://github.com/{repository}.git",
            f"refs/tags/{tag}",
            f"refs/tags/{tag}^{{}}",
        )
    )
    if result.returncode != 0:
        raise ReleasePostPublicationError(
            f"unable to inspect remote tag: {result.stderr.strip()}"
        )
    lines = result.stdout.strip().splitlines()
    if not lines:
        return None
    peeled: str | None = None
    direct: str | None = None
    for line in lines:
        fields = line.split()
        if len(fields) != 2:
            raise ReleasePostPublicationError(
                "unexpected git ls-remote output"
            )
        if fields[1] == f"refs/tags/{tag}^{{}}":
            peeled = fields[0]
        elif fields[1] == f"refs/tags/{tag}":
            direct = fields[0]
        else:
            raise ReleasePostPublicationError(
                "unexpected git ls-remote tag reference"
            )
    return peeled or direct


def _release_api_path(repository: str, tag: str) -> str:
    if repository.count("/") != 1 or not all(repository.split("/")):
        raise ReleasePostPublicationError(
            "repository must be in OWNER/REPO form"
        )
    if not tag.strip():
        raise ReleasePostPublicationError("tag is required")
    return f"repos/{repository}/releases/tags/{quote(tag, safe='')}"


def _load_release(repository: str, tag: str) -> dict[str, object]:
    result = _run(("gh", "api", _release_api_path(repository, tag)))
    if result.returncode != 0:
        raise ReleasePostPublicationError(
            f"unable to fetch GitHub Release: {result.stderr.strip()}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ReleasePostPublicationError(
            "GitHub Release response is not valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ReleasePostPublicationError(
            "GitHub Release response must be an object"
        )
    return payload


def _hash_file(path: Path) -> tuple[str, int]:
    if not path.is_file():
        raise ReleasePostPublicationError(
            f"asset file does not exist: {path}"
        )
    data = path.read_bytes()
    return sha256(data).hexdigest(), len(data)


def _expected_assets(
    *,
    archive_path: Path,
    artifact_metadata: Path,
    gate_file: Path,
) -> dict[str, ReleaseAssetIntegrity]:
    values: dict[str, ReleaseAssetIntegrity] = {}
    for path in (archive_path, artifact_metadata, gate_file):
        digest, size = _hash_file(path)
        asset = ReleaseAssetIntegrity(
            name=path.name,
            size_bytes=size,
            digest=f"sha256:{digest}",
        )
        if asset.name in values:
            raise ReleasePostPublicationError(
                f"duplicate expected asset name: {asset.name}"
            )
        values[asset.name] = asset
    return values


def _validate_release_assets(
    raw_assets: object,
    expected: dict[str, ReleaseAssetIntegrity],
) -> tuple[ReleaseAssetIntegrity, ...]:
    if not isinstance(raw_assets, list):
        raise ReleasePostPublicationError(
            "GitHub Release assets must be an array"
        )
    observed: dict[str, ReleaseAssetIntegrity] = {}
    for raw in raw_assets:
        if not isinstance(raw, dict):
            raise ReleasePostPublicationError(
                "GitHub Release asset entries must be objects"
            )
        name = raw.get("name")
        state = raw.get("state")
        size = raw.get("size")
        digest = raw.get("digest")
        if not isinstance(name, str) or not name.strip():
            raise ReleasePostPublicationError(
                "GitHub Release asset name is missing"
            )
        if state != "uploaded":
            raise ReleasePostPublicationError(
                f"GitHub Release asset is not uploaded: {name}"
            )
        if not isinstance(size, int) or isinstance(size, bool):
            raise ReleasePostPublicationError(
                f"GitHub Release asset size is invalid: {name}"
            )
        if not isinstance(digest, str):
            raise ReleasePostPublicationError(
                f"GitHub Release asset digest is missing: {name}"
            )
        asset = ReleaseAssetIntegrity(
            name=name,
            size_bytes=size,
            digest=digest,
        )
        if name in observed:
            raise ReleasePostPublicationError(
                f"duplicate GitHub Release asset: {name}"
            )
        observed[name] = asset

    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        detail: list[str] = []
        if missing:
            detail.append(f"missing={','.join(missing)}")
        if unexpected:
            detail.append(f"unexpected={','.join(unexpected)}")
        raise ReleasePostPublicationError(
            "release asset set mismatch: " + "; ".join(detail)
        )

    for name, expected_asset in expected.items():
        actual = observed[name]
        if actual.size_bytes != expected_asset.size_bytes:
            raise ReleasePostPublicationError(
                f"release asset size mismatch: {name}"
            )
        if actual.normalized_digest != expected_asset.normalized_digest:
            raise ReleasePostPublicationError(
                f"release asset digest mismatch: {name}"
            )
    return tuple(observed[name] for name in sorted(observed))


def verify_published_release(
    *,
    gate_file: Path,
    archive_path: Path,
    artifact_metadata: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> ReleasePostPublicationReceipt:
    gate = verify_gate(
        gate_file=gate_file,
        archive_path=archive_path,
        artifact_metadata=artifact_metadata,
        expected_repository=repository,
        expected_tag=tag,
        expected_sha=candidate_sha,
    )
    artifact = verify_artifact(
        archive_path=archive_path,
        metadata_file=artifact_metadata,
        expected_sha=candidate_sha,
    )
    if not isinstance(artifact, ReleaseTrustArtifact):
        raise ReleasePostPublicationError(
            "M3.52 verifier returned an unexpected artifact type"
        )
    if not isinstance(gate, ReleasePublicationGate):
        raise ReleasePostPublicationError(
            "M3.53 verifier returned an unexpected gate type"
        )
    gate.assert_matches_artifact(artifact)

    remote_sha = _remote_tag_sha(repository, tag)
    if remote_sha is None:
        raise ReleasePostPublicationError(
            "required release tag does not exist remotely"
        )
    if remote_sha.lower() != candidate_sha.lower():
        raise ReleasePostPublicationError(
            "remote release tag does not point to candidate SHA"
        )

    release = _load_release(repository, tag)
    if release.get("tag_name") != tag:
        raise ReleasePostPublicationError(
            "GitHub Release tag does not match expected tag"
        )
    release_name = release.get("name")
    if release_name != gate.release_id:
        raise ReleasePostPublicationError(
            "GitHub Release name does not match release_id"
        )
    target_commitish = release.get("target_commitish")
    if not isinstance(target_commitish, str):
        raise ReleasePostPublicationError(
            "GitHub Release target_commitish is missing"
        )
    if target_commitish.lower() != candidate_sha.lower():
        raise ReleasePostPublicationError(
            "GitHub Release target_commitish does not match candidate SHA"
        )
    if release.get("draft") is not False:
        raise ReleasePostPublicationError(
            "GitHub Release must be published, not draft"
        )
    if release.get("prerelease") is not False:
        raise ReleasePostPublicationError(
            "GitHub Release must not be a prerelease"
        )
    published_at = release.get("published_at")
    if not isinstance(published_at, str) or not published_at.strip():
        raise ReleasePostPublicationError(
            "GitHub Release published_at is missing"
        )
    github_release_id = release.get("id")
    if not isinstance(github_release_id, int) or isinstance(
        github_release_id, bool
    ):
        raise ReleasePostPublicationError(
            "GitHub Release id is invalid"
        )
    github_release_url = release.get("html_url")
    if not isinstance(github_release_url, str) or not github_release_url.strip():
        raise ReleasePostPublicationError(
            "GitHub Release html_url is missing"
        )

    expected_assets = _expected_assets(
        archive_path=archive_path,
        artifact_metadata=artifact_metadata,
        gate_file=gate_file,
    )
    assets = _validate_release_assets(
        release.get("assets"),
        expected_assets,
    )
    return ReleasePostPublicationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=gate.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        artifact_id=artifact.artifact_id,
        artifact_fingerprint=artifact.fingerprint,
        archive_sha256=artifact.archive_sha256,
        archive_size_bytes=artifact.archive_size_bytes,
        gate_fingerprint=gate.fingerprint,
        github_release_id=github_release_id,
        github_release_url=github_release_url,
        github_release_name=release_name,
        github_target_commitish=target_commitish,
        published_at=published_at,
        assets=assets,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(receipt: ReleasePostPublicationReceipt, path: Path) -> None:
    if path.exists():
        raise ReleasePostPublicationError(
            "verification receipt output already exists; receipts are write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            receipt.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
