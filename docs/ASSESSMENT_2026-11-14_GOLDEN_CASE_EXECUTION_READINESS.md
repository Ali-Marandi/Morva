# Engineering Assessment — Golden Case Execution Readiness

**Date:** 2026-11-14  
**Repository:** `Ali-Marandi/Morva`  
**Gate:** 1 — Legal Rules and Calculation Correctness  
**Main baseline inspected:** `528e946f743e4718225543e7a7883809bcd698ef`  
**Gate 1 candidate chain:** PR #210 (`0b9f26f3abcc7e1b4de2d6c331eb8a2b45681ad1`) → PR #211 (`0de3f1b3b9a944ca659d9ce7ba696e8cd4d44043`) → this PR #213 (`8e64f485ce5d33754cddc26bc9c69565f4dfe539`)

## Decision

**Execution Runner implementation is not yet safe to start. Gate 1 remains BLOCKED.**

The repository has made material progress on loader integrity, per-case validation, evidence binding, strict JSON parsing and placeholder-hash rejection. Those controls do not yet establish that every approved Golden Case is executed through the production RuleEngine and that the stored `expected_output` object is bound to the stored output fingerprint.

This assessment records the exact contract gaps so the next code tranche does not invent a legal schema, calendar conversion rule or component-to-rule mapping.

## Verified source findings

1. **The verifier is defined but not wired into the Golden Case execution path.**  
   `src/morva/rules/regression_cases.py` defines `verify_expected_result(case, actual_result)`. A repository code search on the inspected main baseline returns the function definition, but no production/test/workflow call site. The current focused workflow runs Ruff plus `tests/test_regression_cases.py` and `tests/test_calculation_matrix.py`; it does not invoke a per-case RuleEngine runner.  
   Sources: [regression_cases.py](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/src/morva/rules/regression_cases.py), [code search](https://github.com/Ali-Marandi/Morva/search?q=verify_expected_result&type=code), [Golden Case workflow](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/.github/workflows/golden-case-repository-gate.yml).

2. **The expected-output object is not cryptographically bound to its fingerprint by the current contract.**  
   The loader accepts `expected_output` as an object or null. Repository validation checks that an output exists and that `expected_output_fingerprint` has the expected SHA-256 shape. The verifier fingerprints the actual `RuleResult` and compares it with the stored fingerprint; it does not consume or canonicalize `case.expected_output`. Consequently, the contract does not currently demonstrate that the JSON object and fingerprint in a case describe the same expected result.  
   Sources: [RegressionCase loader and verifier](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/src/morva/rules/regression_cases.py), [canonical RuleResult fingerprint](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/src/morva/rules/regression.py).

3. **The execution adapter contract is incomplete.**  
   `RegressionCase.effective_date` is stored as `str`; `RuleContext.effective_date` is a Python `date`. The RuleEngine resolves a `RuleDefinition` by rule code and effective date, while the case carries a `component_code`. The inspected Runner path does not define an authoritative mapping from Rule Pack + component + population scope to exactly one RuleDefinition.  
   Sources: [RegressionCase](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/src/morva/rules/regression_cases.py), [RuleEngine contract](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/src/morva/rules/engine.py).

4. **Calendar conversion cannot be guessed.**  
   The corpus uses dates such as `1405-01-01`, while RuleContext requires a `date`. The existing import contract explicitly says Persian/Jalali dates must be preserved as source values until an authoritative calendar-conversion step is applied. A direct ISO/Gregorian parse would risk changing the effective date.  
   Source: [1405-05 import contract](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/docs/data-import/1405-05-import-contract.md).

5. **The current 1405.1 corpus is not executable certified evidence.**  
   Its five TAX, PENSION, INSURANCE, LOAN and COURT_ORDER entries remain `review_required`, have empty inputs, null expected outputs/fingerprints, and all-zero legal-source hashes.  
   Source: [1405.1 cases.json](https://github.com/Ali-Marandi/Morva/blob/528e946f743e4718225543e7a7883809bcd698ef/docs/legal/golden-cases/1405.1/cases.json).

## Required contract before implementation

The following must be agreed and encoded before creating an execution adapter:

- **Canonical expected-result schema:** define the exact allowed fields, types and normalization for an expected `RuleResult`; either derive the expected fingerprint from that canonical object or prove the stored object and fingerprint are identical representations of one result.
- **Effective-date semantics:** specify the source calendar, conversion authority/library, timezone policy (if applicable), effective-date inclusivity and preservation of the original source string. No implicit Jalali-to-Gregorian conversion.
- **Rule resolution:** define a deterministic, fail-closed mapping from `rule_pack_version`, `component_code`, `population_scope` and effective date to exactly one approved `RuleDefinition`. Missing or ambiguous resolution must block the case.
- **Input contract:** identify the authoritative mapping of case input keys to RuleContext values, including Decimal-only semantics and units. Do not infer fields from the current placeholder corpus.
- **Execution evidence:** bind each result to the case ID, Rule Pack version, resolved RuleDefinition/version, source hash and canonical suite hash.

## Runner acceptance criteria

1. Execute every case with status `approved` or `published`; never silently skip a malformed or unresolvable approved case.
2. Resolve exactly one applicable RuleDefinition for every case; reject missing or ambiguous mappings.
3. Construct RuleContext only through the approved date and input adapters.
4. Execute the real `RuleEngine.calculate` path; do not substitute fixture arithmetic or a second implementation of the formula.
5. Compare the complete canonical result payload with `expected_output` and verify its fingerprint against `expected_output_fingerprint`.
6. Fail on output mismatch, fingerprint mismatch, stale suite binding, invalid source evidence, RuleEngine exception or nondeterministic rerun.
7. Fail the execution gate when there are zero approved/published cases; a zero-case run must not be reported as a successful execution.
8. Emit counts for discovered, approved, executed, passed, failed and blocked cases; require `executed == approved` and `skipped == 0`.
9. Add positive synthetic adapter tests clearly labelled as engineering fixtures, plus negative tests for missing/ambiguous rule resolution, invalid calendar conversion, output-object/fingerprint disagreement, tampering, duplicate IDs and engine errors. Synthetic tests do not certify the legal corpus.
10. Run the focused Golden Case gate and the full required CI on the exact resulting SHA before describing the software tranche as validated.

## Explicitly out of scope

- No legal inputs, statutory amounts, rates, coefficients, thresholds or expected payroll outputs are to be invented.
- No production Rule Pack is to be activated.
- No payroll/payment execution, provider call, credential, secret, database migration or production configuration is changed.
- No Production Readiness Gate is cleared by this engineering assessment.

**Conclusion:** the safe next tranche is a contract-first, test-backed adapter and runner after the schema, date semantics and rule mapping are authoritative. Until then, preserve Gate 1 and all six Production Readiness Gates as **BLOCKED / fail-closed**.
