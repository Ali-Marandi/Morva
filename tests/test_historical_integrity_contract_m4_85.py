from __future__ import annotations

import ast
from pathlib import Path

INTEGRITY_LAYERS = (
    {
        "id": "m4_77_runtime",
        "path": "src/morva/runtime/historical_m4_75_verification_receipt_history_integrity_m4_77.py",
        "required_modules": (
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.historical_integrity_primitives",
        ),
        "forbidden_tokens": ("m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
        "test": {
            "path": "tests/test_historical_m4_75_verification_receipt_history_integrity_m4_77.py",
            "required_modules": (
                "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            ),
            "expected_symbols": (
                "HistoricalM475VerificationReceiptHistoryIntegrityRepository",
            ),
        },
    },
    {
        "id": "m4_78_runtime",
        "path": "src/morva/runtime/independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py",
        "required_modules": (
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.historical_integrity_primitives",
        ),
        "forbidden_tokens": ("m4_83", "m4_84", "m4_85", "m4_86"),
        "test": {
            "path": "tests/test_independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py",
            "required_modules": (
                "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
            ),
            "expected_symbols": (
                "independently_verify_historical_m4_75_verification_receipt_history_integrity",
            ),
        },
    },
    {
        "id": "m4_79_persistence",
        "path": "src/morva/persistence/independent_m4_77_verification_receipts_m4_79.py",
        "required_modules": (
            "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
        ),
        "forbidden_tokens": ("m4_80", "m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
        "test": {
            "path": "tests/test_independent_m4_77_verification_receipts_m4_79.py",
            "required_modules": (
                "morva.persistence.independent_m4_77_verification_receipts_m4_79",
            ),
            "expected_symbols": (
                "IndependentM477VerificationReceiptM479Repository",
            ),
        },
    },
    {
        "id": "m4_80_runtime",
        "path": "src/morva/runtime/independent_m4_77_verification_receipt_m4_80.py",
        "required_modules": (
            "morva.persistence.independent_m4_77_verification_receipts_m4_79",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
            "morva.runtime.historical_integrity_primitives",
        ),
        "forbidden_tokens": ("m4_84", "m4_85", "m4_86"),
        "test": {
            "path": "tests/test_independent_m4_77_verification_receipt_m4_80.py",
            "required_modules": (
                "morva.runtime.independent_m4_77_verification_receipt_m4_80",
            ),
            "expected_symbols": (
                "independently_verify_m4_79_verification_receipt",
            ),
        },
    },
    {
        "id": "m4_81_persistence",
        "path": "src/morva/persistence/independent_m4_79_verification_receipts_m4_81.py",
        "required_modules": (
            "morva.persistence.independent_m4_77_verification_receipts_m4_79",
            "morva.runtime.independent_m4_77_verification_receipt_m4_80",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
        ),
        "forbidden_tokens": ("m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
        "test": {
            "path": "tests/test_independent_m4_79_verification_receipts_m4_81.py",
            "required_modules": (
                "morva.persistence.independent_m4_79_verification_receipts_m4_81",
            ),
            "expected_symbols": (
                "IndependentM479VerificationReceiptM481Repository",
            ),
        },
    },
)


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


def test_integrity_contract_is_complete_and_unique() -> None:
    assert len(INTEGRITY_LAYERS) == 5
    ids = [layer["id"] for layer in INTEGRITY_LAYERS]
    assert len(ids) == len(set(ids))
    paths = [layer["path"] for layer in INTEGRITY_LAYERS]
    assert len(paths) == len(set(paths))


def test_integrity_contract_files_and_tests_exist() -> None:
    for layer in INTEGRITY_LAYERS:
        assert Path(layer["path"]).is_file(), layer["id"]
        assert Path(layer["test"]["path"]).is_file(), layer["id"]


def test_integrity_runtime_dependency_edges_are_explicit() -> None:
    for layer in INTEGRITY_LAYERS:
        modules = _imported_modules(_tree(Path(layer["path"])))
        for required in layer["required_modules"]:
            assert required in modules, f"{layer['id']} must depend on {required}"


def test_integrity_runtime_layers_have_no_forward_dependencies() -> None:
    for layer in INTEGRITY_LAYERS:
        source = _source(Path(layer["path"])).lower()
        for token in layer["forbidden_tokens"]:
            assert token not in source, (
                f"{layer['id']} must not depend on future {token} code"
            )


def test_integrity_runtime_tests_cover_expected_layer() -> None:
    for layer in INTEGRITY_LAYERS:
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


def test_integrity_contract_keeps_shared_primitive_guard() -> None:
    guarded_paths = {
        "src/morva/runtime/historical_m4_75_verification_receipt_history_integrity_m4_77.py",
        "src/morva/runtime/independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py",
        "src/morva/runtime/independent_m4_77_verification_receipt_m4_80.py",
    }
    for path_value in guarded_paths:
        tree = _tree(Path(path_value))
        assert any(
            isinstance(node, ast.ImportFrom)
            and node.module == "morva.runtime.historical_integrity_primitives"
            and any(alias.name == "canonical_sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.ImportFrom)
            and node.module == "hashlib"
            and any(alias.name == "sha256" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sha256"
            for node in ast.walk(tree)
        )
