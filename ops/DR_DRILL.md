# Morva Disaster-Recovery Drill

## Purpose

Provide a repeatable, auditable backup/restore procedure for PostgreSQL without placing credentials or production data in Git.

## Preconditions

- A production-like PostgreSQL source is available through `MORVA_DATABASE_URL`.
- An isolated PostgreSQL restore target is available through `MORVA_DR_RESTORE_URL`.
- Backup storage is encrypted and access-controlled by the deployment environment.
- The drill is authorized by the system owner and run against a non-production copy unless the formal DR policy explicitly permits otherwise.

## Procedure

Run:

```bash
bash ops/dr_drill.sh
```

The drill:

1. creates a PostgreSQL custom-format dump;
2. validates the dump catalog with `pg_restore --list`;
3. restores into the isolated target;
4. verifies that the restored database contains expected public tables;
5. emits a machine-readable `DRILL_OK` or `DRILL_FAILED` result.

## Evidence to record outside Git

- drill date/time;
- source environment identifier;
- backup object identifier and encrypted-storage confirmation;
- restore target identifier;
- dump integrity result;
- restore result;
- application smoke-test result;
- measured RTO;
- measured RPO;
- incident/exception record if applicable;
- approver/sign-off.

RTO/RPO values are deployment commitments and must not be invented in source code.

## Production gate

A successful local or CI syntax check of this script is not a completed disaster-recovery certification. Production certification requires execution in the target environment and retained evidence of backup, restore, RTO/RPO and application recovery.
