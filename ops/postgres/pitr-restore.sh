#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must be set}"
: "${BASE_BACKUP_DIR:?BASE_BACKUP_DIR must be set}"
: "${WAL_ARCHIVE_DIR:?WAL_ARCHIVE_DIR must be set}"
: "${RESTORE_DIR:?RESTORE_DIR must be set}"
: "${RECOVERY_TARGET_TIME:?RECOVERY_TARGET_TIME must be set in PostgreSQL timestamp form}"

rm -rf "$RESTORE_DIR"
mkdir -p "$RESTORE_DIR"
umask 077

pg_basebackup \
  --dbname="$DATABASE_URL" \
  --pgdata="$RESTORE_DIR" \
  --format=plain \
  --wal-method=stream \
  --checkpoint=fast \
  --no-password

cat > "$RESTORE_DIR/postgresql.auto.conf" <<EOF
restore_command = 'cp "$WAL_ARCHIVE_DIR/%f" "%p"'
recovery_target_time = '$RECOVERY_TARGET_TIME'
recovery_target_action = 'pause'
EOF

touch "$RESTORE_DIR/recovery.signal"

echo "$RESTORE_DIR"
