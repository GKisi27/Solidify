# ═══════════════════════════════════════════════════════════════
# SOLIDIFY - Makefile
# ═══════════════════════════════════════════════════════════════

.PHONY: help dev build test lint clean deploy-dev deploy-prod

# ─────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────
help:
	@echo "Solidify - Available Commands"
	@echo "────────────────────────────────────────"
	@echo "  make dev          Start development environment"
	@echo "  make build        Build all Docker images"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run linters"
	@echo "  make clean        Clean up containers and volumes"
	@echo "  make deploy-dev   Deploy to development"
	@echo "  make deploy-prod  Deploy to production"

# ─────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────
dev:
	docker compose up -d
	@echo "✓ Development environment started"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

stop:
	docker compose down
	@echo "✓ Development environment stopped"

logs:
	docker compose logs -f

# ─────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────
build:
	docker compose build
	@echo "✓ All images built"

build-prod:
	docker compose -f docker-compose.prod.yml build
	@echo "✓ Production images built"

# ─────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────
test:
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "Running worker tests..."
	cd worker && pytest

test-backend:
	cd backend && pytest --cov=app

test-frontend:
	cd frontend && npm test

test-e2e:
	cd frontend && npm run test:e2e

# ─────────────────────────────────────────────────────────────────
# Linting
# ─────────────────────────────────────────────────────────────────
lint:
	@echo "Linting backend..."
	cd backend && ruff check .
	@echo "Linting frontend..."
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format

# ─────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────
clean:
	docker compose down -v --remove-orphans
	docker system prune -f
	@echo "✓ Cleanup complete"

# ─────────────────────────────────────────────────────────────────
# Deployment
# ─────────────────────────────────────────────────────────────────
deploy-dev:
	@echo "Deploying to development..."
	# Add deployment commands here

deploy-prod:
	@echo "Deploying to production..."
	# Add deployment commands here
