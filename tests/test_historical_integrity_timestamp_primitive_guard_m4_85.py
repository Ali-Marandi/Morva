from __future__ import annotations

import ast
from pathlib import Path

RUNTIME_PATHS = (
    Path("src/morva/runtime/historical_m4_75_verification_receipt_history_integrity_m4_77.py"),
    Path("src/morva/runtime/independent_historical_m4_75_verification_receipt_history_integrity_m4_78.py"),
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_historical_integrity_runtimes_use_shared_utc_timestamp_primitive() -> None:
    for path in RUNTIME_PATHS:
        tree = _tree(path)
        shared_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "morva.runtime.historical_integrity_primitives"
            and any(
                alias.name == "canonical_utc_timestamp"
                for alias in node.names
            )
            for node in ast.walk(tree)
        )
        assert shared_import, f"{path} must import canonical_utc_timestamp from the shared primitive"


def test_historical_integrity_runtimes_have_no_local_timestamp_normalization() -> None:
    for path in RUNTIME_PATHS:
        tree = _tree(path)
        forbidden_timezone_import = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "datetime"
            and any(alias.name == "timezone" for alias in node.names)
            for node in ast.walk(tree)
        )
        forbidden_utc_attribute = any(
            isinstance(node, ast.Attribute)
            and node.attr == "utc"
            and isinstance(node.value, ast.Name)
            and node.value.id == "timezone"
            for node in ast.walk(tree)
        )
        forbidden_isoformat_call = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "isoformat"
            for node in ast.walk(tree)
        )
        assert not forbidden_timezone_import, (
            f"{path} reintroduces direct datetime.timezone imports "
            "for timestamp canonicalization"
        )
        assert not forbidden_utc_attribute, (
            f"{path} reintroduces direct timezone.utc timestamp normalization"
        )
        assert not forbidden_isoformat_call, (
            f"{path} reintroduces local datetime.isoformat timestamp serialization"
        )
