# M4.40 — Historical Snapshot-Bound Freshness Receipts

M4.40 persists the deterministic M4.39 historical snapshot-bound freshness evaluation as an append-only receipt.

## Contract

A receipt records the exact:

1. repository and candidate SHA;
2. target environment and organization scope;
3. historical registry snapshot ID and fingerprint;
4. registry integrity version, policy count and fingerprint;
5. policy ID, version and policy fingerprint;
6. convergence and freshness timestamps/fingerprint;
7. historical snapshot-bound evaluation fingerprint;
8. recording actor and creation timestamp.

The receipt fingerprint is the M4.39 deterministic evaluation fingerprint and is unique. Re-recording the same fingerprint is idempotent only for the original actor; a different actor is rejected.

## Verification

Verification is independent and fail-closed:

1. reload the persisted receipt;
2. reconstruct the exact M4.36 historical snapshot;
3. resolve the recorded policy only from that snapshot membership;
4. compare snapshot, registry and policy identities;
5. rebuild the M4.39 deterministic evaluation;
6. require the rebuilt fingerprint to equal the persisted receipt fingerprint.

This prevents a receipt from becoming a trusted historical record merely because its row is present in the database.

## API

Authenticated creation:

POST `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts`

Read-only history:

GET `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts`

Read-only independent verification:

GET `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipts/{receipt_id}/verify`

Receipt creation is ministry-managed and requires the existing `evidence.binding.write` privileged boundary.

## Safety boundary

Governance/readiness metadata only. No provider execution, credentials, payroll calculation, payment mutation or production authorization.
