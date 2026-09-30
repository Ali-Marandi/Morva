# M4.75 — Independent M4.74 Verification

## Purpose

M4.75 independently reconstructs the M4.73 verification result represented by a persisted M4.74 receipt. It does not trust the M4.74 persistence path as the source of truth.

## Verification model

For a selected M4.74 receipt, M4.75:

1. Validates the persisted receipt structure and its binding to the exact M4.72 snapshot.
2. Validates the M4.72 snapshot structure.
3. Re-validates every point-in-time M4.71 source receipt through its persistence verifier.
4. Reconstructs the M4.73 result from the M4.71 source history.
5. Compares snapshot binding, persisted/reconstructed fingerprints and validity.
6. Emits deterministic mismatch blockers and a separate M4.75 verification fingerprint.

## Deterministic blockers

- `M474_SNAPSHOT_ID_MISMATCH`
- `M474_VERIFICATION_FINGERPRINT_MISMATCH`
- `M474_PERSISTED_FINGERPRINT_MISMATCH`
- `M474_RECONSTRUCTED_FINGERPRINT_MISMATCH`
- `M474_VALIDITY_MISMATCH`

Malformed receipts, malformed snapshots and invalid source receipts fail closed.

## API

GET:
`/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-72-verification-history-integrity-snapshots/verification-receipts/{verification_id}/verify-independent`

The endpoint is read-only and uses the existing `evidence.read` authorization boundary.

## Safety boundary

M4.75 remains verification/readiness metadata only. It does not execute providers, consume production credentials, mutate payroll or payments, or grant production authorization.

## Validation

The dedicated workflow runs Ruff, focused M4.74/M4.75 regression suites and `alembic upgrade head` against SQLite.
