# M3.39 — Release provenance and signing attestation

## Scope

M3.39 adds a software evidence boundary for the final release package. It binds the release tag and exact candidate commit to the M3.37 certification fingerprint, the M3.38 evidence-bundle fingerprint, artifact SHA-256 values and signing/release provenance.

## Fail-closed requirements

A release attestation is not ready unless:

- the release identifier and tag are explicit;
- the candidate commit is an exact Git SHA-1;
- certification and evidence-bundle fingerprints are valid SHA-256 values;
- at least one uniquely identified artifact is present;
- the release URI is retained;
- signing identity, timezone-aware signing time and signature evidence URI are all present.

`ReleaseAttestation.assert_release_ready()` fails closed when any of these conditions is missing.

## Deterministic provenance

`ReleaseAttestation.fingerprint` produces a deterministic SHA-256 digest over the release identifier, tag, candidate commit, certification/evidence fingerprints, artifact hashes and signing/release provenance.

## External boundary

M3.39 does not create a cryptographic signature, publish a GitHub Release, or claim that finance/legal/operations approvals exist. A real release still requires the responsible release signer, the verified build artifacts, the external certification evidence and the formal approvals represented by M3.37/M3.38.

The production gate remains closed until those external artifacts are actually supplied and verified.
