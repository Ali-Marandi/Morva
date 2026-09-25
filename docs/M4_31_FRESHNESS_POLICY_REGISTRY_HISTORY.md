# M4.31 Freshness Policy Registry History

M4.31 hardens the M4.30 persisted freshness-policy registry with a deterministic, cursor-paginated read API.

## Contract

The registry history endpoint:

- returns persisted policy identities newest-first in deterministic creation order;
- uses `before_created_at` plus `before_id` as a stable cursor;
- limits each page to at most 100 records;
- validates each restored policy fingerprint before returning it;
- does not mutate policy state.

## API

`GET /api/v1/integration-execution/readiness/convergence/freshness/policies`

Supported query parameters:

- `before_created_at` — optional timezone-aware cursor timestamp;
- `before_id` — optional UUID cursor tie-breaker;
- `limit` — 1..100, default 50.

The response includes `items`, `has_more`, and the next cursor when more records remain.

## Safety boundary

This is governance/readiness metadata only. It performs no provider execution, credential use, payroll calculation, payment mutation or production authorization.
