from __future__ import annotations

import ast
import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _guard() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))[
        "guards"
    ]["shared_sha256_primitive"]


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path), filename=str(path))


def test_historical_integrity_runtimes_use_shared_sha256_primitive() -> None:
    guard = _guard()
    for path_value in guard["runtime_paths"]:
        path = Path(path_value)
        tree = _tree(path)
        shared_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == guard["required_module"]
            and any(alias.name == "canonical_sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert shared_import, (
            f"{path} must import canonical_sha256 from the shared primitive"
        )


def test_historical_integrity_runtimes_have_no_local_sha256_implementation() -> None:
    guard = _guard()
    for path_value in guard["runtime_paths"]:
        path = Path(path_value)
        tree = _tree(path)
        forbidden_hash_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == guard["forbidden_import_module"]
            and any(alias.name == guard["forbidden_import_name"] for alias in node.names)
            for node in ast.walk(tree)
        )
        forbidden_sha256_call = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == guard["forbidden_call_name"]
            for node in ast.walk(tree)
        )
        forbidden_json_dump = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "json"
            and node.func.attr == "dumps"
            for node in ast.walk(tree)
        )
        assert not forbidden_hash_import, (
            f"{path} reintroduces a local hashlib.sha256 import"
        )
        assert not forbidden_sha256_call, f"{path} reintroduces a local sha256() call"
        assert not forbidden_json_dump, (
            f"{path} reintroduces local json.dumps fingerprint serialization"
        )
