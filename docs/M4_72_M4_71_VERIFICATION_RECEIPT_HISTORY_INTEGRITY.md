# M4.72 — M4.71 Verification-Receipt History Integrity

## Purpose

Capture deterministic point-in-time integrity snapshots over the persisted M4.71 independent-verification receipt history.

## Controls

- Re-verify every M4.71 source receipt before capture, listing and direct snapshot verification.
- Apply the snapshot timestamp as the point-in-time source-history boundary.
- Preserve deterministic record counts, valid counts, history fingerprints and aggregate fingerprints.
- Support ministry-managed cursor history and append-only fingerprint-idempotent snapshots.

## Safety boundary

M4.72 remains governance/readiness metadata only. It adds no provider execution, credentials, payment mutation or production authorization.
