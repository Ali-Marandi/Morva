# M4.4 — Master-Data Evidence Bridge

M4.4 binds an externally supplied M4.1 master-data evidence item to an internally accepted master-data assessment.

## Contract

The bridge requires:
- an accepted internal master-data assessment;
- an M4.1 evidence item of type `master_data`;
- exact population-scope equality;
- exact SHA-256 equality between the external evidence artifact and the accepted evidence hash;
- existing authority-confirmation and integrity-snapshot evidence;
- a distinct binding actor;
- timezone-aware binding time.

The binding fails closed if evidence is missing, unaccepted, future-dated, expired, out of scope or inconsistent with the accepted internal evidence hash.

## Safety

No employee record, national identifier, ministry dataset, real source artifact or production credential is added to Git. The bridge only binds metadata and existing evidence fingerprints.
