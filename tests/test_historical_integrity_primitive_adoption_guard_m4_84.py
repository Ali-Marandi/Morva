from __future__ import annotations

import ast
import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_historical_integrity_runtimes_use_manifest_shared_sha256_primitive() -> None:
    guard = _manifest()["guards"]["shared_sha256_primitive"]
    required_module = guard["required_module"]
    for path_value in guard["runtime_paths"]:
        path = Path(path_value)
        assert path.is_file()
        tree = _tree(path)
        assert any(
            isinstance(node, ast.ImportFrom)
            and node.module == required_module
            and any(
                alias.name == "canonical_sha256"
                for alias in node.names
            )
            for node in ast.walk(tree)
        ), f"{path} must import canonical_sha256 from {required_module}"


def test_historical_integrity_runtimes_have_no_manifest_forbidden_sha256_usage() -> None:
    guard = _manifest()["guards"]["shared_sha256_primitive"]
    for path_value in guard["runtime_paths"]:
        path = Path(path_value)
        tree = _tree(path)
        assert not any(
            isinstance(node, ast.ImportFrom)
            and node.module == guard["forbidden_import_module"]
            and any(
                alias.name == guard["forbidden_import_name"]
                for alias in node.names
            )
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == guard["forbidden_call_name"]
            for node in ast.walk(tree)
        )
