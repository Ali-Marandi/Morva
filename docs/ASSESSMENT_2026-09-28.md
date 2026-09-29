## M4.75 — Independent M4.74 receipt verification

M4.75 independently verifies persisted M4.74 receipts without invoking the M4.74 receipt repository as the source of truth. It reconstructs the M4.73 result directly from the M4.72 snapshot and point-in-time M4.71 receipt history, compares receipt/snapshot/verification identities, and emits deterministic mismatch blockers plus a verification fingerprint.

The implementation remains verification/readiness-only and does not add provider execution, credentials, payment mutation, legal-rate inference or production authorization.

## M4.74 — M4.73 verification-receipt persistence

M4.74 persists the M4.73 independent verification result as an append-only, fingerprint-idempotent receipt. Recording, listing and direct verification reconstruct and re-verify the M4.72 source snapshot plus the point-in-time M4.71 receipt history before trusting persisted verification metadata.

The tranche adds the M4.74 Alembic migration, repository/persistence model, focused regression coverage, authenticated API endpoints, audit evidence and a dedicated CI workflow. The implementation remains verification/readiness-only: no provider execution, credentials, payment mutation, legal-rate inference or production authorization is introduced.

# Morva Technical Assessment — 2026-09-28

## M4.79 — Persisted M4.78 independent verification receipts

M4.79 closes the persistence boundary after M4.78. Each persisted receipt is reconstructed from the M4.77 snapshot and point-in-time M4.76 verification-result history before persistence or exposure. Fingerprint idempotency, actor binding, cursor history and direct re-verification are enforced. This remains a verification/readiness mechanism only.



## M4.78 — Independent M4.77 history-integrity verification

M4.78 adds an independent verification layer over M4.77 snapshots. The verifier does not invoke the M4.77 snapshot builder or use its repository for reconstruction; it canonicalizes point-in-time M4.76 verification results directly, independently recomputes history and aggregate fingerprints, checks counts, emits deterministic blockers and produces a verification fingerprint. The endpoint remains authenticated, read-only and governance-bound.



## M4.77 — M4.76 verification-result history integrity

M4.77 adds a point-in-time aggregate integrity layer over the persisted M4.76 independent-verification results. Every source result is structurally revalidated and independently reconstructed through the M4.76 repository before the snapshot is captured, listed or verified. The snapshot records deterministic record/valid counts and SHA-256 history and aggregate fingerprints, with ministry-managed cursor history and direct verification. The feature remains governance/readiness-only.



## M4.76 — Persisted independent M4.75 verification results

M4.76 closes the persistence boundary after M4.75. The repository stores the complete independent verification identity append-only, keys idempotency to the verification fingerprint, re-verifies the M4.74 source receipt, validates the M4.72 snapshot and reconstructs the M4.73 result from the point-in-time M4.71 receipt history before accepting a persisted result. Ministry-managed cursor history and direct re-verification are exposed through authenticated APIs. This remains a governance/readiness integrity mechanism and does not execute providers, introduce credentials, mutate payments or confer production authority.



**Assessed branch:** `feat/m4-73-m4-72-independent-verification`  
**Assessed commit:** `bc8e41c1acf0f9d3c54b4e8b8411a7fc880f4314`  
**Base:** `main` at `663ce8d42154fa26fb3ff6206b2a8c498d25af82`  
**PR:** #154 — M4.73–M4.75 verification-history integrity expansion  
**Production authority:** blocked

## Scope

This tranche refreshes M4.69 directly on the current `main` baseline rather than replaying the older M4.69 branch history.

Implemented software scope:

- deterministic point-in-time integrity snapshots over persisted M4.68 verification-result history;
- source-result re-verification before capture, listing and direct verification;
- append-only, fingerprint-idempotent snapshot persistence;
- ministry-managed timestamp+UUID cursor history;
- Alembic persistence migration;
- authenticated API endpoints for capture, history and point-in-time verification;
- focused M4.69 regression tests and a dedicated CI workflow.

## Verification posture

The change is structurally isolated to verification/readiness metadata. It does not add provider execution, credentials, payment mutation or production authorization.

The GitHub connector currently exposes the PR and branch state but did not return workflow-run/status records for the new commit at assessment time. Accordingly, CI is **not certified green by this assessment**. The repository's own CI definition still remains the authoritative automated verification path for lint, tests, migrations and dependency checks.

## Review observations

1. M4.69 is based directly on the current `main` head, eliminating the one-commit divergence present in the older M4.69 implementation branch.
2. The migration depends on the existing M4.68 revision `0049_independent_m4_66_receipt_verification_persistence_m4_68`.
3. The persistence repository reconstructs the M4.68 history independently when verifying a persisted M4.69 snapshot, rather than trusting the original aggregate builder output.
4. The API applies ministry scope checks and records the capture operation in the persistent audit trail.
5. Production readiness remains blocked by the documented external legal, authoritative-data, integration, security, reconciliation, resilience and certification evidence requirements.

## Extended implementation position

M4.70 independently reconstructs persisted M4.69 snapshots with deterministic blocker codes and a verification fingerprint. M4.71 persists those independent results as append-only, fingerprint-idempotent receipts with ministry-managed cursor history, direct verification and audit events. M4.72 captures deterministic point-in-time integrity snapshots over the complete M4.71 receipt history with source re-verification and cursor history.

The PR remains open. The GitHub connector exposes the branch/PR metadata, but does not expose workflow-run/status records for this head, so CI is not certified green by this assessment.

## Next engineering boundary

The active engineering line now covers M4.69–M4.75; the next boundary is persistence of M4.75 independent verification results, followed by independent verification of that persisted receipt, while retaining the same fail-closed, independently reconstructable and governance-only boundary.
