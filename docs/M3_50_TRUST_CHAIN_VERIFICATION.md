# M3.50 Independent Trust-Chain Verification

## Scope

M3.50 provides one verification boundary for the trust chain used by a signed release.
The chain is modeled as three signed registry versions:

- Registry V1 → V2 through the M3.48 signing-key rotation ceremony;
- Registry V2 → V3 through the M3.49 Root trust-anchor rotation ceremony;
- the release evidence bundle bound to Registry V3 through M3.43/M3.47.

The verifier has no private-key capability.

## Verification order

1. Verify the release bundle source chain using the independent M3.44 verifier:
   manifest, aggregate gate, rehearsal summary, current registry, exact candidate SHA and bundle signature.
2. Verify the M3.48 signing-key rotation between V1 and V2.
3. Verify the M3.49 Root handoff between V2 and V3.
4. Confirm the M3.48 Root ID is the source Root of M3.49.
5. Confirm the M3.49 target Root signs V3.
6. Confirm the release-signing public key is active and trusted by V3 at the requested verification time.
7. Re-verify the release bundle signature and emit a deterministic chain fingerprint.

## Result

The verification result records the three registry fingerprints, both ceremony fingerprints and the exact
bundle fingerprint. Its own SHA-256 fingerprint becomes a compact receipt for the complete verified chain.

## Failure behavior

Any mismatch in registry version/fingerprint, Root continuity, ceremony source/target binding, release-signing
key trust, evidence source integrity, bundle identity or signature causes verification to fail closed.

## Production boundary

M3.50 proves software-level cryptographic/provenance composition only. Production authorization remains subject
to real Root/Recovery Anchor custody, legal/finance/operations approvals, authoritative external evidence, staging
and pilot validation, independent security review, deployment controls and the existing production gate.
