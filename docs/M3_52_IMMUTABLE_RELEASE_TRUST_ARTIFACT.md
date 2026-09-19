# M3.52 — Immutable Release Trust Artifact

## Purpose

M3.52 converts a successfully verified M3.51 release trust pack into a deterministic, write-once `tar.gz` artifact.

The artifact metadata binds the release identity to the M3.51 pack fingerprint, archive SHA-256 digest and exact archive size. The artifact ID is derived from the pack fingerprint.

## Artifact construction

`m3_52_release_trust_artifact.py build` first runs the M3.51 verifier. It then creates a deterministic USTAR/GZIP archive with normalized file metadata, sorted members and a zero gzip timestamp.

The builder rejects an existing output archive instead of overwriting it. Symbolic links, unsafe archive member names, duplicate members and private-key material are outside the accepted evidence boundary.

## Verification

`verify` validates the external artifact metadata, archive filename, SHA-256 digest and size, rejects unsafe members, safely extracts the archive into a temporary directory and reruns the M3.51 verifier.

The reconstructed pack identity must match the recorded artifact identity, release ID, tag, candidate SHA and pack fingerprint.

## GitHub Actions publication

The M3.52 CI workflow publishes the rehearsal archive as a single immutable GitHub Actions artifact and separately publishes a publication attestation containing the GitHub artifact ID, URL and GitHub-reported artifact digest.

GitHub's current `upload-artifact` documentation states that v4+ artifacts are immutable and exposes an SHA-256 artifact digest; M3.52 uses the current action line in CI while retaining its own deterministic archive digest as the source-level integrity value. The workflow remains rehearsal-only.

## Production boundary

M3.52 does not create a production GitHub Release, authorize deployment, or replace finance/legal/operations approval. Production publication remains gated on authoritative evidence, production key custody, independent security assessment, integration/staging evidence, reconciliation, recovery and formal release certification.