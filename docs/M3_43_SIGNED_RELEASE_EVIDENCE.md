# M3.43 Signed Release Evidence Bundle

## Scope

M3.43 introduces a formal evidence-bundle contract that binds the M3.41 artifact manifest,
the M3.40 aggregate gate, and the M3.42 release rehearsal.

The bundle records:

- release identifier and tag
- exact candidate Git commit SHA
- manifest, aggregate-gate and rehearsal fingerprints
- SHA-256 and size for every evidence file included in the bundle
- an Ed25519 signature with a public-key-derived key identifier and timezone-aware timestamp

The signed payload is canonicalized before signing so the signature is independent of JSON
whitespace and key ordering.

## Verification

The verifier checks, in order:

1. evidence-file existence, size and SHA-256
2. bundle fingerprint integrity
3. signature algorithm and key identifier
4. Ed25519 signature validity
5. exact candidate-SHA match when an expected SHA is supplied

A signature cannot make an incomplete release gate ready. The aggregate gate remains the
authoritative production-readiness decision.

## CI boundary

The M3.43 workflow creates an ephemeral Ed25519 key solely for a rehearsal run. The private
key is never uploaded as an artifact. The public key and signed rehearsal bundle are retained
only as CI evidence.

The CI gate fixture is deliberately incomplete and therefore remains blocked. No finance,
legal, operations, independent-security, disaster-recovery, load/performance, reconciliation,
deployment or release-publication approval is manufactured by this workflow.

## Production boundary

The M3.43 bundle is an integrity/authenticity mechanism, not a production authorization.

Production use still requires the real externally approved evidence, controlled signing-key
custody, formal domain signoffs, release publication controls and deployment evidence defined
by the production gate.
