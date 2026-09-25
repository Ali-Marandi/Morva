# M4.37 — Receipt-to-Historical-Snapshot Binding

M4.37 closes the chain between the M4.35 registry-bound freshness receipt and the M4.36 historical registry snapshot.

## Contract

The new append-only binding records:

- the exact M4.35 receipt UUID and binding fingerprint
- the exact M4.36 snapshot UUID and snapshot fingerprint
- registry integrity version, policy count and aggregate registry fingerprint
- the exact policy ID/version/fingerprint used by the receipt
- a deterministic M4.37 SHA-256 binding fingerprint
- the actor and creation timestamp

The binding is created only after:

1. the M4.35 receipt reconstructs successfully;
2. the M4.36 snapshot reconstructs successfully against its exact member UUID set;
3. the receipt registry identity matches the historical snapshot;
4. the receipt's exact policy record is still present, unchanged and a member of the historical snapshot.

## Re-verification

The verification endpoint independently reloads the receipt and historical snapshot, reconstructs the snapshot membership and rechecks the receipt/snapshot registry identity. Later registry appends are intentionally tolerated because M4.36 verifies the recorded historical membership set rather than substituting the current registry.

## API

- POST /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound-integrity/receipt-snapshot-bindings
- GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound-integrity/receipt-snapshot-bindings/{binding_id}/verify

Creation remains ministry-managed and requires the existing privileged evidence.binding.write boundary. Verification is read-only.

## Safety boundary

This is governance/readiness metadata only. It does not execute providers, use production credentials, calculate payroll, mutate payment state or grant production authority.
