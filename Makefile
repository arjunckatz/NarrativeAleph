.PHONY: setup setup-backend setup-frontend db-up db-down migrate revision ingest-sample extract-events test-backend lint format frontend-dev frontend-build test

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

setup-backend:
	$(PIP) install -e ".[dev]"

setup-frontend:
	cd frontend && npm install

setup: setup-backend setup-frontend

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

migrate:
	cd backend && $(PYTHON) -m alembic upgrade head

revision:
	cd backend && $(PYTHON) -m alembic revision --autogenerate -m "$(msg)"

ingest-sample:
	cd backend && $(PYTHON) -m app.ingestion.cli ../data/sample_documents.json

extract-events:
	cd backend && $(PYTHON) -m app.events.cli $(ARGS)

test-backend:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

test: lint test-backend frontend-build
