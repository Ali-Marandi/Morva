# M3.60 — Independent Production Promotion Verifier

## Purpose

M3.60 independently verifies the M3.59 production-promotion gate. It revalidates the
M3.58 bundle, reconstructs the M3.59 gate fingerprint, rechecks the external promotion
authorization and requires the externally supplied deployment attestation to match the
attestation embedded in the bundle.

## Required consistency

The verifier proves consistency across:

- M3.58 bundle ID and fingerprint;
- repository, release ID, tag and exact candidate SHA;
- source environment and production target;
- promotion authorization ID, approval time and approver;
- deployment ID and operator;
- embedded and external deployment attestation.

The deployment operator and promotion approver must remain distinct.

## Safety boundary

M3.60 is strictly verification-only and writes only a local, write-once verification
receipt. It does not promote, deploy, publish or mutate infrastructure.
