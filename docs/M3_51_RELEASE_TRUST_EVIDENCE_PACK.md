# M3.51 — Release Trust Evidence Pack

## Purpose

M3.51 composes the independently verified M3.50 trust chain into a portable, deterministic evidence
pack.

The pack records the exact release identity, verification time, trust-registry fingerprints, M3.48
signing-key rotation fingerprint, M3.49 root-rotation fingerprint, M3.50 chain fingerprint and
SHA-256/size for every source file.

## Pack contents

A pack contains exactly one source for each of these roles:

- signed release evidence bundle
- release manifest
- aggregate release gate
- release rehearsal evidence
- release-signing public key
- previous signed trust registry
- intermediate signed trust registry
- current signed trust registry
- M3.48 signing-key rotation ceremony
- M3.49 root trust-anchor rotation ceremony
- old root public key
- new root public key
- M3.50 chain verification receipt

The verifier also rejects unexpected files, missing files, hash/size changes, duplicate roles or
paths, malformed fingerprints, private-key material and an unexpected candidate commit SHA.

## Verification model

`m3_51_release_trust_pack.py verify` first validates the pack manifest and all source hashes, then
reconstructs the M3.50 independent verifier from the pack's recorded public sources. The
reconstructed result must match every trust-chain fingerprint and the M3.50 verification receipt
recorded in the pack.

The pack fingerprint is a deterministic SHA-256 digest over its canonical metadata and sorted source
manifest. The pack contains no private signing or root keys and has no production-authorization
semantics.

## Build boundary

`build` requires an already verifiable M3.43/M3.47 bundle and a successful M3.50 chain verification.
Pack output directories are write-once: an existing output directory is rejected rather than
overwritten.

The CI workflow uses ephemeral test fixtures only. It does not authorize real payroll, payment,
release publication or deployment.

## Remaining operational evidence

M3.51 does not replace formal finance/legal/operations certification, production key custody,
independent security assessment, authoritative data acceptance, official adapters, staging/pilot
settlement evidence, disaster recovery drills or deployment approval.
