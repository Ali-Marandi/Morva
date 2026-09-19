from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import gzip
import io
import json
from pathlib import Path
import tarfile


class ReleaseTrustArtifactError(ValueError):
    """Raised when a release trust artifact is invalid."""


@dataclass(frozen=True, slots=True)
class ReleaseTrustArtifact:
    artifact_id: str
    release_id: str
    tag: str
    candidate_sha: str
    pack_fingerprint: str
    archive_filename: str
    archive_sha256: str
    archive_size_bytes: int

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ReleaseTrustArtifactError("artifact_id is required")
        if not self.release_id.strip() or not self.tag.strip():
            raise ReleaseTrustArtifactError("release_id and tag are required")
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef" for char in self.candidate_sha.lower()
        ):
            raise ReleaseTrustArtifactError("candidate_sha must be a Git commit SHA-1")
        if len(self.pack_fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in self.pack_fingerprint.lower()
        ):
            raise ReleaseTrustArtifactError(
                "pack_fingerprint must be a SHA-256 hex digest"
            )
        if not self.archive_filename.strip() or Path(self.archive_filename).name != self.archive_filename:
            raise ReleaseTrustArtifactError(
                "archive_filename must be a plain file name"
            )
        if len(self.archive_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.archive_sha256.lower()
        ):
            raise ReleaseTrustArtifactError(
                "archive_sha256 must be a SHA-256 hex digest"
            )
        if self.archive_size_bytes <= 0:
            raise ReleaseTrustArtifactError("archive_size_bytes must be positive")

    @property
    def fingerprint(self) -> str:
        payload = {
            "artifact_id": self.artifact_id,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "pack_fingerprint": self.pack_fingerprint.lower(),
            "archive_filename": self.archive_filename,
            "archive_sha256": self.archive_sha256.lower(),
            "archive_size_bytes": self.archive_size_bytes,
        }
        canonical = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def artifact_id_for(pack_fingerprint: str) -> str:
        if len(pack_fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in pack_fingerprint.lower()
        ):
            raise ReleaseTrustArtifactError(
                "pack_fingerprint must be a SHA-256 hex digest"
            )
        return f"morva-trust-evidence-v1-{pack_fingerprint.lower()}"

    def to_payload(self) -> dict[str, object]:
        return {
            "artifact_version": 1,
            "artifact_id": self.artifact_id,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "pack_fingerprint": self.pack_fingerprint,
            "archive_filename": self.archive_filename,
            "archive_sha256": self.archive_sha256,
            "archive_size_bytes": self.archive_size_bytes,
            "fingerprint": self.fingerprint,
        }


def _safe_member_name(path: str) -> str:
    candidate = Path(path)
    if (
        not path
        or candidate.is_absolute()
        or ".." in candidate.parts
        or path.startswith("./")
    ):
        raise ReleaseTrustArtifactError(
            f"archive member path is unsafe: {path}"
        )
    normalized = candidate.as_posix()
    if normalized != path or normalized == "":
        raise ReleaseTrustArtifactError(
            f"archive member path is not canonical: {path}"
        )
    return normalized


def create_deterministic_archive(pack_directory: Path, archive_path: Path) -> str:
    base = pack_directory.resolve()
    if not base.is_dir():
        raise ReleaseTrustArtifactError(f"pack directory does not exist: {base}")
    if archive_path.exists():
        raise ReleaseTrustArtifactError(
            "archive output already exists; artifacts are write-once"
        )
    files = sorted(
        path
        for path in base.rglob("*")
        if path.is_file()
    )
    if not files or not (base / "pack.json").is_file():
        raise ReleaseTrustArtifactError("pack directory must contain pack.json")
    seen: set[str] = set()
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for path in files:
            if path.is_symlink():
                raise ReleaseTrustArtifactError(
                    f"symbolic links are forbidden in artifact sources: {path}"
                )
            member_name = _safe_member_name(path.relative_to(base).as_posix())
            if member_name in seen:
                raise ReleaseTrustArtifactError(
                    f"duplicate archive member: {member_name}"
                )
            seen.add(member_name)
            data = path.read_bytes()
            info = tarfile.TarInfo(member_name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    compressed = gzip.compress(tar_buffer.getvalue(), compresslevel=9, mtime=0)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(compressed)
    return sha256(compressed).hexdigest()


def verify_archive_member_safety(archive_path: Path) -> tuple[str, ...]:
    if not archive_path.is_file():
        raise ReleaseTrustArtifactError(f"archive does not exist: {archive_path}")
    names: list[str] = []
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            _safe_member_name(member.name)
            if not member.isfile():
                raise ReleaseTrustArtifactError(
                    f"non-regular archive member is forbidden: {member.name}"
                )
            if member.name in names:
                raise ReleaseTrustArtifactError(
                    f"duplicate archive member: {member.name}"
                )
            names.append(member.name)
            if archive.extractfile(member) is None:
                raise ReleaseTrustArtifactError(
                    f"archive member has no readable data: {member.name}"
                )
    if "pack.json" not in names:
        raise ReleaseTrustArtifactError("archive must contain pack.json")
    return tuple(names)