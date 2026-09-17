#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BACKUP_DIR:?BACKUP_DIR must be set}"
: "${BACKUP_ENCRYPTION_KEY_FILE:?BACKUP_ENCRYPTION_KEY_FILE must be set}"

mkdir -p "$BACKUP_DIR"
umask 077

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/morva-${stamp}.dump.enc"
manifest="$BACKUP_DIR/morva-${stamp}.sha256"

tmp="$(mktemp --suffix=.dump)"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > "$tmp"
openssl enc -aes-256-gcm -pbkdf2 -salt -pass file:"$BACKUP_ENCRYPTION_KEY_FILE" -in "$tmp" -out "$out"
sha256sum "$out" > "$manifest"

echo "$out"
