from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ImportManifest:
    source_name: str
    template_version: str
    period: str
    owner: str
    file_sha256: str
    received_at: str
    provenance: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ImportIssue:
    issue_code: str
    severity: str
    record_key: str
    evidence: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ImportValidation:
    accepted: bool
    issues: tuple[ImportIssue, ...]


def sha256_file(path: str | Path) -> str:
    file_path = Path(path)
    digest = sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_period(period: str) -> None:
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:].isdigit():
        raise ValueError("period must use YYYY-MM format")
    month = int(period[5:])
    if not 1 <= month <= 12:
        raise ValueError("period month must be between 01 and 12")


def validate_columns(
    rows: Iterable[Mapping[str, object]],
    required_columns: Iterable[str],
    *,
    source_name: str,
) -> ImportValidation:
    rows = tuple(rows)
    required = tuple(required_columns)
    if not rows:
        return ImportValidation(False, (ImportIssue("EMPTY_SOURCE", "critical", source_name, {"rows": 0}),))
    present = set(rows[0])
    missing = [column for column in required if column not in present]
    if missing:
        return ImportValidation(
            False,
            (ImportIssue("REQUIRED_COLUMN_MISSING", "critical", source_name, {"missing": missing}),),
        )
    return ImportValidation(True, ())
