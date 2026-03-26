#!/usr/bin/env bash
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Required env vars
: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_FILE="/tmp/wallet_${TIMESTAMP}.sql.gz"

# Step 1: dump
log "Starting pg_dump of '${POSTGRES_DB}' on ${POSTGRES_HOST}:${POSTGRES_PORT}"
export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --no-password \
    | gzip > "${BACKUP_FILE}"
log "Dump complete: ${BACKUP_FILE} ($(du -sh "${BACKUP_FILE}" | cut -f1))"

# Step 2: upload
log "Uploading to ${RCLONE_REMOTE}"
rclone copy \
    --config /rclone/rclone.conf \
    "${BACKUP_FILE}" \
    "${RCLONE_REMOTE}"
log "Upload complete"

# Step 3: clean up local file
rm -f "${BACKUP_FILE}"
log "Local temp file removed"

# Step 4: prune old remote backups
log "Deleting remote files older than ${BACKUP_RETAIN_DAYS} days from ${RCLONE_REMOTE}"
rclone delete \
    --config /rclone/rclone.conf \
    --min-age "${BACKUP_RETAIN_DAYS}d" \
    "${RCLONE_REMOTE}"
log "Remote pruning complete"

log "Backup finished successfully"