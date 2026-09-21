from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.production_readiness_handoff import (
    HandoffSource,
    ProductionReadinessHandoffError,
    build_handoff,
    load_handoff,
    verify_handoff_sources,
    write_handoff,
)


def _sources(tmp_path: Path):
    (tmp_path / "a.json").write_text('{"a":1}\n', encoding="utf-8")
    (tmp_path / "nested").mkdir(exist_ok=True)
    (tmp_path / "nested" / "b.json").write_text('{"b":2}\n', encoding="utf-8")
    return ("a.json", "nested/b.json")


def _handoff(tmp_path: Path):
    return build_handoff(
        root=tmp_path,
        source_paths=_sources(tmp_path),
        repository="Ali-Marandi/Morva",
        release_id="Morva Release",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        convergence_fingerprint="b" * 64,
        created_at=datetime.fromisoformat("2026-09-20T01:20:00+00:00"),
    )


def test_roundtrip_and_source_verification(tmp_path: Path):
    handoff = _handoff(tmp_path)
    assert len(handoff.sources) == 2
    verify_handoff_sources(handoff=handoff, root=tmp_path)


def test_tampered_source_is_rejected(tmp_path: Path):
    handoff = _handoff(tmp_path)
    (tmp_path / "a.json").write_text('{"a":999}\n', encoding="utf-8")
    with pytest.raises(ProductionReadinessHandoffError, match="sha256 mismatch"):
        verify_handoff_sources(handoff=handoff, root=tmp_path)


def test_extra_source_is_rejected(tmp_path: Path):
    handoff = _handoff(tmp_path)
    (tmp_path / "extra.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ProductionReadinessHandoffError, match="source set"):
        verify_handoff_sources(handoff=handoff, root=tmp_path)


def test_private_key_material_is_rejected(tmp_path: Path):
    (tmp_path / "secret.txt").write_text(
        "-----BEGIN " + "PRIVATE KEY-----",
        encoding="utf-8",
    )
    with pytest.raises(ProductionReadinessHandoffError, match="private-key"):
        _build = build_handoff(
            root=tmp_path,
            source_paths=("secret.txt",),
            repository="Ali-Marandi/Morva",
            release_id="Morva Release",
            tag="v1.0.1",
            candidate_sha="a" * 40,
            convergence_fingerprint="b" * 64,
            created_at=datetime.now(timezone.utc),
        )


def test_manifest_tamper_is_rejected(tmp_path: Path):
    handoff = _handoff(tmp_path)
    path = tmp_path / "handoff.json"
    write_handoff(handoff, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        ProductionReadinessHandoffError,
        match="fingerprint mismatch",
    ):
        load_handoff(path)


def test_write_once(tmp_path: Path):
    handoff = _handoff(tmp_path)
    path = tmp_path / "handoff.json"
    write_handoff(handoff, path)
    with pytest.raises(ProductionReadinessHandoffError, match="write-once"):
        write_handoff(handoff, path)


def test_source_path_rejects_traversal():
    with pytest.raises(ProductionReadinessHandoffError):
        HandoffSource("../secret", "a" * 64, 1)


@pytest.mark.skipif(not hasattr(Path, "symlink_to"), reason="symlinks unavailable")
def test_symlink_is_rejected(tmp_path: Path):
    _sources(tmp_path)
    link = tmp_path / "link.json"
    link.symlink_to(tmp_path / "a.json")
    handoff = _handoff(tmp_path)
    with pytest.raises(ProductionReadinessHandoffError, match="symlink"):
        verify_handoff_sources(handoff=handoff, root=tmp_path)
