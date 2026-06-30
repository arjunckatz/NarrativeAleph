# Narrative Aleph

Narrative Aleph is a financial narrative intelligence engine. It ingests market-style text, stores evidence-bearing document chunks, and retrieves relevant passages that can later support market narrative extraction and explanation.

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
- Rule-based event extraction over document chunks.
- Event persistence with service-level duplicate suppression.
- In-memory narrative aggregation from extracted events.
- Minimal React + TypeScript placeholder frontend.
- Pytest and Ruff coverage for backend infrastructure, ingestion, chunking, hashing, search, event extraction, and narrative aggregation.

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
- `app/events/`: rule-based market event extraction and persistence.
- `app/narratives/`: in-memory event-to-narrative aggregation.
- `app/schemas/`: API/response schemas.

## Demo Quickstart

With Python 3.11+, Node.js, Docker, and Make installed:

```bash
cp .env.example .env
make setup
make db-up
make migrate
make ingest-sample
make extract-events
uvicorn app.main:app --reload --app-dir backend
```

Then query the running API:

```bash
curl "http://127.0.0.1:8000/api/search?q=export%20restrictions&ticker=NVDA&limit=5"
curl "http://127.0.0.1:8000/api/narratives?ticker=NVDA"
```

The sample corpus is synthetic. Repeating ingestion or event extraction skips rows already
persisted, so the demo commands are safe to rerun.

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
- `GET /api/search`
- `GET /api/narratives`

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

## Search API

The current search implementation is lexical-only over ingested `DocumentChunk` rows.

Example:

```text
GET /api/search?q=export%20restrictions&ticker=NVDA&limit=5
```

Supported query parameters:

- `q`
- `ticker`
- `source_type`
- `start_date`
- `end_date`
- `limit`

The endpoint returns matching document chunks with document metadata, chunk metadata, deterministic lexical scores, and text snippets.

Search currently supports:

- Query validation for query, ticker, source type, date range, and limit.
- Candidate retrieval from `DocumentChunk` joined with `Document`.
- Deterministic lexical scoring based on phrase match, title term matches, term frequency, and unique query terms matched.
- Snippet generation from chunk text.

Not yet implemented:

- Frontend search UI.
- Embeddings or vector search.
- Hybrid retrieval.

## Current Pipeline

Current local flow:

```text
documents -> chunks -> lexical search
documents -> chunks -> extracted events -> narrative candidates
```

Narrative aggregation currently groups persisted `Event` rows or event-like objects in memory and returns scored candidates with lightweight supporting event evidence. It does not write to `narratives`, `narrative_scores`, or `narrative_evidence` yet.

Example narrative API call: `GET /api/narratives?ticker=NVDA&start_date=2026-06-01`.

## Event Extraction

The current event extraction layer is rule-based and runs over stored `DocumentChunk` rows. It writes accepted matches to the existing `events` table and stores source metadata such as `document_id`, `chunk_id`, matched terms, document title, and source type.

Supported event types:

- `export_restriction`
- `demand_slowdown`
- `margin_pressure`
- `earnings_beat`
- `earnings_miss`
- `guidance_cut`

Run extraction after ingesting documents:

```bash
cd backend
python -m app.events.cli --ticker NVDA --min-confidence 0.7
```

Dry-run without writing events:

```bash
cd backend
python -m app.events.cli --dry-run
```

Equivalent Makefile helper:

```bash
make extract-events ARGS="--ticker NVDA --min-confidence 0.7"
```

There is no event API yet. Extraction is deterministic, local, and does not use LLMs, embeddings, or vector search.

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
python -m app.events.cli
python -m uvicorn app.main:app --reload
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
- Event API.
- Narrative persistence, ranking, or generation.
- ML models.
- Trading signals or price prediction.
- Frontend product workflows.
