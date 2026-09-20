# CI Baseline Repairs — 2026-09-20

This maintenance tranche restores the repository-wide validation baseline exposed by
the current M3.73–M3.88 integration/readiness line.

## Repairs

- remove stale unused datetime and type imports across recent readiness modules/tests;
- restore the missing `_load_payload` helper in production release lineage loading;
- bind both technical-policy and full-policy fingerprints explicitly in release lineage;
- repair the Ed25519 signing fixture context so the temporary signature envelope is exactly
  64 decoded bytes, as required by the type contract;
- remove the remaining unused local in the trust-chain regression test.

## Validation intent

The changes are mechanical or contract-preserving. They do not relax any fail-closed
production gate and do not introduce credentials, legal payroll values, external provider
behavior or production deployment authority.
