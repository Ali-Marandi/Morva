# M3.34 — Backup, WAL/PITR and Disaster-Recovery Drill

## Scope

This tranche adds a provider-neutral software evidence contract plus PostgreSQL operational scripts for encrypted logical backups and point-in-time restore preparation. It does not certify a production backup platform, storage provider, KMS/HSM, RTO/RPO target, or disaster-recovery environment.

## Required production evidence

Every approved recovery drill must record:

- backup identifier and SHA-256 digest;
- encryption verification using the approved production key custody path;
- base-backup and WAL archive identifiers;
- restore start/completion timestamps with timezone;
- measured RPO and RTO against approved targets;
- WAL replay success;
- point-in-time target verification using an application-level marker;
- operator identity and immutable evidence location;
- resulting evidence fingerprint.

`RecoveryDrillEvidence` is intentionally fail-closed: missing encryption verification, WAL replay, PITR verification, or RPO/RTO compliance prevents release readiness.

## Operational scripts

`ops/postgres/backup.sh` produces an encrypted custom-format PostgreSQL dump using AES-256-GCM through the project's existing cryptography dependency and emits a SHA-256 manifest. The encryption key file must contain exactly 32 raw bytes and must be supplied by the approved secret/key custody system; it must never be committed to source control.

`ops/postgres/pitr-restore.sh` creates a restore copy from PostgreSQL base-backup streaming, configures `restore_command`, sets a recovery target time, and enables `recovery.signal`. The WAL archive must be an independently retained production artifact.

## Drill sequence

1. Create a PostgreSQL base backup and confirm the backup digest.
2. Verify the encrypted backup can be decrypted only with the approved key custody path.
3. Record an application-level marker and its UTC timestamp.
4. Generate and archive WAL after the marker.
5. Restore the base backup into an isolated environment.
6. Configure `restore_command` against the retained WAL archive and choose a target time before/after the marker according to the drill objective.
7. Start recovery and verify the expected application-level state at the target.
8. Record measured RPO/RTO and all evidence in the approved evidence store.
9. Reject the release gate if any required control is missing or non-compliant.

## Production prerequisites still outside this repository

KMS/HSM custody, backup storage isolation, backup-key segregation, retention/immutability policy, cross-region or secondary-site replication, automated WAL archiving, restore capacity, approved RPO/RTO values, access-control review, and independent security/DR sign-off remain operational certification gates.
