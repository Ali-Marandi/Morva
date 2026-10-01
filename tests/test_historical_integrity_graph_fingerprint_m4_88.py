from __future__ import annotations

import json
from pathlib import Path

from morva.runtime.historical_integrity_primitives import canonical_sha256

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")
FINGERPRINT_PATH = Path("contracts/historical_integrity_graph_m4_88.json")

EXPECTED_GRAPH_FINGERPRINT = "5351a1f955e5ca0d7d748f53ae7573553c1e02758d1be053b681676f0173de8c"

EXPECTED_ARTIFACT_KEYS = {
    "schema_version",
    "contract_id",
    "manifest_path",
    "fingerprint_scope",
    "algorithm",
    "canonicalization",
    "projection_fields",
    "graph_fingerprint",
}


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _graph_projection(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": manifest["schema_version"],
        "contract_id": manifest["contract_id"],
        "layers": [
            {
                "id": layer["id"],
                "path": layer["path"],
                "required_modules": layer["required_modules"],
                "forbidden_tokens": layer["forbidden_tokens"],
                "test": layer["test"],
            }
            for layer in manifest["layers"]
        ],
        "guards": manifest["guards"],
        "graph": manifest["graph"],
    }


def test_integrity_graph_fingerprint_artifact_matches_manifest() -> None:
    manifest = _read_json(MANIFEST_PATH)
    fingerprint = _read_json(FINGERPRINT_PATH)

    assert set(fingerprint) == EXPECTED_ARTIFACT_KEYS
    assert fingerprint["schema_version"] == 1
    assert fingerprint["contract_id"] == "morva.historical_integrity.graph.m4_88"
    assert fingerprint["manifest_path"] == str(MANIFEST_PATH)
    assert fingerprint["fingerprint_scope"] == "integrity_graph_contract"
    assert fingerprint["algorithm"] == "sha256"
    assert fingerprint["canonicalization"] == "json-sort-keys-compact-utf8"
    assert fingerprint["projection_fields"] == [
        "schema_version",
        "contract_id",
        "layers",
        "guards",
        "graph",
    ]
    assert fingerprint["graph_fingerprint"] == canonical_sha256(
        _graph_projection(manifest)
    )
    assert fingerprint["graph_fingerprint"] == EXPECTED_GRAPH_FINGERPRINT


def test_integrity_graph_fingerprint_is_stable_and_nonempty() -> None:
    manifest = _read_json(MANIFEST_PATH)
    fingerprint = canonical_sha256(_graph_projection(manifest))

    assert len(fingerprint) == 64
    assert fingerprint == canonical_sha256(_graph_projection(manifest))
    assert fingerprint == EXPECTED_GRAPH_FINGERPRINT


def test_integrity_graph_fingerprint_changes_when_contract_changes() -> None:
    manifest = _read_json(MANIFEST_PATH)
    baseline = canonical_sha256(_graph_projection(manifest))

    changed_graph = dict(manifest["graph"])
    changed_graph["sequence"] = list(reversed(changed_graph["sequence"]))
    changed_projection = _graph_projection(manifest)
    changed_projection["graph"] = changed_graph

    assert canonical_sha256(changed_projection) != baseline
