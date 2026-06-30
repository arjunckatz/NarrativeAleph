# Narrative Aleph

Narrative Aleph is a financial narrative intelligence engine. Given local market-style documents, it ingests and chunks text, retrieves lexical evidence, extracts deterministic market events, aggregates those events into scored narratives, and returns an evidence-backed explanation.

It is not a trading bot, stock price predictor, or generic finance dashboard.

## Current Status

The project currently supports a local demo flow:

- Local synthetic corpus in `data/sample_documents.json`.
- Deterministic document hashing, deduplication, and word-safe chunking.
- Lexical search over stored `DocumentChunk` rows with scoring and snippets.
- Rule-based event extraction over chunks, persisted to the `events` table.
- Narrative aggregation and deterministic scoring from stored events.
- Evidence-backed `/api/explain` endpoint built from narrative candidates.
- Minimal React + TypeScript placeholder frontend.

No real market/news APIs, embeddings, LLMs, ML ranking, or frontend workflows are implemented yet.

## Architecture

- `backend/`: FastAPI app, SQLAlchemy models, Alembic migrations, ingestion, search, event extraction, narratives, and explain services.
- `frontend/`: Vite React + TypeScript placeholder app.
- `data/`: clearly synthetic finance documents for local development.
- `docker-compose.yml`: local Postgres service.
- `Makefile`: common setup, migration, ingestion, extraction, lint, test, and build commands.

Key backend modules:

- `app/ingestion/`: JSON validation, hashing, chunking, and idempotent insertion.
- `app/search/`: lexical retrieval, deterministic scoring, and snippets.
- `app/events/`: rule-based event extraction, persistence service, and CLI.
- `app/narratives/`: event-to-narrative mapping, aggregation, scoring, and supporting evidence.
- `app/explain/`: deterministic explanation summary over top scored narratives.

## Backend Pipeline

```text
sample JSON documents
  -> validated Document rows
  -> overlapping DocumentChunk rows
  -> lexical search evidence

DocumentChunk rows
  -> deterministic event extraction
  -> persisted Event rows
  -> narrative aggregation/scoring
  -> evidence-backed explain response
```

The current narrative/explain layer is read-only over stored `Event` rows. It does not write to `narratives`, `narrative_scores`, or `narrative_evidence`.

## Quickstart

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
curl "http://127.0.0.1:8000/api/explain?ticker=NVDA&limit=3"
```

The sample corpus is synthetic. Repeating ingestion or event extraction skips rows already persisted, so the demo commands are safe to rerun.

## Demo Workflow

1. Start Postgres: `make db-up`
2. Apply migrations: `make migrate`
3. Ingest sample documents: `make ingest-sample`
4. Extract events: `make extract-events`
5. Start the API: `uvicorn app.main:app --reload --app-dir backend`
6. Inspect search, narratives, and explain responses with the example URLs below.

## API Examples

Search lexical evidence:

```text
GET /api/search?q=export%20restrictions&ticker=NVDA&limit=5
```

Get scored narrative candidates:

```text
GET /api/narratives?ticker=NVDA&start_date=2026-06-01
```

Get a deterministic explanation summary:

```text
GET /api/explain?ticker=NVDA&limit=3
```

Current HTTP endpoints:

- `GET /health`
- `GET /api/version`
- `GET /api/search`
- `GET /api/narratives`
- `GET /api/explain`

## Search

Search is lexical-only over ingested `DocumentChunk` rows. It supports:

- `q`
- `ticker`
- `source_type`
- `start_date`
- `end_date`
- `limit`

Results include document metadata, chunk metadata, deterministic lexical score, and a text snippet. Embeddings, vector search, and hybrid retrieval are intentionally deferred.

## Event Extraction

Event extraction is deterministic and rule-based. It runs over stored chunks and writes accepted matches to the existing `events` table with source metadata such as `document_id`, `chunk_id`, document title, source type, and matched terms.

Supported event types:

- `export_restriction`
- `demand_slowdown`
- `margin_pressure`
- `earnings_beat`
- `earnings_miss`
- `guidance_cut`

Run extraction after ingesting documents:

```bash
make extract-events ARGS="--ticker NVDA --min-confidence 0.7"
```

Dry-run without writing events:

```bash
cd backend
python -m app.events.cli --dry-run
```

There is no event API yet.

## Setup Details

Install backend dependencies:

```bash
make setup-backend
```

Install frontend dependencies:

```bash
make setup-frontend
```

Run checks:

```bash
make lint
make test-backend
make frontend-build
```

Database commands:

```bash
make db-up
make migrate
make db-down
```

The frontend is intentionally minimal and does not expose ingestion, search, narrative, or explain workflows yet.

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
- Embeddings or vector search.
- LLM-generated explanations.
- ML ranking models.
- Price movement integration.
- Event API.
- Narrative persistence to `NarrativeScore` or `NarrativeEvidence`.
- Trading signals or price prediction.
- Frontend product workflows.
