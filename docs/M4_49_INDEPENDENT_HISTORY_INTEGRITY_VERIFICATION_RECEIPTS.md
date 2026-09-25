# M4.49 — Independent Historical Verification History Integrity Receipts

## Purpose

M4.49 persists the independent M4.48 verification result for an M4.47 history-integrity snapshot as append-only, fingerprint-idempotent readiness evidence.

## Contract

For a selected M4.47 snapshot, the persistence layer reconstructs the complete M4.46 independent-verification history that existed before the snapshot timestamp, re-verifies each source record, and then invokes the independent M4.48 verifier. The resulting verification identity, aggregate fingerprints, record counts, validity state and deterministic blockers are stored in a write-once receipt.

Repeated persistence of the same verification fingerprint is idempotent for the same actor and is rejected for a different actor. Listing and direct verification re-run the reconstruction instead of trusting the stored receipt as authoritative.

## API surface

- Ministry-managed POST for persisting an M4.48 verification receipt for a snapshot.
- Ministry-managed cursor-paginated verification history with snapshot and validity filters.
- Authenticated direct verification of a persisted M4.49 receipt.

## Persistence

The dedicated migration 0037_independent_historical_freshness_verification_history_integrity_receipts.py creates the M4.49 table, a foreign key to the M4.47 snapshot, fingerprint uniqueness and query indexes.

## Safety boundary

M4.49 is governance/readiness verification metadata only. It does not execute external providers, use production credentials, calculate payroll, mutate payments or grant production authorization. External authoritative evidence, staging/pilot execution and formal certification remain outside this software path.
