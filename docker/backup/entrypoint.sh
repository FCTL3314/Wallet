#!/usr/bin/env bash
set -euo pipefail

BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"
BACKUP_ON_START="${BACKUP_ON_START:-false}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Writing cron schedule: ${BACKUP_SCHEDULE}"
echo "${BACKUP_SCHEDULE} /backup.sh >> /proc/1/fd/1 2>&1" > /etc/crontabs/root

if [ "${BACKUP_ON_START}" = "true" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] BACKUP_ON_START=true — running backup now"
    /backup.sh
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting cron daemon"
exec crond -f -L /dev/stdout
