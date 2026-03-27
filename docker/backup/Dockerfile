FROM alpine:3.19

RUN apk add --no-cache \
    postgresql16-client \
    bash \
    rclone \
    tzdata

COPY docker/backup/backup.sh /backup.sh
COPY docker/backup/entrypoint.sh /entrypoint.sh

RUN chmod +x /backup.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]