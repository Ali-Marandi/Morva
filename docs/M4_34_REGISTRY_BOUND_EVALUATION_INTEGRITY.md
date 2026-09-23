# M4.34 Registry-Bound Freshness Evaluation Integrity

M4.34 adds a new read-only evaluation path that binds a freshness assessment to the aggregate integrity snapshot of the persisted policy registry used for that evaluation.

## Contract

The registry-integrity-bound evaluation:

- resolves the exact persisted policy ID and version;
- evaluates the latest persisted scope-bound convergence under that policy;
- computes the current deterministic registry integrity snapshot in the same database session;
- binds policy identity, freshness-assessment identity and registry integrity identity into a new deterministic fingerprint;
- exposes the registry policy count and aggregate registry fingerprint in the response.

The existing registry-bound freshness endpoint is unchanged for backward compatibility.

## API

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound-integrity`

Required query parameters are the same scope/candidate selectors used by the existing registry-bound endpoint, plus `policy_id` and optional `policy_version` (default `1`).

## Safety boundary

Verification and governance metadata only. No provider execution, credential use, payroll calculation, payment mutation or production authorization is introduced.
