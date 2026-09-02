#!/usr/bin/env bash
set -euo pipefail

: "${MORVA_DATABASE_URL:?set MORVA_DATABASE_URL to the source PostgreSQL connection string}"
: "${MORVA_DR_RESTORE_URL:?set MORVA_DR_RESTORE_URL to an isolated restore target}"
BACKUP_FILE="${MORVA_DR_BACKUP_FILE:-./morva-drill-$(date -u +%Y%m%dT%H%M%SZ).dump}"

umask 077
printf 'Creating encrypted-storage-ready PostgreSQL custom-format dump: %s\n' "$BACKUP_FILE"
pg_dump --format=custom --no-owner --no-acl --dbname="$MORVA_DATABASE_URL" --file="$BACKUP_FILE"

printf 'Checking dump integrity...\n'
pg_restore --list "$BACKUP_FILE" >/dev/null

printf 'Restoring into isolated target...\n'
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$MORVA_DR_RESTORE_URL" "$BACKUP_FILE"

printf 'Running restore verification...\n'
TABLE_COUNT=$(psql "$MORVA_DR_RESTORE_URL" -Atc "select count(*) from information_schema.tables where table_schema='public';")
if [[ "$TABLE_COUNT" -lt 1 ]]; then
  echo 'DRILL_FAILED: restored database contains no public tables' >&2
  exit 1
fi

printf 'DRILL_OK restored_public_tables=%s backup=%s\n' "$TABLE_COUNT" "$BACKUP_FILE"
