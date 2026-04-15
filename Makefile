# Solidify Makefile
# Convenience commands for development and deployment

.PHONY: help dev backend frontend celery flower seed-users build up down clean test

help:
	@echo "Solidify Makefile Commands"
	@echo "=========================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start all services (backend, frontend, celery, redis)"
	@echo "  make backend      - Start backend API server only"
	@echo "  make frontend     - Start frontend dev server only"
	@echo "  make celery       - Start Celery worker only"
	@echo "  make flower       - Start Flower monitoring UI"
	@echo ""
	@echo "Database:"
	@echo "  make seed-users   - Add default users to database"
	@echo ""
	@echo "Docker:"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start all Docker containers"
	@echo "  make down         - Stop all Docker containers"
	@echo "  make clean        - Remove all Docker containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo ""

# Development commands
dev:
	docker-compose up -d

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

celery:
	python scripts/start_celery_worker.py

flower:
	celery -A worker.celery_app flower --port=5555

# Database utilities
seed-users:
	python scripts/add_user.py

# Docker commands
build:
	docker-compose build

dev-build:
	docker compose -f docker-compose.dev.yml up -d --build

up:
	docker-compose up -d
	@echo ""
	@echo "Services started:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Flower:   http://localhost:5555"
	@echo ""

down:
	docker-compose down

clean:
	docker-compose down -v
	@echo "Cleaned up containers and volumes"

# Testing
test:
	cd backend && pytest tests/
	cd worker && pytest tests/

