.PHONY: dev prod down dev-build prod-build logs lint lint-fix setup backup backup-logs

# Development
dev:
	docker compose -f docker/dev/docker-compose.yml up -d

dev-build:
	docker compose -f docker/dev/docker-compose.yml up -d --build

dev-down:
	docker compose -f docker/dev/docker-compose.yml down

dev-reset:
	docker compose -f docker/dev/docker-compose.yml down -v
	docker compose -f docker/dev/docker-compose.yml up -d --build

# Setup
setup:
	pre-commit install
	@echo "pre-commit hooks installed."

# Linting
lint:
	cd backend && uv run ruff check .

lint-fix:
	cd backend && uv run ruff check --fix . && uv run ruff format .

# Utilities
logs:
	docker compose -f docker/dev/docker-compose.yml logs -f

db:
	docker compose -f docker/dev/docker-compose.yml up db -d

seed:
	docker exec -it dev-backend-1 uv run python scripts/seed_dev.py

# Production backup commands
backup:
	docker compose -f docker/prod/docker-compose.yml exec backup /backup.sh

backup-logs:
	docker compose -f docker/prod/docker-compose.yml logs -f backup
