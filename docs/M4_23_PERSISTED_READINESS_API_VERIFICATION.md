# M4.23 — Independent Persisted Readiness API Verification

## Purpose

M4.23 adds an independent, read-only verification boundary for M4.22 persisted integration-execution readiness receipts.

The verifier does not call the M4.20 assessment builder and does not execute external providers. It reconstructs the persisted assessment fingerprint and M4.21 verification fingerprint directly from stored fields and fails closed on drift.

## Verified invariants

- canonical repository is exactly `Ali-Marandi/Morva`;
- candidate SHA is an exact 40-character Git SHA-1 and optional API filters must match the persisted receipt;
- target environment is limited to `staging` or `pilot`;
- assessment version is supported;
- evidence-readiness, binding and binding-verification fingerprints are valid SHA-256 values;
- state is exactly `ready` or `blocked`;
- `ready` has no blockers and `blocked` has at least one blocker;
- assessment check time is not later than the stored verification time;
- the independently reconstructed M4.20 assessment fingerprint matches the persisted fingerprint;
- the independently reconstructed M4.21 verification fingerprint matches the persisted fingerprint.

Persistence creation time is reported but is not used as a prerequisite for the original M4.21 verification timestamp, because the receipt may legitimately be persisted after it was independently verified.

## API

`GET /api/v1/integration-execution/readiness/verify`

Authorization remains `evidence.read` at ministry scope. The endpoint is read-only and accepts only optional candidate-SHA and staging/pilot filters.

A missing receipt returns `404`. Any persistence or independent-verification inconsistency returns `409`.

## Safety boundary

This tranche does not:

- activate a provider;
- consume external integration credentials;
- call external endpoints;
- authorize real payroll/payment release;
- mutate production data.

M4.23 therefore strengthens evidence integrity and observability without changing Morva's fail-closed production posture.
