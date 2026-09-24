# M4.42 — Historical Snapshot-Bound Freshness Receipt Lineage History

## Purpose

M4.42 adds a deterministic read-only history boundary for M4.41 historical freshness receipt lineage records.

The history endpoint is designed for audit/review workflows. It does not create new evidence and does not grant production authority.

## Contract

- Newest-first ordering is deterministic on `created_at DESC, id DESC`.
- Pagination uses the existing timestamp-plus-UUID cursor shape.
- Optional filters target the exact M4.40 freshness receipt, M4.37 historical binding, or historical registry snapshot.
- Every selected lineage record is independently re-verified against its M4.40 receipt and M4.37 binding before being returned.
- History access is ministry-managed and read-only.

## API

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/history`

Supported query parameters:

- `freshness_receipt_id`
- `historical_binding_id`
- `snapshot_id`
- `before_created_at`
- `before_id`
- `limit`

The response returns the lineage payload, recording actor, creation timestamp, `has_more` and the next cursor when more records exist.

## Safety boundary

M4.42 is governance/readiness metadata only. It performs no provider execution, credential activation, payroll calculation, payment mutation, or production authorization.
