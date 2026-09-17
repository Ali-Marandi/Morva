from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MUTATIONS = (
    (
        "calculator_taxable_filter",
        Path("src/morva/payroll/calculator.py"),
        'line.kind == "earning" and line.taxable',
        'line.kind == "earning"',
    ),
    (
        "calculator_pensionable_filter",
        Path("src/morva/payroll/calculator.py"),
        'line.kind == "earning" and line.pensionable',
        'line.kind == "earning"',
    ),
    (
        "models_net_sign",
        Path("src/morva/payroll/models.py"),
        "return self.gross - self.deductions",
        "return self.gross + self.deductions",
    ),
    (
        "contribution_ceiling",
        Path("src/morva/payroll/policies.py"),
        "min(gross, self.ceiling)",
        "gross",
    ),
)

SELECTED_TESTS = (
    "tests/test_calculator.py",
    "tests/test_m3_35_financial_properties.py",
)


def prepare_copy(destination: Path) -> None:
    shutil.copytree(ROOT / "src", destination / "src")
    for test in SELECTED_TESTS:
        target = destination / test
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / test, target)


def run_tests(root: Path) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(root / "src")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *SELECTED_TESTS],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="morva-m3-35-") as raw:
        root = Path(raw)
        prepare_copy(root)
        baseline = run_tests(root)
        if baseline.returncode != 0:
            print("M3.35 mutation gate baseline failed.")
            print(baseline.stdout)
            print(baseline.stderr)
            return baseline.returncode

        failures: list[str] = []
        for name, relative_path, original, mutant in MUTATIONS:
            mutant_root = root / name
            prepare_copy(mutant_root)
            target = mutant_root / relative_path
            source = target.read_text(encoding="utf-8")
            count = source.count(original)
            if count != 1:
                failures.append(f"{name}: expected one mutation site, found {count}")
                continue
            target.write_text(source.replace(original, mutant), encoding="utf-8")
            outcome = run_tests(mutant_root)
            if outcome.returncode == 0:
                failures.append(f"{name}: surviving mutant")
            else:
                print(f"M3.35 killed mutant: {name}")

        if failures:
            print("M3.35 mutation gate failed:")
            for failure in failures:
                print(f"- {failure}")
            return 1

    print("M3.35 mutation gate passed: all targeted financial mutants were killed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
