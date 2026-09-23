# M4.38 — Historical Snapshot Policy Resolution

M4.38 makes the M4.36 historical registry snapshot usable as an explicit policy-selection boundary.

## Contract

The snapshot repository now resolves a policy only after independently reconstructing the exact historical member-ID set. The selected policy must:

- exist as the requested policy ID and positive version;
- be structurally valid and fingerprint-verified;
- belong to the exact member UUID set captured by the historical snapshot.

A policy appended after snapshot capture therefore cannot be selected through the historical snapshot, even when that policy exists in the current registry.

## API

GET /api/v1/integration-execution/readiness/convergence/freshness/policies/snapshots/{snapshot_id}/policies/{policy_id}

Verification is read-only and uses the existing authenticated evidence-read boundary.

## Safety boundary

Governance/readiness metadata only. No provider execution, credentials, payroll calculation, payment mutation or production authority.
