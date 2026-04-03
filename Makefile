## TenderHack Makefile — quick commands for the Ubuntu server

.PHONY: up down logs migrate load-data build restart

# Start all services
up:
	docker compose up -d --build

# Stop all
down:
	docker compose down

# View live logs
logs:
	docker compose logs -f backend

# Run DB migrations
migrate:
	docker compose exec backend alembic upgrade head

# Load datasets from ./data/ directory
load-data:
	docker compose exec backend python -m scripts.load_data

# Build images without starting
build:
	docker compose build

# Restart backend only (after code change on server)
restart:
	docker compose restart backend

# Frontend dev server (local, not Docker)
frontend-dev:
	cd frontend && npm install && npm run dev
