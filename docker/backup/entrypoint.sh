#!/usr/bin/env bash
set -euo pipefail

BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Writing cron schedule: ${BACKUP_SCHEDULE}"
echo "${BACKUP_SCHEDULE} /backup.sh >> /proc/1/fd/1 2>&1" > /etc/crontabs/root

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting cron daemon"
exec crond -f -L /dev/stdout
