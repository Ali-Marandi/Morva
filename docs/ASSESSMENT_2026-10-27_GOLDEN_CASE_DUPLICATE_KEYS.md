# Engineering Assessment — Golden Case Duplicate JSON Keys
**Date:** 2026-10-27  
**Repository:** `Ali-Marandi/Morva`  
**Branch:** `fix/golden-case-duplicate-json-keys-20261027`  
**Base candidate:** PR #211 head `0de3f1b3b9a944ca659d9ce7ba696e8cd4d44043`  
**Baseline evidence:** PR #211 has 15 completed successful workflow runs and 49 successful checks. It remains open and unmerged; independent review is still required.

## Selected scope and root cause

Python's default JSON object decoder accepts repeated object keys by keeping the last value. The Golden Case loader previously used `json.loads()` with default behavior, so duplicate keys could conceal conflicting metadata or calculation inputs before repository validation saw the parsed object.

This follow-up is limited to Gate 1's Golden Case input boundary. It does not change payroll arithmetic, legal rules, statutory values, expected legal outputs or production activation.

## Implementation

- Add a strict `object_pairs_hook` that rejects a repeated key in any JSON object.
- Apply it to the whole `cases.json` document, covering both top-level case metadata and nested input/expected-output objects.
- Add regression cases for duplicate `case_id`, nested `input_values` and nested `expected_output` keys.
- Update Changelog, Roadmap, Implementation Matrix, and Production Readiness evidence notes.

## CI finding and corrective action

The first CI attempt failed at Ruff/compile time because the new multiline `json.loads()` call was accidentally committed with literal `\\n` text instead of actual source line breaks. The same syntax error caused downstream test collection to fail. The corrective code commit `563b375a8b05a6f817a9510696a2a0ba75bbd596` removed the syntax error without weakening tests. The combined code/evidence-binding HEAD `d7b4e500c389ebc90509b941d4f6786b5bafa0ac` passed all 14 associated workflow runs and 48 checks, including full Morva CI. The documentation-only follow-up HEAD `121b703546db2743d9ff69744fd2e3b2d47951f5` also passed all 14 workflows and 48 checks; links are recorded in the PR description.

## Acceptance criteria

- Focused Golden Case regression tests and full Morva CI passed on the code/test HEAD; the subsequent documentation-only HEAD also passed 14 workflows and 48 checks.
- Existing valid Golden Case repository hash remains unchanged.
- The candidate is independently reviewed and its ancestry remains stacked on PR #211; parent PRs are still open and unmerged.
- Gate 1 remains blocked unless authoritative primary-source legal evidence, formal legal/finance approval and a certified golden corpus are supplied.

## Boundary

No migration is required. No payment/provider operation, production activation, secret change or statutory-rule change is performed. No production-readiness status is promoted by this code change.
