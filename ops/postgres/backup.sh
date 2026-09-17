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
python - "$tmp" "$out" "$BACKUP_ENCRYPTION_KEY_FILE" <<'PY'
import os
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

source, target, key_file = sys.argv[1:]
key = open(key_file, "rb").read()
if len(key) != 32:
    raise SystemExit("BACKUP_ENCRYPTION_KEY_FILE must contain exactly 32 raw bytes")
nonce = os.urandom(12)
plaintext = open(source, "rb").read()
ciphertext = AESGCM(key).encrypt(nonce, plaintext, b"morva-postgres-backup-v1")
with open(target, "wb") as handle:
    handle.write(nonce + ciphertext)
PY
sha256sum "$out" > "$manifest"

echo "$out"
