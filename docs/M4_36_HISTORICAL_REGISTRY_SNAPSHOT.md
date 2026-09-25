# M4.36 Historical Registry Snapshot & Reconstruction

M4.36 adds an append-only historical anchor for the exact membership of a freshness-policy registry snapshot.

## Contract

A snapshot records:

- the M4.33 registry integrity version and aggregate registry fingerprint;
- the exact policy-record count;
- the canonical set of immutable policy-record UUIDs included in the snapshot;
- a membership fingerprint over those UUIDs;
- a deterministic snapshot fingerprint over the above identities.

The membership manifest is the critical historical boundary. Later policy additions do not silently enter an older snapshot, and deletion or mutation of any recorded member causes reconstruction to fail closed.

## API

Capture a ministry-managed snapshot:

POST /api/v1/integration-execution/readiness/convergence/freshness/policies/snapshots

Independently reconstruct and verify a persisted snapshot:

GET /api/v1/integration-execution/readiness/convergence/freshness/policies/snapshots/{snapshot_id}/verify

## Persistence

Migration 0030_readiness_freshness_policy_registry_snapshots stores the immutable snapshot anchor and exact member UUID manifest.

The snapshot repository re-runs the M4.33 integrity calculation against the exact recorded member IDs rather than the current full registry.

## Safety boundary

Verification/governance metadata only. No provider execution, credential use, payroll calculation, payment mutation or production authorization is introduced.