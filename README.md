# Narrative Alpha

Narrative Alpha is a portfolio-grade fintech/AI foundation for financial narrative intelligence. Given a ticker and date range in later phases, it will retrieve evidence, extract market-moving events, rank likely narratives, and explain asset price movement with citations.

This project is not a trading bot, stock price predictor, or generic finance dashboard.

## Phase Scope

Phases 0 and 1 establish the repo, API shell, local database, ORM models, migrations, and tests. Phase 2 adds local JSON document ingestion and deterministic chunking only.

Out of scope for these phases:

- search
- embeddings
- event extraction
- narrative ranking
- frontend product workflows
- real news, filing, transcript, or market data APIs

## Local Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install backend dependencies:

```bash
make setup-backend
```

3. Install frontend dependencies:

```bash
make setup-frontend
```

4. Copy `.env.example` to `.env` and adjust values if needed.
5. Start Postgres:

```bash
make db-up
```

6. Run migrations:

```bash
make migrate
```

7. Run checks:

```bash
make test
```

### Windows or No `make` Fallback

If `make` is unavailable, run the underlying commands directly:

```powershell
python -m pip install -e ".[dev]"
cd frontend
npm.cmd install
cd ..
docker compose up -d postgres
cd backend
python -m alembic upgrade head
cd ..
python -m ruff check .
python -m pytest
cd frontend
npm.cmd run build
```

Use `npm` instead of `npm.cmd` on macOS/Linux shells.

## Backend

Run the API locally:

```bash
uvicorn app.main:app --reload --app-dir backend
```

Endpoints:

- `GET /health`
- `GET /api/version`

## Local Document Ingestion

Phase 2 supports local JSON ingestion only. It does not call real news, filing, transcript, market data, or embedding APIs.

Run the sample ingestion after Postgres is running and migrations have been applied:

```bash
make ingest-sample
```

Equivalent direct command:

```bash
cd backend
python -m app.ingestion.cli ../data/sample_documents.json
```

The ingestion command validates the full file before writing anything. Missing required fields, invalid `source_type`, invalid `published_at`, or empty `raw_text` stop the run without partial ingestion.

The local sample file lives at `data/sample_documents.json` and contains clearly synthetic finance documents around NVDA export restrictions, AI datacenter demand, margin pressure, semiconductor selloff, cloud capex, TSLA delivery misses, and AAPL China demand.

## Frontend

Run the placeholder frontend:

```bash
make frontend-dev
```

The frontend is intentionally minimal until API/data contracts exist.

## Phase 1 Schema Notes

Documents include a `content_hash` and a uniqueness constraint on source type, ticker, source name, and hash to prevent duplicate ingestion later. A Postgres-only partial unique index on non-null document URLs is intentionally deferred until ingestion requirements make URL canonicalization rules clear.
