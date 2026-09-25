# M4.43 — Historical Freshness Chain Verifier

M4.43 adds an independent, read-only reconstruction of the historical freshness chain spanning the M4.36 snapshot, M4.37 historical binding, M4.40 historical freshness receipt, M4.41 lineage and the M4.42 history boundary.

## Contract

The verifier compares exact:

- M4.40 freshness-receipt identity;
- M4.37 historical-binding identity;
- M4.36 snapshot identity and registry fingerprint;
- policy ID, version and fingerprint;
- registry integrity version, policy count and aggregate fingerprint;
- M4.41 lineage fingerprint.

A valid chain returns `verified` with no blockers. Any cross-record identity drift returns `blocked` with deterministic blocker codes and a deterministic verification fingerprint.

## API

GET `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/{lineage_id}/verify-chain`

The endpoint is authenticated read-only verification metadata. It performs no provider execution, credential activation, payroll calculation, payment mutation or production authorization.

## Safety boundary

M4.43 is a governance/readiness verification boundary only. It does not certify real external evidence or grant production authority.
