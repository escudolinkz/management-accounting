SHELL := /bin/bash
export COMPOSE_DOCKER_CLI_BUILD=1

up:
	docker compose up -d --build
	docker compose ps

e2e:
	docker compose exec frontend npm run test:e2e || true

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.seed

test:
	docker compose exec api pytest -q

fmt:
	docker compose exec api black app
	docker compose exec api ruff check --fix app || true
