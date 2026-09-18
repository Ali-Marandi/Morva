# M3.44 Independent Evidence Verifier

## Scope

M3.44 adds an independent verification path for the M3.43 signed evidence bundle.

The verifier does not create or sign evidence. It consumes only:

- the signed evidence bundle
- the recorded manifest
- the aggregate release-gate evidence
- the M3.42 rehearsal summary
- the public Ed25519 key
- an optional expected Git commit SHA

It reconstructs the M3.42 release rehearsal from the recorded sources and checks that the
bundle binds to exactly the same release identity and fingerprints.

## Verification sequence

1. Load and integrity-check the evidence-bundle fingerprint.
2. Verify evidence-file sizes and SHA-256 digests.
3. Verify the Ed25519 signature and public-key-derived `key_id`.
4. Reconstruct the M3.41 manifest and M3.40 aggregate gate.
5. Reconstruct the M3.42 rehearsal and compare release ID, tag and fingerprints.
6. Confirm each supplied source file is explicitly listed in the signed bundle.
7. Optionally require an exact expected candidate commit SHA.

The verifier reports the aggregate gate state but does not manufacture or alter readiness.

## Production boundary

Independent verification is a cryptographic integrity/authenticity check. It is not a
substitute for finance, legal, operations, security, disaster-recovery, performance,
reconciliation, deployment or other required production approvals.

The CI workflow continues to use an ephemeral signing key and a deliberately blocked,
rehearsal-only release gate.
