# Engineering Assessment — Golden Case Schema Guard
**Date:** 2026-10-25  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `fix/golden-case-schema-guard-20261025`  
**Verified parent baseline:** PR #210 head `96a4e6d04f2e9e0aa7afff1b188b30b7c8782ca0`  
**Baseline validation:** 48 associated GitHub Actions workflow runs completed successfully. PR #210 remains open and unmerged pending independent review.

## Selected scope and rationale

The preceding Gate 1 tranche fixed case overwrites by component, validates all repository cases, binds every represented component to registered legal evidence, rejects duplicate IDs and rejects empty/non-string case IDs. The next directly dependent risk was that the repository loader still converted malformed metadata to strings, accepted a Rule Pack identifier as an unchecked filesystem path component, and accepted non-finite decimal values or malformed fingerprint shapes.

This tranche hardens that input boundary only. It does not invent legal inputs, expected outputs, statutory values, primary-source evidence or approvals.

## Implementation

- Restrict Rule Pack version identifiers to a bounded single path segment before accessing `cases.json`, rejecting slash/backslash traversal forms.
- Require non-empty string values for the Rule Pack version, component code, population scope, effective date and status.
- Require optional fingerprint/legal metadata fields to be strings or null.
- Convert input values to finite `Decimal` values, rejecting booleans, nulls, collections, invalid numbers, NaN and infinities.
- Require `expected_output` to be an object or null and reject non-finite numbers within the object.
- Require input, expected-output and legal-source fingerprints to be 64-character hexadecimal SHA-256 values when supplied.
- Preserve the existing canonical suite-hash regression for unchanged repository data.

## Dependency graph

```text
docs/legal/golden-cases/<version>/cases.json
                    |
                    v
              load_cases()
              |          |
              |          +--> regression_suite_hash()
              |                    |
              |                    v
              |          RuleEvidenceRecord hash binding
              v
       validate_repository()
              |
              v
 validate_repository_against_evidence()
              |
              v
       matrix_readiness()
              |
              v
 GET /calculation-matrix/{rule_pack_version}/readiness
```

The loader is the shared ingress to the repository hash and validation paths. Hardening it protects both deterministic hash construction and readiness evaluation. No new forward dependency or parallel lifecycle was introduced.

## Validation plan

- Focused tests: `tests/test_regression_cases.py` and `tests/test_calculation_matrix.py`.
- Dedicated workflow: `.github/workflows/golden-case-repository-gate.yml`, running Ruff and both focused test modules.
- Full CI remains necessary for pytest, migrations, lint, dependency audit, backend security and web build.
- No database migration, API/OpenAPI contract change or frontend change is required.
- CI for this new branch is pending; the parent PR's green result does not certify the new commit.

## Remaining blockers

The committed 1405.1 corpus still has only five cases for a subset of required components; their status remains `review_required`, input values are empty, expected outputs are null and legal hashes are placeholders. Strict loader validation cannot substitute for authoritative legal and finance evidence. Gate 1 and all other production-readiness gates remain `BLOCKED`.

## Next engineering action

Wait for evidence from the new branch's actual focused workflow and relevant full CI. Fix any real failures before considering this tranche green. Do not merge stacked PRs without independent review and do not activate rules or production execution based on CI success.
