FROM alpine:3.19

RUN apk add --no-cache \
    postgresql16-client \
    bash \
    curl \
    ca-certificates \
    tzdata

RUN curl -fsSL https://rclone.org/install.sh | bash

COPY docker/backup/backup.sh /backup.sh
COPY docker/backup/entrypoint.sh /entrypoint.sh

RUN chmod +x /backup.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]