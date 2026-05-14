#!/usr/bin/env bash
# Restore the database from a backup produced by backup.sh.
# Run as jarvis from /home/jarvis/anjaneya:
#   bash deploy/scripts/restore_db.sh /home/jarvis/backups/db/anjaneya-YYYYMMDD-HHMMSS.sql.gz

set -euo pipefail

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "Usage: bash deploy/scripts/restore_db.sh <path-to-backup.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /home/jarvis/backups/db/ 2>/dev/null || echo "  (none found)"
    exit 1
fi

# Load DB credentials from the env file.
set -a
# shellcheck disable=SC1091
source /home/jarvis/anjaneya/.env
set +a

echo "==> WARNING: this DROPS and recreates the '$DB_NAME' database."
echo "==> Restoring from: $BACKUP_FILE"
read -r -p "Type YES to proceed: " confirm
if [ "$confirm" != "YES" ]; then
    echo "Aborted."
    exit 1
fi

echo "==> Stopping the app"
sudo systemctl stop anjaneya.service

echo "==> Recreating the database"
sudo -u postgres psql <<EOF
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
EOF

echo "==> Restoring data"
gunzip -c "$BACKUP_FILE" \
    | PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME"

echo "==> Starting the app"
sudo systemctl start anjaneya.service

echo "==> Restore complete."
