# M3.57 — Independent Deployment Evidence Verifier

## Purpose

M3.57 independently re-reads the M3.56 deployment gate, the M3.55
post-publication receipt and the external deployment attestation. It recomputes the
Gate fingerprint and compares every material deployment field across the three
evidence sources.

## Verification contract

The verifier requires the gate fingerprint to be internally consistent and the Gate
to match:

- repository, release ID, tag and candidate SHA from the M3.55 receipt;
- release-receipt fingerprint from M3.55;
- deployment evidence ID, environment, deployment ID, deployed SHA, timestamp,
  operator, health-check digest and rollback target from the external attestation;
- succeeded deployment status and explicitly verified rollback evidence.

The deployed SHA must equal the candidate SHA. Deployment timestamps must carry an
explicit timezone.

## Safety boundary

M3.57 is read-only. It does not deploy, publish, edit or delete anything. Its output is a
write-once verification receipt for later evidence packaging and audit.

The existence of this verifier does not establish that a deployment has occurred; real
deployment evidence still has to come from the authorized deployment system.

## CI boundary

The workflow runs deterministic fixture tests and scans workflow files for actual
deployment or release mutation command invocations. It does not need a real deployment.
