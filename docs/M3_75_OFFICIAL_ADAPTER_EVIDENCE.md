# M3.75 — Official Adapter Evidence Contract

M3.75 adds a fail-closed registry for the six external adapter boundaries:
SINA, accounting, treasury, bank, tax and insurance.

Each record binds provider, schema version, authoritative contract source identifier,
SHA-256 digest, repository, candidate SHA and verification timestamp. The registry
requires the complete canonical set and rejects missing, mismatched, future-dated or
expired evidence.

This does not implement or activate real external endpoints. The existing protocol and
FailClosedAdapter boundary remains in force until authoritative contracts, credentials,
staging/pilot validation and formal operational approval exist.
