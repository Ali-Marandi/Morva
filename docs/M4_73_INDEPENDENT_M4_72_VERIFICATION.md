# M4.73 — Independent M4.72 Verification

## Purpose

M4.73 adds an independent verification path for the M4.72 point-in-time verification-receipt history-integrity snapshots. It reconstructs the expected M4.72 state directly from the persisted M4.71 verification receipts rather than calling the M4.72 snapshot builder.

## Verification model

For a selected M4.72 snapshot, M4.73:

1. Uses only M4.71 receipt records created before the snapshot timestamp.
2. Canonically orders those records by UTC `created_at` and UUID.
3. Re-validates every source receipt structurally.
4. Recomputes the receipt-history fingerprint, record count, valid count, and integrity fingerprint.
5. Compares those reconstructed values with the persisted M4.72 snapshot.
6. Emits deterministic mismatch blockers and a separate verification fingerprint.

## Deterministic blockers

- `M472_HISTORY_FINGERPRINT_MISMATCH`
- `M472_RECORD_COUNT_MISMATCH`
- `M472_VALID_COUNT_MISMATCH`
- `M472_INTEGRITY_FINGERPRINT_MISMATCH`

Malformed persisted snapshots and malformed M4.71 source receipts fail closed as verification errors.

## API

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-68-verification-history-integrity-snapshots/{snapshot_id}/verify-independent-m4-72`

The endpoint is read-only and uses the existing `evidence.read` authorization boundary.

## Safety boundary

M4.73 is verification-only metadata logic. It does not execute providers, consume credentials, mutate payments, grant production authorization, or bypass existing authorization controls.

## Validation

The dedicated workflow runs Ruff, the focused M4.72/M4.73 regression suites, and `alembic upgrade head` against SQLite.
