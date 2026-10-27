# Engineering Assessment — Gate 1 Golden Evidence Suite Hash Binding

**Date:** 2026-10-27  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `fix/golden-case-duplicate-json-keys-20261027`  
**Parent chain:** PR #210 → PR #211 → PR #213  
**Validation status:** Exact-HEAD GitHub Actions pending; local test execution was not performed in this environment.

## Finding

`validate_repository_against_evidence()` checked each golden case against the registered component evidence for source hash, article, clause, population scope and approval state, but did not compare `RuleEvidenceRecord.regression_suite_hash` with the current canonical hash returned by `regression_suite_hash(rule_pack_version)`.

The calculation-matrix gate compared the stored evidence hash with the matrix entry hash. Those two persisted values can agree with one another while both are stale relative to the current golden corpus. That leaves the evidence-to-corpus binding incomplete.

## Change

- Compute the current canonical golden-suite hash once during evidence validation.
- Emit an explicit blocker for every case in a component when its registered rule evidence references a different suite hash.
- Add a regression test proving stale evidence is rejected and a matching suite hash does not produce a false blocker.
- Keep the strict duplicate-key JSON parsing and prior schema/path guards intact.
- Synchronize the changelog, roadmap, implementation matrix and production-readiness checklist.

## Verification

- New focused regression test: added; execution awaits exact-HEAD GitHub Actions.
- Ruff, full Python tests, migrations, security checks and web build: not run locally in this environment; exact-HEAD CI evidence is pending.
- Earlier successful CI for PR #213 does not validate this new code change and is not reused as evidence for the new HEAD.
- No database schema or migration change is required.

## Safety boundary

This is evidence-binding validation only. It does not invent legal sources, statutory rates, coefficients or expected payroll outputs. It does not change payroll arithmetic, credentials, official endpoints, payment execution or production authorization. Gate 1 and all six Production Readiness Gates remain **BLOCKED** until authoritative legal evidence, formal legal/finance/security/operations approvals and a certified golden corpus are retained.
