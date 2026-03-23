.PHONY: up down logs migrate test shell api-shell worker-logs beat-logs

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest /app/tests -v --tb=short

shell:
	docker compose exec api sh

api-shell:
	docker compose exec api sh

worker-logs:
	docker compose logs -f worker --tail=100

beat-logs:
	docker compose logs -f beat --tail=50
