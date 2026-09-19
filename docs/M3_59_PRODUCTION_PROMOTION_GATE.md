# M3.59 — Production Promotion Evidence Gate

## Purpose

M3.59 creates a fail-closed promotion boundary between a verified staging/pilot deployment
and a prospective production promotion.

## Contract

The gate requires:

- a valid M3.58 deployment-evidence bundle;
- an external versioned promotion authorization bound to the exact bundle fingerprint;
- source environment staging or pilot and target environment production;
- exact candidate SHA consistency across the bundle and deployment attestation;
- succeeded deployment evidence from M3.56 and independent verification from M3.57;
- a timezone-aware approval timestamp;
- a distinct promotion approver from the deployment operator.

The authorization must contain a real Boolean approved field. String values such as "false"
are rejected.

## Safety boundary

M3.59 does not promote, deploy, publish, edit or delete anything. It only creates a
write-once deterministic evidence gate. The existence of this gate does not establish that
production approval or deployment has actually occurred.

## Production status

Formal finance/legal/security/operations certification and real production authorization
remain external requirements.
