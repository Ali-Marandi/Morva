# M4.88 — Historical Integrity Graph Fingerprint

M4.88 adds a deterministic, versioned fingerprint for the M4.77–M4.81 integrity-graph contract declared by the M4.86 machine-readable manifest.

## Scope

The fingerprint covers the contract fields that define the guarded architecture:

- manifest schema version and contract ID;
- guarded layer IDs and source paths;
- required dependency modules;
- forbidden-version tokens;
- focused test declarations;
- shared integrity primitive guard;
- graph sequence, cycle policy and dependency direction.

The human-readable manifest description is intentionally excluded so documentation wording changes do not alter the architectural identity.

## Canonicalization

The fingerprint is computed with Morva's shared `canonical_sha256` primitive using sorted JSON keys, compact separators and UTF-8 encoding.

Stored artifact:

`contracts/historical_integrity_graph_m4_88.json`

Source contract:

`contracts/historical_integrity_manifest_m4_86.json`

## Enforcement

A dedicated M4.88 workflow recomputes the fingerprint from the manifest and runs the M4.87 graph validator plus the M4.85/M4.86/M4.84 structural guards.

Any change to the guarded graph contract without updating the fingerprint artifact fails closed in CI.

## Boundary

M4.88 changes no runtime behavior, persistence schema, API contract, application fingerprint payload, blocker semantics or production authorization.
