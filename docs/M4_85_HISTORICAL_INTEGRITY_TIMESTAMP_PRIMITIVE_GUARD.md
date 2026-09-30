# M4.85 — Historical Integrity Timestamp Primitive Guard

M4.85 adds a structural regression guard over the M4.77/M4.78 historical-integrity runtimes.

### Guarded contract
- M4.77 and M4.78 must import `canonical_utc_timestamp` from `morva.runtime.historical_integrity_primitives`.
- Those runtimes must not reintroduce direct `datetime.timezone` / `timezone.utc` timestamp normalization.
- Those runtimes must not serialize integrity timestamps with local `datetime.isoformat()`.
- The guard uses Python AST inspection so the rule is structural rather than formatting-dependent.

### Boundary
This tranche changes no persistence schema, API contract, fingerprint payload, blocker code, or production authority. It only prevents architectural regression of the shared UTC timestamp primitive.
