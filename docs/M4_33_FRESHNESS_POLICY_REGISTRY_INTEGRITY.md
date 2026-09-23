# M4.33 Freshness Policy Registry Integrity Snapshot

M4.33 adds a deterministic aggregate integrity fingerprint over the persisted freshness-policy registry.

## Contract

- every persisted policy is revalidated before inclusion;
- records are canonically ordered by policy ID, policy version and policy fingerprint;
- the snapshot includes the immutable record identity, policy identity, version, max-age, recording actor and creation timestamp;
- the aggregate fingerprint is SHA-256 and does not include the response generation time;
- adding a policy changes the aggregate fingerprint.

## API

`GET /api/v1/integration-execution/readiness/convergence/freshness/policies/integrity`

The endpoint returns the integrity version, policy count, aggregate fingerprint and the response generation timestamp.

## Safety boundary

Read-only governance metadata. No provider execution, credential use, payroll calculation, payment mutation or production authorization is introduced.
