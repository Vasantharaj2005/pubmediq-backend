.PHONY: help dev test lint format migrate seed docker-up docker-down clean install

# ----------------------------
# Help
# ----------------------------
help:
	@echo ""
	@echo "  PubMedIQ Backend Makefile"
	@echo "  ========================"
	@echo ""
	@echo "  Setup:"
	@echo "    make install       Install all dependencies"
	@echo "    make seed          Create DB tables + seed test data"
	@echo ""
	@echo "  Development:"
	@echo "    make dev           Run FastAPI dev server (with reload)"
	@echo "    make worker        Run ingestion background worker"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate       Run Alembic migrations"
	@echo "    make migrate-undo  Downgrade last migration"
	@echo "    make revision msg='message'  Create new migration"
	@echo ""
	@echo "  Testing:"
	@echo "    make test          Run all tests"
	@echo "    make test-unit     Run unit tests only"
	@echo "    make test-api      Run API tests only"
	@echo "    make test-cov      Run tests with coverage report"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint          Run ruff linter"
	@echo "    make format        Run ruff formatter"
	@echo "    make typecheck     Run mypy type checker"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up     Start all services (PostgreSQL, Redis)"
	@echo "    make docker-down   Stop all services"
	@echo "    make docker-logs   Tail docker logs"
	@echo ""
	@echo "  Ingestion:"
	@echo "    make create-index  Create Pinecone vector index"
	@echo "    make ingest q='alzheimer biomarkers'  Ingest PubMed articles"
	@echo ""

# ----------------------------
# Setup
# ----------------------------
install:
	pip install -r requirements.txt

# ----------------------------
# Development Server
# ----------------------------
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

worker:
	python -m app.workers.ingestion_worker

# ----------------------------
# Database Migrations
# ----------------------------
migrate:
	alembic upgrade head

migrate-undo:
	alembic downgrade -1

revision:
	alembic revision --autogenerate -m "$(msg)"

# ----------------------------
# Seeding
# ----------------------------
seed:
	python scripts/seed_database.py

# ----------------------------
# Testing
# ----------------------------
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-api:
	pytest tests/api/ -v

test-agents:
	pytest tests/agents/ -v

test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# ----------------------------
# Code Quality
# ----------------------------
lint:
	ruff check app/ tests/ scripts/

format:
	ruff format app/ tests/ scripts/

typecheck:
	mypy app/

# ----------------------------
# Docker
# ----------------------------
docker-up:
	docker-compose -f deployment/docker-compose.yml up -d

docker-down:
	docker-compose -f deployment/docker-compose.yml down

docker-logs:
	docker-compose -f deployment/docker-compose.yml logs -f

docker-build:
	docker build -f deployment/Dockerfile -t pubmediq-backend:latest .

# ----------------------------
# Ingestion
# ----------------------------
create-index:
	python scripts/create_index.py

ingest:
	python scripts/ingest_pubmed.py --query "$(q)"

# ----------------------------
# Cleanup
# ----------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
