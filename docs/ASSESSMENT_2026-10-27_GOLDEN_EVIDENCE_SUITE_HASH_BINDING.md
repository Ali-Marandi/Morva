# Engineering Assessment — Gate 1 Golden Evidence Suite Hash Binding

**Date:** 2026-10-27  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `fix/golden-case-duplicate-json-keys-20261027`  
**Parent chain:** PR #210 → PR #211 → PR #213  
**Validation status:** Code/test HEAD `d7b4e500c389ebc90509b941d4f6786b5bafa0ac` and subsequent documentation-only HEAD `121b703546db2743d9ff69744fd2e3b2d47951f5` each passed all 14 associated GitHub Actions workflow runs and all 48 check runs. The full Morva CI completed successfully, including Python 3.12/3.13 tests; focused Golden Case, Web Type Check, Backend Security Regression and M3.13/M3.15/M3.16/M3.22/M3.23/M3.24 gates also passed. Local test execution was not performed in this environment.

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

- The focused stale/matching suite-hash regression test passed in the exact-code-HEAD Golden Case Repository Gate: [run 40460021049](https://github.com/Ali-Marandi/Morva/actions/runs/40460021049).
- Full CI on the same code HEAD completed successfully: [Morva CI run 40460020931](https://github.com/Ali-Marandi/Morva/actions/runs/40460020931), including Python 3.12/3.13, repository-wide lint, migration upgrade and web build.
- The exact code HEAD has 14 successful workflow runs and 48 successful checks. Local pytest/Ruff were not run in this execution environment; validation claims are based on GitHub Actions.
- No database schema or migration change is required.

## Exact-HEAD CI reconciliation (2026-10-28)

The previously described documentation-only HEAD `9763abc3df0d84126aa79b2c4cf0d5dab2f7c900` has now completed its GitHub validation. The exact commit's check-runs API reports **48/48 successful checks**; all 10 associated PR-triggered workflow runs returned by the workflow-run query completed successfully.

Key exact-HEAD evidence:
- [Morva CI](https://github.com/Ali-Marandi/Morva/actions/runs/40583928308) succeeded, including full pytest on Python 3.12 and 3.13, repository-wide Ruff, `alembic upgrade head`, `pip-audit`, release hygiene and the web production build.
- [Golden Case Repository Gate](https://github.com/Ali-Marandi/Morva/actions/runs/40583928499) succeeded.
- [Morva Web Type Check](https://github.com/Ali-Marandi/Morva/actions/runs/40583928498) and [Backend Security Regression](https://github.com/Ali-Marandi/Morva/actions/runs/40583928486) succeeded.
- The M3.13, M3.15, M3.16, M3.22, M3.23 and M3.24 associated gates also completed successfully.

This addendum is documentation-only and does not alter runtime code. GitHub Actions must validate the new documentation commit independently; the evidence above applies to the prior exact HEAD only. Local pytest/Ruff were not run in this environment.

## Safety boundary

This is evidence-binding validation only. It does not invent legal sources, statutory rates, coefficients or expected payroll outputs. It does not change payroll arithmetic, credentials, official endpoints, payment execution or production authorization. Gate 1 and all six Production Readiness Gates remain **BLOCKED** until authoritative legal evidence, formal legal/finance/security/operations approvals and a certified golden corpus are retained.


## Exact-HEAD CI reconciliation (2026-10-29)

The current code/evidence-binding HEAD `9b9005fab64846073d514f19a2eae0ea0af81107` has now completed validation. The GitHub check-runs API returned **48/48 successful checks** for this exact SHA. Both the [PR-triggered Morva CI run 40643415123](https://github.com/Ali-Marandi/Morva/actions/runs/40643415123) and [push-triggered Morva CI run 40643408909](https://github.com/Ali-Marandi/Morva/actions/runs/40643408909) completed successfully. The full test jobs for Python 3.12 and 3.13, Web Build, Golden Case Repository Gate, Web Type Check, and Backend Security Regression are successful.

This evidence applies to `9b9005fab64846073d514f19a2eae0ea0af81107` only. The present addendum changes documentation only; GitHub Actions must validate the new documentation HEAD independently. Local pytest/Ruff were not run in this environment.
