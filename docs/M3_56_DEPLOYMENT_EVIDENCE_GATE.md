# M3.56 — Deployment Evidence Gate

## Purpose

M3.56 binds a successful deployment attestation to the exact M3.55
post-publication verification receipt and the exact candidate commit.

## Required evidence

The external attestation must provide:

- a versioned evidence identifier;
- the M3.55 receipt fingerprint;
- environment: staging, pilot or production;
- a deployment identifier and succeeded status;
- the exact deployed Git commit SHA;
- a deployment timestamp and operator;
- a SHA-256 health-check evidence digest;
- a rollback target commit SHA;
- explicit rollback verification.

The gate rejects any attestation whose deployed SHA differs from the candidate, whose
receipt fingerprint is unrelated to the published Release, whose deployment status is not
succeeded or whose rollback evidence is not explicitly verified.

## Safety boundary

M3.56 does not deploy anything and does not mutate GitHub Releases, tags, assets or
infrastructure. It converts external deployment evidence into a deterministic,
write-once software gate.

The production environment is supported as an evidence scope, but this implementation
does not claim that production deployment has occurred or that production certification
has been granted.

## CI boundary

CI exercises the gate with deterministic fixtures only. Real deployment evidence must be
supplied by the authorized deployment system after an actual deployment.
