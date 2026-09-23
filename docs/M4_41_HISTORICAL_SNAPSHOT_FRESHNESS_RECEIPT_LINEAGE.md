# M4.41 — Historical Snapshot-Bound Freshness Receipt Lineage

M4.41 closes the historical freshness evidence chain by linking the M4.40 persisted historical snapshot-bound freshness receipt to the M4.37 receipt-to-snapshot binding.

## Contract

The lineage object binds:

- the M4.40 freshness receipt identity;
- the M4.37 historical receipt binding identity;
- the exact M4.36 snapshot identity and fingerprint;
- registry integrity version/count/fingerprint;
- policy ID/version/fingerprint;
- a deterministic SHA-256 lineage fingerprint.

Creation requires the existing privileged `evidence.binding.write` ministry-managed boundary.

## Verification

Verification independently reloads and verifies both source records, then requires exact continuity for:

- snapshot ID and fingerprint;
- registry integrity identity;
- policy ID/version/fingerprint;
- M4.40 freshness receipt fingerprint;
- M4.37 historical binding fingerprint.

The lineage fingerprint is rebuilt from those exact identities and must match the persisted value.

## API

POST `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage`

GET `/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-snapshot-bound/receipt-lineage/{lineage_id}/verify`

## Safety boundary

Governance/readiness metadata only. No provider execution, credentials, payroll calculation, payment mutation or production authorization.
