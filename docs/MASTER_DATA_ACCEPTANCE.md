# Master Data Acceptance Contract

Morva uses a two-stage master-data acceptance boundary:

1. **Assessment** validates the dataset manifest and the current persisted master-data integrity gate. It produces `eligible` or `blocked` and stores the decision evidence.
2. **Confirmation** records an explicit authoritative-source confirmation reference. Only an `eligible` assessment can be confirmed as `accepted`.

The contract intentionally does not manufacture or infer ministry authority. The authoritative reference must point to evidence supplied through the organization's approved source process.

## Required manifest fields

- dataset name and schema version
- source system and source URI (`https://` or `sftp://`)
- authoritative source reference
- Jalali-compatible dataset period in `YYYY-MM`
- SHA-256 dataset fingerprint
- positive row count
- zero duplicate-key count
- zero rejected-row count
- successful schema validation

## Blocking rules

Assessment is `blocked` when any manifest rule fails or when the persisted master-data integrity gate reports blocking errors. Integrity warnings are retained but do not block eligibility.

Confirmation is fail-closed: an assessment must already be `eligible`, and an explicit authority confirmation reference is required.

## Audit and persistence

Every assessment and confirmation is stored in `master_data_acceptance` and emits an immutable audit event. The dataset fingerprint is unique per dataset name, preventing accidental duplicate acceptance records for the same source artifact.

## API

`POST /api/v1/master-data/acceptance-assessments`

Creates an assessment and returns `blocked` or `eligible`.

`POST /api/v1/master-data/acceptance-assessments/{id}/confirm`

Confirms an eligible assessment as authoritative.

`GET /api/v1/master-data/acceptance-assessments/{id}`

Returns the stored acceptance evidence and current state.

This contract is an acceptance control, not proof that a supplied source is legally authoritative by itself. Formal authority remains an organizational responsibility and must be evidenced by the supplied confirmation reference.
