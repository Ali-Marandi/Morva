# Morva 1.0.1 Release

## Release intent
Morva 1.0.1 is a security and CI reliability patch release following the 1.0.0 web platform release.

## Included
- `cryptography` upgraded to the audited 50.x line.
- Python 3.12 and 3.13 CI validation passing.
- Alembic migration validation passing.
- Ruff lint validation passing.
- Full pytest suite passing.
- `pip-audit` passing with no unresolved dependency vulnerabilities in the tested environment.
- Web production build passing.
- Payroll lifecycle regression test aligned with the canonical `draft -> data_received` boundary.

## Production posture
This release does not authorize real payroll execution or payment release. The application remains fail-closed until all production certification gates are evidenced.

## Mandatory production gates
1. Approved 1405 legal/rule pack.
2. Current official tax, pension, insurance and deduction instructions loaded and regression-tested for every employee population.
3. Real non-production SINA/accounting/treasury/bank endpoints and credentials configured and tested.
4. At least one authoritative payroll sample per employee population reconciled line-by-line with zero unexplained differences.
5. Independent security acceptance plus MFA validation.
6. Backup/restore, PITR and disaster-recovery evidence.
7. Three-way reconciliation across Morva entitlement, Treasury payment instruction and bank confirmation with no unresolved mismatches.

## Data safety
No real employee, bank, payroll or credential data belongs in Git. Production data admission requires provenance, checksum, schema validation and audit metadata.

## AI boundary
AI remains advisory only. It cannot activate legal rules, alter payroll calculations, approve payroll or release payment.
