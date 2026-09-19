# M3.53 — Release Publication Gate

## Purpose

M3.53 defines a fail-closed technical boundary between a verified M3.52 trust artifact and a prospective GitHub Release publication.

The gate binds the repository, release ID, tag, exact candidate commit SHA, M3.52 artifact ID, artifact fingerprint, archive SHA-256 digest and archive size into one deterministic fingerprint.

## Verification

`m3_53_release_publication_gate.py build` first verifies the complete M3.52 artifact. It then writes a write-once publication-gate record.

`verify` re-verifies the artifact and checks that repository and tag match the gate. The recorded release reference is derived as `refs/tags/<tag>` and must match the serialized value.

Any mismatch in repository, tag, candidate SHA, artifact fingerprint, archive digest/size or release reference fails closed.

## Publication boundary

The gate is a technical publication-input attestation. It does not create a GitHub Release and does not authorize production payroll, payment, deployment or operational use.

A future release workflow may require this gate before publication, but the publication step must still be bound to the exact commit and formal release approvals.

## CI rehearsal

The M3.53 workflow builds and verifies the gate from the existing M3.51/M3.52 fixture chain, uploads the gate as short-retention evidence and explicitly records that the run is rehearsal-only.

GitHub's current `actions/upload-artifact` release line is v7.0.1, and the action documents immutable artifact behavior for v4+; M3.53 uses v7 for its rehearsal evidence upload. citeturn231776search0turn231776search1