# M4.23 Persisted Readiness Receipt History

M4.23 extends the M4.22 persisted integration-execution readiness boundary with deterministic audit history.

## Scope

The history endpoint is read-only and ministry-scoped:

`GET /api/v1/integration-execution/readiness/history`

Supported filters:

- exact candidate Git commit SHA-1;
- target environment: `staging` or `pilot`;
- page size from 1 to 100.

Pagination is cursor-based. The cursor contains both `verified_before` and `before_id` so receipts sharing the same verification timestamp cannot be skipped or duplicated.

## Integrity behavior

Every receipt selected for a history page is reconstructed through the existing M4.21 verification object before it is returned. A persisted fingerprint mismatch, invalid blocker payload, timezone violation or other structural inconsistency produces a fail-closed `409` response.

The repository orders receipts by:

1. `verified_at DESC`
2. `id DESC`

The next-page cursor is emitted only when another record exists.

## Safety boundary

M4.23 does not create provider calls, use external credentials, mutate payroll/payment state or grant production authority. It only exposes previously persisted, independently verified software-side evidence for audit and operational review.

The history API intentionally remains ministry-scoped because the current persisted M4.22 receipt does not carry an organization-scope identity. Organization-scoped receipt history should not be introduced until that binding is part of the canonical persistence contract.
