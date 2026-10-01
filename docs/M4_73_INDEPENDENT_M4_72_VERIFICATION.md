# M4.73 — Independent M4.72 Verification

## Purpose

M4.73 independently reconstructs and verifies each persisted M4.72 verification-receipt history integrity snapshot without treating the M4.72 repository or builder as the source of truth.

## Verification boundary

For a requested M4.72 snapshot, the verifier:

- validates the persisted snapshot structure and fingerprint;
- applies the snapshot creation timestamp as the point-in-time boundary;
- re-reads and structurally validates the complete M4.71 receipt history before that boundary;
- reconstructs the canonical history fingerprint, record count and valid-record count independently;
- compares the reconstructed identity with the persisted M4.72 identity;
- emits deterministic blocker codes and a verification fingerprint.

## Blockers

The verification surface reports deterministic mismatch codes for:

- `M472_HISTORY_FINGERPRINT_MISMATCH`
- `M472_RECORD_COUNT_MISMATCH`
- `M472_VALID_COUNT_MISMATCH`
- `M472_INTEGRITY_FINGERPRINT_MISMATCH`

A structurally invalid persisted snapshot or source record fails closed rather than being converted into a valid result.

## API

The authenticated read endpoint is exposed at:

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-68-verification-history-integrity-snapshots/{snapshot_id}/verify-independent-m4-72`

The endpoint remains read-only and does not create provider, payment, credential or production-authorization side effects.

## Validation

The dedicated CI gate runs Ruff, the M4.72 and M4.73 focused pytest suite, Alembic migration validation against SQLite, and an explicit verification-only boundary assertion.
