#!/usr/bin/env bash
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

notify() {
    [ -n "${BACKUP_PING_URL:-}" ] || return 0
    wget -q -O /dev/null -T 10 "${BACKUP_PING_URL}${1:-}" || true
}

rclone_cmd() {
    rclone --config "${RCLONE_CONFIG_FILE}" "$@"
}

# Required env vars
: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${RCLONE_REMOTE:?RCLONE_REMOTE is required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
BACKUP_RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"
RCLONE_CONFIG_FILE="${RCLONE_CONFIG_FILE:-/rclone/rclone.conf}"

BACKUP_PREFIX="wallet_"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
BACKUP_FILE="/tmp/${BACKUP_PREFIX}${TIMESTAMP}.sql.gz"
BACKUP_NAME="$(basename "${BACKUP_FILE}")"
CURRENT_STEP="startup"

on_exit() {
    local status=$?
    if [ -f "${BACKUP_FILE}" ]; then
        rm -f "${BACKUP_FILE}"
        log "Local temp file removed"
    fi
    if [ "${status}" -ne 0 ]; then
        log "BACKUP FAILED during '${CURRENT_STEP}' (exit ${status})"
        notify "/fail"
    fi
    exit "${status}"
}
trap on_exit EXIT

# Step 1: dump
CURRENT_STEP="pg_dump"
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
CURRENT_STEP="upload"
log "Uploading to ${RCLONE_REMOTE}"
rclone_cmd copy "${BACKUP_FILE}" "${RCLONE_REMOTE}"
log "Upload complete"

# Step 3: confirm the upload landed before anything gets deleted
CURRENT_STEP="verify"
if ! rclone_cmd lsf "${RCLONE_REMOTE}" --include "${BACKUP_NAME}" | grep -q .; then
    log "Uploaded file '${BACKUP_NAME}' is not on the remote"
    exit 1
fi
log "Verified '${BACKUP_NAME}' on remote"

# Step 4: prune old remote backups
CURRENT_STEP="prune"
log "Deleting backups older than ${BACKUP_RETAIN_DAYS} days from ${RCLONE_REMOTE}"
rclone_cmd delete \
    --min-age "${BACKUP_RETAIN_DAYS}d" \
    --max-depth 1 \
    --include "${BACKUP_PREFIX}*.sql.gz" \
    --drive-use-trash=false \
    "${RCLONE_REMOTE}"
if RETAINED="$(rclone_cmd lsf --files-only --max-depth 1 --include "${BACKUP_PREFIX}*.sql.gz" "${RCLONE_REMOTE}" | wc -l | tr -d ' ')"; then
    log "Remote pruning complete, ${RETAINED} backup(s) retained"
else
    log "Remote pruning complete"
fi

CURRENT_STEP="done"
notify
log "Backup finished successfully"
