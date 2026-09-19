# M3.58 — Deployment Evidence Bundle

## Purpose

M3.58 packages the release-verification receipt, deployment evidence gate, external
deployment attestation and independent M3.57 verification receipt into one deterministic,
write-once archive.

## Bundle contract

The bundle contains exactly these four evidence sources plus pack.json:

- M3.55 post-publication release verification receipt;
- M3.56 deployment evidence gate;
- external deployment attestation;
- M3.57 independent deployment verification receipt.

Each source is hashed and size-bound in the bundle manifest. Private-key PEM markers are
rejected. The archive uses the deterministic USTAR/GZIP construction already established
for Morva release-trust artifacts.

Verification recomputes the archive digest and source hashes, validates the bundle
metadata fingerprint, re-extracts only regular safe paths and reruns the M3.57 evidence
verification on the extracted sources.

## Safety boundary

M3.58 does not deploy, publish, edit or delete anything. It only packages and verifies
evidence already produced by preceding gates.

The resulting bundle is suitable for later signing, retention and independent audit. It
does not itself establish legal, finance, security or operations approval.
