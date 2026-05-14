#!/usr/bin/env bash
# Nightly backup — Postgres dump + media tarball.
# Runs as jarvis via cron (installed by provision.sh):
#   0 3 * * * /home/jarvis/anjaneya/deploy/scripts/backup.sh >> /var/log/anjaneya/backup.log 2>&1

set -euo pipefail

BACKUP_DIR="/home/jarvis/backups"
APP_DIR="/home/jarvis/anjaneya"
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"

# Load DB credentials from the env file.
set -a
# shellcheck disable=SC1091
source "$APP_DIR/.env"
set +a

echo "[$(date)] Starting backup"

# --- Database -------------------------------------------------------------
DB_FILE="$BACKUP_DIR/db/anjaneya-$DATE.sql.gz"
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" \
    | gzip > "$DB_FILE"
echo "[$(date)] DB backup:    $DB_FILE ($(du -h "$DB_FILE" | cut -f1))"

# --- Media ----------------------------------------------------------------
MEDIA_FILE="$BACKUP_DIR/media/media-$DATE.tar.gz"
if tar -czf "$MEDIA_FILE" -C "$APP_DIR" media/ 2>/dev/null; then
    echo "[$(date)] Media backup: $MEDIA_FILE ($(du -h "$MEDIA_FILE" | cut -f1))"
else
    echo "[$(date)] Media backup: skipped (media/ empty or missing)"
fi

# --- Retention ------------------------------------------------------------
find "$BACKUP_DIR/db"    -name "anjaneya-*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR/media" -name "media-*.tar.gz"    -mtime +$RETENTION_DAYS -delete

echo "[$(date)] Backup complete. Retained last $RETENTION_DAYS days."
