# M4.84 — Historical Integrity Primitive Adoption Guard

M4.84 adds a structural regression guard over the historical-integrity runtimes.

### Guarded contract
- M4.77, M4.78 and M4.80 must import canonical_sha256 from morva.runtime.historical_integrity_primitives.
- Those runtimes must not reintroduce hashlib.sha256.
- Those runtimes must not rebuild canonical fingerprint JSON with local json.dumps.
- The guard uses Python AST inspection so the rule is structural rather than dependent on formatting.

### Boundary
This tranche changes no persistence schema, API contract, fingerprint payload, blocker code, or production authority. It only prevents architectural regression of the shared integrity primitive.
