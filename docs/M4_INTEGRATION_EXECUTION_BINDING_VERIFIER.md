# M4 Integration Execution Binding Verifier

This verifier independently reconstructs the M4 integration-execution binding produced by the M4 integration-execution evidence bridge.

## Verification chain

The verifier re-loads the recorded binding, checks its stored fingerprint, confirms the current authoritative M4 registry fingerprint and exact repository/candidate SHA, then reconstructs the binding through the bridge's fail-closed builder.

The resulting comparison therefore covers:

- the M3.86 integration-execution readiness identity;
- the exact staging/pilot environment and execution ID;
- the M3.84 execution and M3.85 independent-verification fingerprints;
- the current M4 authoritative registry fingerprint;
- all six canonical adapter-to-authoritative-evidence mappings; and
- the binding actor/timestamp and deterministic binding fingerprint.

A verification receipt is itself fingerprinted and contains no credentials or provider data.

## Fail-closed behavior

Verification rejects a binding when:

- the serialized binding is malformed or fingerprint-tampered;
- the M4 registry fingerprint has changed;
- the repository or candidate SHA differs;
- the supplied adapter-to-evidence mapping cannot reconstruct the recorded binding;
- the underlying M3.86 readiness gate fails its own structural/fingerprint checks; or
- the reconstructed binding differs from the recorded binding.

## Safety boundary

This component is verification-only. It does not execute SINA, accounting, treasury, bank, tax or insurance providers, use credentials, contact external endpoints, mutate production systems or manufacture staging/pilot evidence.

Real integration execution evidence remains an externally produced and independently verified prerequisite.
