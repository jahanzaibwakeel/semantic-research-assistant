.PHONY: dev prod down logs migrate test build backup maintenance

dev:
	docker compose up --build

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec backend alembic upgrade head

test:
	cd backend && python -m unittest discover tests

build:
	cd frontend && npm run build

backup:
	powershell -ExecutionPolicy Bypass -File scripts/backup.ps1

maintenance:
	powershell -ExecutionPolicy Bypass -File scripts/maintenance.ps1
