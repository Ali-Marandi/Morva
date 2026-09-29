from __future__ import annotations

import ast
from pathlib import PurePosixPath

RUNTIME_PATHS = (
    PurePosixPath("src/morva/runtime/historical_m4_75_verification_receipt_history_integrity_m4_77.py"),
    PurePosixPath("src/morva/runtime/independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py"),
    PurePosixPath("src/morva/runtime/independent_m4_77_verification_receipt_m4_80.py"),
)


def _source(path: PurePosixPath) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: PurePosixPath) -> ast.Module:
    return ast.parse(_source(path), filename=str(path))


def test_historical_integrity_runtimes_use_shared_sha256_primitive() -> None:
    for path in RUNTIME_PATHS:
        tree = _tree(path)
        shared_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "morva.runtime.historical_integrity_primitives"
            and any(alias.name == "canonical_sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert shared_import, f"{path} must import canonical_sha256 from the shared primitive"


def test_historical_integrity_runtimes_have_no_local_sha256_implementation() -> None:
    for path in RUNTIME_PATHS:
        tree = _tree(path)
        forbidden_hash_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "hashlib"
            and any(alias.name == "sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        forbidden_sha256_call = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sha256"
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
        assert not forbidden_hash_import, f"{path} reintroduces a local hashlib.sha256 import"
        assert not forbidden_sha256_call, f"{path} reintroduces a local sha256() call"
        assert not forbidden_json_dump, f"{path} reintroduces local json.dumps fingerprint serialization"
