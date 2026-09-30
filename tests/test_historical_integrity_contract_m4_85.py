from __future__ import annotations

import ast
from pathlib import Path

CONTRACTS = {
    "m4_77_runtime": {
        "path": Path("src/morva/runtime/historical_m4_75_verification_receipt_history_integrity_m4_77.py"),
        "required_modules": {
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.historical_integrity_primitives",
        },
        "forbidden_tokens": ("m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
    },
    "m4_78_runtime": {
        "path": Path("src/morva/runtime/independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py"),
        "required_modules": {
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.historical_integrity_primitives",
        },
        "forbidden_tokens": ("m4_83", "m4_84", "m4_85", "m4_86"),
    },
    "m4_79_persistence": {
        "path": Path("src/morva/persistence/independent_m4_77_verification_receipts_m4_79.py"),
        "required_modules": {
            "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
        },
        "forbidden_tokens": ("m4_80", "m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
    },
    "m4_80_runtime": {
        "path": Path("src/morva/runtime/independent_m4_77_verification_receipt_m4_80.py"),
        "required_modules": {
            "morva.persistence.independent_m4_77_verification_receipts_m4_79",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
            "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
            "morva.runtime.historical_integrity_primitives",
        },
        "forbidden_tokens": ("m4_84", "m4_85", "m4_86"),
    },
    "m4_81_persistence": {
        "path": Path("src/morva/persistence/independent_m4_79_verification_receipts_m4_81.py"),
        "required_modules": {
            "morva.persistence.independent_m4_77_verification_receipts_m4_79",
            "morva.runtime.independent_m4_77_verification_receipt_m4_80",
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
            "morva.persistence.historical_m4_72_verification_receipt_m4_75",
        },
        "forbidden_tokens": ("m4_82", "m4_83", "m4_84", "m4_85", "m4_86"),
    },
}

TEST_CONTRACTS = {
    "m4_77_tests": {
        "path": "tests/test_historical_m4_75_verification_receipt_history_integrity_m4_77.py",
        "required_modules": {
            "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77",
        },
    },
    "m4_78_tests": {
        "path": "tests/test_independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py",
        "required_modules": {
            "morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78",
        },
    },
    "m4_79_tests": {
        "path": "tests/test_independent_m4_77_verification_receipts_m4_79.py",
        "required_modules": {
            "morva.persistence.independent_m4_77_verification_receipts_m4_79",
        },
    },
    "m4_80_tests": {
        "path": "tests/test_independent_m4_77_verification_receipt_m4_80.py",
        "required_modules": {
            "morva.runtime.independent_m4_77_verification_receipt_m4_80",
        },
    },
    "m4_81_tests": {
        "path": "tests/test_independent_m4_79_verification_receipts_m4_81.py",
        "required_modules": {
            "morva.persistence.independent_m4_79_verification_receipts_m4_81",
        },
    },
}


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


def test_integrity_contract_files_exist() -> None:
    for contract in CONTRACTS.values():
        assert contract["path"].is_file()
    for contract in TEST_CONTRACTS.values():
        assert Path(contract["path"]).is_file()


def test_integrity_runtime_dependency_edges_are_explicit() -> None:
    for name, contract in CONTRACTS.items():
        modules = _imported_modules(_tree(contract["path"]))
        for required in contract["required_modules"]:
            assert required in modules, f"{name} must depend on {required}"


def test_integrity_runtime_layers_have_no_forward_dependencies() -> None:
    for name, contract in CONTRACTS.items():
        source = _source(contract["path"]).lower()
        for token in contract["forbidden_tokens"]:
            assert token not in source, f"{name} must not depend on future {token} code"


def test_integrity_runtime_tests_cover_their_expected_layer() -> None:
    expected_symbols = {
        "m4_77_tests": ("HistoricalM475VerificationReceiptHistoryIntegrityRepository",),
        "m4_78_tests": (
            "independently_verify_historical_m4_75_verification_receipt_history_integrity",
        ),
        "m4_79_tests": ("IndependentM477VerificationReceiptM479Repository",),
        "m4_80_tests": ("independently_verify_m4_79_verification_receipt",),
        "m4_81_tests": ("IndependentM479VerificationReceiptM481Repository",),
    }
    for key, contract in TEST_CONTRACTS.items():
        tree = _tree(Path(contract["path"]))
        source_names = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        } | {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        modules = _imported_modules(tree)
        for required in contract["required_modules"]:
            assert required in modules, f"{key} must import {required}"
        for symbol in expected_symbols[key]:
            assert symbol in source_names or symbol in _source(Path(contract["path"]))


def test_integrity_contract_has_no_local_sha256_in_target_runtimes() -> None:
    guarded = (
        CONTRACTS["m4_77_runtime"],
        CONTRACTS["m4_78_runtime"],
        CONTRACTS["m4_80_runtime"],
    )
    for contract in guarded:
        tree = _tree(contract["path"])
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
