.PHONY: dev prod down dev-build prod-build logs lint lint-fix setup test backup backup-logs

DEV := docker compose -f docker/dev/docker-compose.yml
PROD := docker compose -f docker/prod/docker-compose.yml

# Development
dev:
	$(DEV) up -d

dev-build:
	$(DEV) up -d --build

dev-down:
	$(DEV) down

dev-reset:
	$(DEV) down -v
	$(DEV) up -d --build

# Setup
setup:
	pre-commit install
	@echo "pre-commit hooks installed."

# Linting
lint:
	cd backend && VIRTUAL_ENV= uv run ruff check .

lint-fix:
	cd backend && VIRTUAL_ENV= uv run ruff check --fix . && VIRTUAL_ENV= uv run ruff format .

# Utilities
logs:
	$(DEV) logs -f

db:
	$(DEV) up db -d

seed:
	docker exec -it dev-backend-1 uv run python scripts/seed_dev.py

test:
	bash docker/test/run-tests.sh

# Production backup commands
backup:
	$(PROD) exec backup /backup.sh

backup-logs:
	$(PROD) logs -f backup
