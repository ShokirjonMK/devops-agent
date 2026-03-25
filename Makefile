.PHONY: up down build logs migrate shell-api shell-db test test-cov clean generate-keys

up:
	docker compose --profile telegram up -d

down:
	docker compose --profile telegram down

build:
	docker compose --profile telegram up -d --build

logs:
	docker compose logs -f --tail=100

migrate:
	docker compose exec api alembic upgrade head

shell-api:
	docker compose exec api sh

shell-db:
	docker compose exec postgres psql -U devops -d devops_agent

test:
	docker compose exec api pytest tests/ -v --tb=short

test-cov:
	docker compose exec api pytest tests/ -v --cov=app --cov-report=html

clean:
	docker compose down -v --remove-orphans
	docker system prune -f

generate-keys:
	@echo "MASTER_ENCRYPTION_KEY=$$(openssl rand -hex 32)"
	@echo "JWT_SECRET=$$(openssl rand -hex 64)"
	@echo "API_INTERNAL_SECRET=$$(openssl rand -hex 32)"
