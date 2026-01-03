.PHONY: dev backend-dev web-dev lint format test migrate makemigrations backend-lint web-lint backend-format web-format backend-test web-test

dev:
	docker-compose up -d

backend-dev:
	cd backend && (trap 'kill 0' INT TERM; \
		uvicorn app.main_api:app --reload --host 0.0.0.0 --port 8000 & \
		uvicorn app.main_worker:app --reload --host 0.0.0.0 --port 8001 & \
		wait)

web-dev:
	cd web && npm run dev

lint: backend-lint web-lint

format: backend-format web-format

test: backend-test web-test

migrate:
	cd backend && alembic upgrade head

makemigrations:
	cd backend && alembic revision --autogenerate -m "migration"

backend-lint:
	cd backend && ruff check . && black --check .

web-lint:
	cd web && npm run lint

backend-format:
	cd backend && ruff check . --fix && black .

web-format:
	cd web && npm run format

backend-test:
	cd backend && pytest

web-test:
	cd web && npm run lint
