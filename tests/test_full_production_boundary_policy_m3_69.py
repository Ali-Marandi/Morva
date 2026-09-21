from pathlib import Path

import pytest

from morva.runtime.production_boundary_policy import scan_repository
from morva.runtime.production_boundary_policy_v2 import (
    M3_54_TO_M3_68_WORKFLOWS,
    ProductionBoundaryPolicyError,
    scan_full_production_boundary,
)


def _write(root: Path, relative: str, content: str = "permissions:\n  contents: read\n"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_complete_m354_m368_coverage(tmp_path: Path):
    for relative in M3_54_TO_M3_68_WORKFLOWS:
        _write(tmp_path, relative)
    receipt = scan_full_production_boundary(
        root=tmp_path,
        repository="Ali-Marandi/Morva",
    )
    assert len(receipt.scanned_paths) == 15
    assert receipt.passed


def test_missing_workflow_is_rejected(tmp_path: Path):
    for relative in M3_54_TO_M3_68_WORKFLOWS[:-1]:
        _write(tmp_path, relative)
    with pytest.raises(ProductionBoundaryPolicyError, match="coverage|missing"):
        scan_full_production_boundary(
            root=tmp_path,
            repository="Ali-Marandi/Morva",
        )


def test_mutation_in_latest_workflow_is_detected(tmp_path: Path):
    for relative in M3_54_TO_M3_68_WORKFLOWS:
        _write(tmp_path, relative)
    _write(
        tmp_path,
        M3_54_TO_M3_68_WORKFLOWS[-1],
        "steps:\n  - run: gh release upload v1.0.0 artifact.tgz\n",
    )
    receipt = scan_repository(
        root=tmp_path,
        repository="Ali-Marandi/Morva",
        relative_paths=M3_54_TO_M3_68_WORKFLOWS,
    )
    assert not receipt.passed
    assert any(f.rule == "workflow-mutation" for f in receipt.findings)
