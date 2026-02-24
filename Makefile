.PHONY: dev prod down dev-build prod-build logs

# Development
dev:
	docker compose -f docker/dev/docker-compose.yml up -d

dev-build:
	docker compose -f docker/dev/docker-compose.yml up -d --build

dev-down:
	docker compose -f docker/dev/docker-compose.yml down

# Production
prod:
	docker compose -f docker/prod/docker-compose.yml up -d

prod-build:
	docker compose -f docker/prod/docker-compose.yml up -d --build

prod-down:
	docker compose -f docker/prod/docker-compose.yml down

# Utilities
logs:
	docker compose -f docker/dev/docker-compose.yml logs -f

db:
	docker compose -f docker/dev/docker-compose.yml up db -d
