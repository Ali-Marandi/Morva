# M3.41 — Release package integrity

## Scope

M3.41 adds a software evidence boundary for the concrete files produced by the Morva release build. It records each artifact's relative path, byte size and SHA-256 digest, binds the manifest to the exact candidate Git commit and produces a deterministic manifest fingerprint.

## Fail-closed verification

`ReleaseManifest` rejects empty releases, invalid commit SHA-1 values, duplicate paths and traversal paths. `verify_files()` fails when an artifact is missing, unexpected, modified or has a changed byte size. The serialized manifest also carries its own fingerprint and the verification tool rejects content changes that do not match that fingerprint.

## CI behavior

The M3.41 workflow builds the Python wheel and source distribution, generates the manifest outside the artifact directory, and then re-hashes the artifact directory against that recorded manifest. This proves package-integrity behavior in CI without treating the CI build as a signed production release.

## Boundary

M3.41 does not create a cryptographic signature, publish a GitHub Release, assert finance/legal/operations approval, or certify reproducible builds across independent environments. Those remain external release-governance requirements represented by M3.37–M3.40.
