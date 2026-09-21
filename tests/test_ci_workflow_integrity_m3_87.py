from __future__ import annotations

from pathlib import Path

import pytest

from morva.runtime.ci_workflow_integrity import (
    CIWorkflowIntegrityError,
    scan_workflows,
    write_receipt,
)


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_clean_workflow_passes(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/clean.yml",
        """name: Clean
on:
  push:
    branches: [main]
    paths:
      - "src/example.py"
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert receipt.passed
    assert receipt.fingerprint


def test_missing_jobs_is_rejected(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/broken.yml",
        """name: Broken
on:
  pull_request:
    branches: [main]
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert not receipt.passed
    assert any(item.rule == "workflow-jobs" for item in receipt.findings)


def test_unscoped_main_push_is_rejected(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/broad.yml",
        """name: Broad
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert any(item.rule == "push-path-scope" for item in receipt.findings)


def test_allowed_core_push_is_not_rejected(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/ci.yml",
        """name: CI
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert receipt.passed


@pytest.mark.parametrize(
    "command",
    [
        "gh release create",
        "gh release upload",
        "git push",
        "git tag",
        "kubectl apply",
        "helm upgrade",
        "terraform apply",
    ],
)
def test_mutation_commands_are_rejected(tmp_path: Path, command: str):
    _write(
        tmp_path,
        ".github/workflows/mutate.yml",
        f"""name: Mutate
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: {command} demo
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert any(item.rule == "workflow-mutation" for item in receipt.findings)


@pytest.mark.parametrize("command", ["eval", "bash -c", "sh -c"])
def test_dynamic_shell_execution_is_rejected(tmp_path: Path, command: str):
    _write(
        tmp_path,
        ".github/workflows/dynamic.yml",
        f"""name: Dynamic
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: {command} "echo safe"
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert any(item.rule == "workflow-dynamic-execution" for item in receipt.findings)



@pytest.mark.parametrize("command", ["bash    -c", "sh\t-c", "eval\t"])
def test_dynamic_shell_execution_with_whitespace_is_rejected(tmp_path: Path, command: str):
    _write(
        tmp_path,
        ".github/workflows/dynamic-whitespace.yml",
        f"""name: Dynamic Whitespace
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: {command} "echo unsafe"
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert any(
        item.rule == "workflow-dynamic-execution" for item in receipt.findings
    )


def test_quoted_dynamic_execution_text_is_not_a_command(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/quoted-dynamic.yml",
        """name: Quoted Dynamic
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: grep -R -- "eval" .github/workflows
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert not any(item.rule == "workflow-dynamic-execution" for item in receipt.findings)




def test_inline_comment_is_not_dynamic_execution(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/commented.yml",
        """name: Commented
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok # eval
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert not any(item.rule == "workflow-dynamic-execution" for item in receipt.findings)


def test_receipt_is_write_once(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/clean.yml",
        """name: Clean
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    output = tmp_path / "receipt.json"
    write_receipt(receipt, output)
    with pytest.raises(CIWorkflowIntegrityError, match="write-once"):
        write_receipt(receipt, output)

def test_quoted_mutation_text_is_not_a_command(tmp_path: Path):
    _write(
        tmp_path,
        ".github/workflows/guard.yml",
        """name: Guard
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: grep -R -- 'gh release create' .github/workflows
""",
    )
    receipt = scan_workflows(tmp_path, "Ali-Marandi/Morva")
    assert receipt.passed
