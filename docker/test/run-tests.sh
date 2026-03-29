#!/bin/sh
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker compose -f $ROOT/docker/test/docker-compose.yml"

cleanup() {
  $COMPOSE down -v 2>/dev/null || true
}
trap cleanup EXIT

$COMPOSE build backend
$COMPOSE run --rm -T backend
