# M3.66 — External Certification Evidence Contract

M3.66 formalizes the evidence that remains outside the software repository before
production certification.

The registry requires exactly these roles:

- legal approval;
- finance approval;
- security assessment;
- operations approval;
- authoritative master data;
- official adapters;
- reconciliation evidence;
- disaster-recovery exercise;
- load validation;
- release certification;
- publication evidence;
- deployment validation.

Every item is bound to the exact candidate SHA and repository, must be externally issued
and marked verified, carries a SHA-256 digest and timezone-aware verification timestamp,
and may carry an expiry time.

The registry itself is deterministic and write-once. This milestone does not fabricate,
approve or substitute for any external evidence.
