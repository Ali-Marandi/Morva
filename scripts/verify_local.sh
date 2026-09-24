#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

declare -a FAILED=()

run_check() {
  local name="$1"
  shift
  printf '\n==> %s\n' "$name"
  if "$@"; then
    printf 'PASS  %s\n' "$name"
  else
    printf 'FAIL  %s\n' "$name"
    FAILED+=("$name")
  fi
}

run_check "Install Python dev dependencies"   python -m pip install -e '.[dev]'

run_check "Ruff"   ruff check .

run_check "Pytest"   pytest -q

run_check "Install pip-audit"   python -m pip install pip-audit

run_check "pip-audit"   pip-audit

run_check "Web production build"   bash -lc 'cd web && npm ci && npm run build'

printf '\n========================================\n'
if ((${#FAILED[@]} == 0)); then
  printf 'PASS: all local Morva verification checks passed.\n'
  exit 0
fi

printf 'FAIL: %d verification check(s) failed:\n' "${#FAILED[@]}"
printf ' - %s\n' "${FAILED[@]}"
exit 1
