# M4.86 — Machine-Readable Historical Integrity Manifest

M4.86 establishes a single machine-readable contract for the M4.77–M4.81 historical-integrity chain.

## Manifest

The authoritative contract is:

`contracts/historical_integrity_manifest_m4_86.json`

It defines, for every guarded tranche:

- runtime or persistence path;
- required dependency modules;
- forbidden forward-dependency tokens;
- focused test path;
- required test imports and expected symbols.

It also defines the shared `canonical_sha256` adoption guard for M4.77, M4.78 and M4.80.

## Enforcement

M4.84 and M4.85 regression guards now consume the manifest instead of maintaining separate hard-coded contract tables. M4.86 adds a dedicated CI workflow that validates the same manifest-driven contract with Ruff and focused pytest execution.

## Boundary

The manifest is a governance/architecture contract. It does not alter runtime behavior, persistence schema, API contracts, fingerprint payloads or blocker codes.
