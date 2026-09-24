#!/usr/bin/env python3
"""Fail-closed consistency checks for package/release version identifiers."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
import tomllib


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise SystemExit("release hygiene: invalid pyproject project.version")
    return version


def changelog_version() -> str:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for line in changelog.splitlines():
        if line.startswith("## "):
            match = VERSION_RE.search(line)
            if match:
                return match.group(1)
    raise SystemExit("release hygiene: CHANGELOG has no versioned top-level entry")


def normalized_tag(value: str) -> str:
    return value[1:] if value.startswith("v") else value


def check_archive_names(version: str, names: list[str]) -> None:
    archives = [
        name
        for name in names
        if name.endswith((".whl", ".tar.gz", ".zip"))
    ]
    if not archives:
        raise SystemExit("release hygiene: published release has no distribution archive")
    mismatched = [name for name in archives if version not in name]
    if mismatched:
        raise SystemExit(
            "release hygiene: distribution archive version mismatch: "
            + ", ".join(sorted(mismatched))
        )


def release_event_assets() -> tuple[str, list[str]] | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    if event_name != "release" or not event_path:
        return None
    payload: dict[str, Any] = json.loads(Path(event_path).read_text(encoding="utf-8"))
    release = payload.get("release")
    if not isinstance(release, dict):
        raise SystemExit("release hygiene: release event payload is malformed")
    tag_name = release.get("tag_name")
    assets = release.get("assets", [])
    if not isinstance(tag_name, str) or not isinstance(assets, list):
        raise SystemExit("release hygiene: release event metadata is malformed")
    names = [
        item["name"]
        for item in assets
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    ]
    return tag_name, names


def local_dist_assets() -> list[str]:
    dist = ROOT / "dist"
    if not dist.is_dir():
        return []
    return [path.name for path in dist.iterdir() if path.is_file()]


def main() -> None:
    version = project_version()
    changelog = changelog_version()
    if changelog != version:
        raise SystemExit(
            f"release hygiene: pyproject={version}, CHANGELOG={changelog}"
        )

    ref_type = os.environ.get("GITHUB_REF_TYPE")
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_type == "tag" and ref_name and normalized_tag(ref_name) != version:
        raise SystemExit(
            f"release hygiene: pyproject={version}, git tag={ref_name}"
        )

    event_assets = release_event_assets()
    if event_assets is not None:
        tag_name, names = event_assets
        if normalized_tag(tag_name) != version:
            raise SystemExit(
                f"release hygiene: pyproject={version}, release tag={tag_name}"
            )
        check_archive_names(version, names)
    else:
        local_assets = local_dist_assets()
        if local_assets:
            check_archive_names(version, local_assets)

    print(f"PASS: release identifiers are consistent at {version}")


if __name__ == "__main__":
    main()
