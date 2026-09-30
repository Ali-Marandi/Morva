# M4.74 — M4.73 Independent Verification Receipt Persistence

## Purpose

M4.74 persists each M4.73 independent verification result as an append-only, fingerprint-idempotent receipt bound to the exact M4.72 integrity snapshot.

## Guarantees

- The M4.72 source snapshot is revalidated before a receipt is recorded.
- Every point-in-time M4.71 source receipt is reverified before recording and during direct receipt verification.
- The deterministic M4.73 verification fingerprint is the idempotency key.
- A fingerprint already owned by another actor is rejected.
- Receipt history is newest-first and uses timestamp-plus-UUID cursor pagination.
- Stored receipts are reconstructed and compared before they are exposed.

## API

POST: /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-72-verification-history-integrity-snapshots/{snapshot_id}/verification-receipts

GET: /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-72-verification-history-integrity-snapshots/verification-history

GET: /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/independent-verification-history-integrity/m4-72-verification-history-integrity-snapshots/verification-receipts/{verification_id}/verify

Writes remain ministry-managed and use the existing privileged evidence-binding authorization. Reads use the existing evidence-read authorization.

## Safety boundary

M4.74 remains verification/readiness metadata only. It does not execute providers, consume production credentials, mutate payroll or payments, or grant production authorization.

## Validation

The dedicated workflow runs Ruff, focused M4.72/M4.73/M4.74 regression suites, and alembic upgrade head against SQLite.
