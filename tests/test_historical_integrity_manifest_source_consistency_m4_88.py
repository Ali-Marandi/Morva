from __future__ import annotations

import ast
import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _module_name(path: str) -> str:
    return path.removesuffix(".py").removeprefix("src/").replace("/", ".")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_manifest_required_modules_are_present_in_sources() -> None:
    for layer in _manifest()["layers"]:
        source = Path(layer["path"])
        imports = _imports(source)
        missing = set(layer["required_modules"]) - imports
        assert not missing, f"{layer['id']} missing manifest imports: {sorted(missing)}"


def test_manifest_does_not_hide_guarded_layer_imports() -> None:
    layers = _manifest()["layers"]
    guarded = {_module_name(layer["path"]): layer["id"] for layer in layers}
    for layer in layers:
        source = Path(layer["path"])
        imports = _imports(source)
        undeclared = sorted(
            guarded[module]
            for module in imports
            if module in guarded and module not in set(layer["required_modules"])
        )
        assert not undeclared, f"{layer['id']} has undeclared guarded dependencies: {undeclared}"


def test_manifest_source_paths_and_test_paths_exist() -> None:
    for layer in _manifest()["layers"]:
        assert Path(layer["path"]).is_file()
        assert Path(layer["test"]["path"]).is_file()


def test_manifest_test_modules_are_imported_by_declared_tests() -> None:
    for layer in _manifest()["layers"]:
        test = layer["test"]
        imports = _imports(Path(test["path"]))
        missing = set(test["required_modules"]) - imports
        assert not missing, f"{layer['id']} test missing manifest imports: {sorted(missing)}"
