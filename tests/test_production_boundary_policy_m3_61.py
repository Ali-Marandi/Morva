from __future__ import annotations

from pathlib import Path

import pytest

from morva.runtime.production_boundary_policy import (
    ProductionBoundaryPolicyError,
    scan_repository,
    write_receipt,
)


REPOSITORY = "Ali-Marandi/Morva"
WORKFLOW = ".github/workflows/test.yml"


def _write(root: Path, content: str) -> None:
    path = root / WORKFLOW
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_clean_workflow_passes(tmp_path: Path):
    _write(
        tmp_path,
        "permissions:\n  contents: read\nsteps:\n  - run: echo ok\n",
    )
    receipt = scan_repository(
        root=tmp_path,
        repository=REPOSITORY,
        relative_paths=(WORKFLOW,),
    )
    assert receipt.passed
    assert receipt.findings == ()


@pytest.mark.parametrize(
    "payload",
    (
        "steps:\n  - run: gh release create v1.0.0\n",
        "steps:\n  - run: git push origin main\n",
        "steps:\n  - run: kubectl apply -f deployment.yml\n",
        "steps:\n  - run: helm upgrade morva chart\n",
        "steps:\n  - run: terraform apply\n",
        "permissions:\n  contents: write\n",
    ),
)
def test_mutation_policy_fails_closed(tmp_path: Path, payload: str):
    _write(tmp_path, payload)
    receipt = scan_repository(
        root=tmp_path,
        repository=REPOSITORY,
        relative_paths=(WORKFLOW,),
    )
    assert not receipt.passed
    assert receipt.findings


@pytest.mark.parametrize(
    "marker",
    (
        "-----BEGIN PRIVATE KEY-----",
        "ghp_test_token",
        "github_pat_test_token",
    ),
)
def test_sensitive_markers_are_rejected(tmp_path: Path, marker: str):
    _write(tmp_path, marker)
    receipt = scan_repository(
        root=tmp_path,
        repository=REPOSITORY,
        relative_paths=(WORKFLOW,),
    )
    assert not receipt.passed
    assert receipt.findings


def test_unreadable_path_is_a_finding(tmp_path: Path):
    receipt = scan_repository(
        root=tmp_path,
        repository=REPOSITORY,
        relative_paths=(WORKFLOW,),
    )
    assert not receipt.passed
    assert receipt.findings[0].rule == "readable"


def test_receipt_is_write_once(tmp_path: Path):
    _write(
        tmp_path,
        "permissions:\n  contents: read\n",
    )
    receipt = scan_repository(
        root=tmp_path,
        repository=REPOSITORY,
        relative_paths=(WORKFLOW,),
    )
    output = tmp_path / "policy.json"
    write_receipt(receipt, output)
    with pytest.raises(ProductionBoundaryPolicyError, match="write-once"):
        write_receipt(receipt, output)
