from __future__ import annotations

import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_schema_and_layer_contract() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == 1
    assert manifest["contract_id"] == "morva.historical_integrity.m4_77_m4_81"

    layers = manifest["layers"]
    assert isinstance(layers, list)
    assert len(layers) == 5

    layer_ids = [layer["id"] for layer in layers]
    assert len(layer_ids) == len(set(layer_ids))
    assert manifest["graph"]["sequence"] == layer_ids
    assert manifest["graph"]["cycle_policy"] == "acyclic"


def test_manifest_paths_and_contract_shape_are_real() -> None:
    for layer in _manifest()["layers"]:
        assert Path(layer["path"]).is_file(), layer["id"]
        assert isinstance(layer["required_modules"], list)
        assert isinstance(layer["forbidden_tokens"], list)

        test = layer["test"]
        assert Path(test["path"]).is_file(), layer["id"]
        assert isinstance(test["required_modules"], list)
        assert isinstance(test["expected_symbols"], list)


def test_manifest_shared_sha256_guard_is_complete() -> None:
    guard = _manifest()["guards"]["shared_sha256_primitive"]
    assert len(guard["runtime_paths"]) == 3
    assert guard["required_module"] == "morva.runtime.historical_integrity_primitives"
    assert guard["forbidden_import_module"] == "hashlib"
    assert guard["forbidden_import_name"] == "sha256"
    assert guard["forbidden_call_name"] == "sha256"
