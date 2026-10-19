# M4.80 — Independent Verification of Persisted M4.79 Receipts

## Purpose

M4.80 independently verifies each persisted M4.79 receipt. It does not trust the M4.79 persistence repository as the reconstruction source of truth.

## Reconstruction and provenance

The verifier loads the M4.79 record, its bound M4.77 source receipt, the M4.75 point-in-time snapshot and only M4.74 source receipts created before that snapshot. It verifies the M4.77 source receipt and each selected M4.74 source receipt, then invokes the independent M4.78 reconstruction runtime.

The stored M4.79 payload is compared to the fresh M4.78 result field by field, including source receipt identity, snapshot IDs, persisted/reconstructed fingerprints, validity values, blocker tuples and the M4.78 verification fingerprint.

## Deterministic mismatch blockers

- `M479_SOURCE_RECEIPT_ID_MISMATCH`
- `M479_PERSISTED_SNAPSHOT_ID_MISMATCH`
- `M479_RECONSTRUCTED_SNAPSHOT_ID_MISMATCH`
- `M479_PERSISTED_VERIFICATION_FINGERPRINT_MISMATCH`
- `M479_RECONSTRUCTED_VERIFICATION_FINGERPRINT_MISMATCH`
- `M479_PERSISTED_VALIDITY_MISMATCH`
- `M479_RECONSTRUCTED_VALIDITY_MISMATCH`
- `M479_PERSISTED_BLOCKERS_MISMATCH`
- `M479_RECONSTRUCTED_BLOCKERS_MISMATCH`
- `M479_VALIDITY_MISMATCH`
- `M479_BLOCKERS_MISMATCH`
- `M479_VERIFICATION_FINGERPRINT_MISMATCH`

Structurally invalid persisted records, invalid source receipts, missing bound snapshots and failed source reconstruction fail closed.

## API boundary

The direct verification endpoint is authenticated, ministry-scoped and read-only. It performs no database mutation. No new table or migration is required.

## Compatibility and safety

M4.80 does not alter M4.79 fingerprint payloads, append-only semantics, migration state or M4.78 blocker semantics. It introduces no M4.81+ runtime dependency and does not perform provider execution, create credentials, mutate payroll/payment state or grant production authority.
