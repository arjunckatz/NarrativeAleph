# Narrative Alpha

Narrative Alpha is a financial narrative intelligence engine. It ingests market-style text, stores evidence-bearing document chunks, and retrieves relevant passages that can later support market narrative extraction and explanation.

It is not a trading bot, stock price predictor, or generic finance dashboard.

## Current Status

Implemented:

- FastAPI backend with `GET /health` and `GET /api/version`.
- SQLAlchemy 2.x data model with Alembic migrations.
- Postgres local development via Docker Compose.
- Local JSON document ingestion from `data/sample_documents.json`.
- Deterministic document hashing and idempotent ingestion.
- Word-safe overlapping document chunking.
- Basic lexical search service over `DocumentChunk` data.
- Deterministic lexical scoring and result snippets.
- Minimal React + TypeScript placeholder frontend.
- Pytest and Ruff coverage for backend infrastructure, ingestion, chunking, hashing, and search.

## Architecture

- `backend/`: FastAPI application, SQLAlchemy models, Alembic migrations, ingestion utilities, and search modules.
- `frontend/`: Vite React + TypeScript placeholder app.
- `data/`: local synthetic sample documents for ingestion and search development.
- `docker-compose.yml`: local Postgres service.
- `Makefile`: common setup, migration, ingestion, test, lint, and frontend commands.

Key backend modules:

- `app/models/`: database entities such as `Document`, `DocumentChunk`, `Event`, `Narrative`, and related score/evidence tables.
- `app/ingestion/`: local JSON loading, validation, hashing, chunking, and database insertion.
- `app/search/`: search parameter validation, lexical candidate retrieval, deterministic scoring, and snippet generation.
- `app/schemas/`: API/response schemas.

## Backend Setup

Create and activate a Python 3.11+ virtual environment, then install backend dependencies:

```bash
make setup-backend
```

Run backend checks:

```bash
make lint
make test-backend
```

Run the API locally:

```bash
uvicorn app.main:app --reload --app-dir backend
```

Current HTTP endpoints:

- `GET /health`
- `GET /api/version`

The search service exists as backend application code, but no public search API route has been wired yet.

## Frontend Setup

Install frontend dependencies:

```bash
make setup-frontend
```

Run the placeholder frontend:

```bash
make frontend-dev
```

Build the frontend:

```bash
make frontend-build
```

The frontend is intentionally minimal and does not yet expose ingestion, search, ranking, or narrative workflows.

## Database And Migrations

Copy `.env.example` to `.env` and adjust values if needed.

Start Postgres:

```bash
make db-up
```

Run migrations:

```bash
make migrate
```

Stop local services:

```bash
make db-down
```

Documents include a deterministic `content_hash` and a uniqueness constraint on source type, ticker, source name, and hash to prevent duplicate ingestion. A Postgres-only partial unique index on non-null document URLs is intentionally deferred until URL canonicalization rules are clear.

## Sample Ingestion

The sample corpus lives at `data/sample_documents.json`. It contains clearly synthetic finance documents around NVDA export restrictions, AI datacenter demand, margin pressure, semiconductor selloff, cloud capex, TSLA delivery misses, and AAPL China demand.

Run sample ingestion after Postgres is running and migrations have been applied:

```bash
make ingest-sample
```

Equivalent direct command:

```bash
cd backend
python -m app.ingestion.cli ../data/sample_documents.json
```

Ingestion validates the full file before writing anything. Missing required fields, invalid `source_type`, invalid `published_at`, or empty `raw_text` stop the run without partial ingestion.

## Search Status

The current search implementation is backend-only and lexical-only.

Supported in code:

- `SearchParams` validation for query, ticker, source type, date range, and limit.
- Candidate retrieval from `DocumentChunk` joined with `Document`.
- Optional ticker, source type, start date, end date, and limit handling.
- Deterministic lexical scoring based on phrase match, title term matches, term frequency, and unique query terms matched.
- Snippet generation from chunk text.

Not yet implemented:

- Public `/api/search` route.
- Frontend search UI.
- Embeddings or vector search.
- Hybrid retrieval.

## Windows Or No `make` Fallback

If `make` is unavailable, run the underlying commands directly:

```powershell
python -m pip install -e ".[dev]"
cd frontend
npm.cmd install
cd ..
docker compose up -d postgres
cd backend
python -m alembic upgrade head
python -m app.ingestion.cli ../data/sample_documents.json
cd ..
python -m ruff check .
python -m pytest
cd frontend
npm.cmd run build
```

Use `npm` instead of `npm.cmd` on macOS/Linux shells.

## Intentionally Not Built Yet

- Real news, filing, transcript, or market data integrations.
- Embeddings.
- Vector search.
- Event extraction.
- Narrative ranking.
- ML models.
- Trading signals or price prediction.
- Frontend product workflows.
