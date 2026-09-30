from __future__ import annotations

import ast
import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path), filename=str(path))


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _layers() -> list[dict[str, object]]:
    return _manifest()["layers"]


def test_manifest_schema_is_valid_and_unique() -> None:
    manifest = _manifest()
    assert manifest["schema_version"] == 1
    assert manifest["contract_id"] == "morva.historical_integrity.m4_77_m4_81"
    layers = _layers()
    assert len(layers) == 5
    ids = [layer["id"] for layer in layers]
    assert len(ids) == len(set(ids))
    for layer in layers:
        assert isinstance(layer["path"], str)
        assert isinstance(layer["required_modules"], list)
        assert isinstance(layer["forbidden_tokens"], list)
        test = layer["test"]
        assert isinstance(test["path"], str)
        assert isinstance(test["required_modules"], list)
        assert isinstance(test["expected_symbols"], list)


def test_integrity_contract_files_and_tests_exist_from_manifest() -> None:
    for layer in _layers():
        assert Path(layer["path"]).is_file(), layer["id"]
        assert Path(layer["test"]["path"]).is_file(), layer["id"]


def test_integrity_runtime_dependency_edges_are_explicit_from_manifest() -> None:
    for layer in _layers():
        modules = _imported_modules(_tree(Path(layer["path"])))
        for required in layer["required_modules"]:
            assert required in modules, f"{layer['id']} must depend on {required}"


def test_integrity_runtime_layers_have_no_forward_dependencies_from_manifest() -> None:
    for layer in _layers():
        source = _source(Path(layer["path"])).lower()
        for token in layer["forbidden_tokens"]:
            assert token not in source, (
                f"{layer['id']} must not depend on future {token} code"
            )


def test_integrity_runtime_tests_cover_expected_layer_from_manifest() -> None:
    for layer in _layers():
        test = layer["test"]
        path = Path(test["path"])
        tree = _tree(path)
        modules = _imported_modules(tree)
        for required in test["required_modules"]:
            assert required in modules, f"{layer['id']} test must import {required}"
        source = _source(path)
        source_names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        for symbol in test["expected_symbols"]:
            assert symbol in source_names or symbol in source


def test_integrity_contract_guard_is_manifest_driven() -> None:
    guard = _manifest()["guards"]["shared_sha256_primitive"]
    guarded_paths = {item for item in guard["runtime_paths"]}
    manifest_paths = {
        layer["path"]
        for layer in _layers()
        if layer["id"] in {"m4_77_runtime", "m4_78_runtime", "m4_80_runtime"}
    }
    assert guarded_paths == manifest_paths

    for path_value in guard["runtime_paths"]:
        tree = _tree(Path(path_value))
        assert any(
            isinstance(node, ast.ImportFrom)
            and node.module == guard["required_module"]
            and any(alias.name == "canonical_sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.ImportFrom)
            and node.module == guard["forbidden_import_module"]
            and any(alias.name == guard["forbidden_import_name"] for alias in node.names)
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == guard["forbidden_call_name"]
            for node in ast.walk(tree)
        )
