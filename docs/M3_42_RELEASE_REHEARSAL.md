# M3.42 Release Rehearsal

## Scope

M3.42 composes the concrete M3.41 artifact manifest with the M3.40 aggregate release
gate into one fail-closed release-rehearsal contract.

The rehearsal binds, exactly:

- candidate Git commit SHA
- release tag
- release identifier
- manifest fingerprint
- aggregate gate fingerprint
- every artifact path and SHA-256 digest between the manifest and attestation

The rehearsal can also re-hash the built artifact directory. A modified, added, removed,
or mismatched artifact fails the rehearsal before release readiness is evaluated.

## CI behavior

The M3.42 workflow performs:

1. package build
2. M3.41 manifest generation
3. creation of a clearly marked **rehearsal-only** aggregate-gate fixture
4. exact manifest/gate composition checks
5. artifact re-hashing
6. evidence summary emission

The CI fixture intentionally lacks real finance, legal, operations, independent-security,
DR, load/performance, reconciliation, signing, and release-publication approvals. Its purpose
is to exercise the wiring and fail-closed behavior without manufacturing production evidence.

## Production boundary

A successful rehearsal is not a production authorization, certification, signature, deployment,
or GitHub Release publication.

The `--require-ready` mode is reserved for a real evidence bundle containing actual approved
evidence. Until that evidence exists, the aggregate gate must remain blocked.
