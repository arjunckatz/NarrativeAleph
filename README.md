# Narrative Alpha

Narrative Alpha is a portfolio-grade fintech/AI foundation for financial narrative intelligence. Given a ticker and date range in later phases, it will retrieve evidence, extract market-moving events, rank likely narratives, and explain asset price movement with citations.

This project is not a trading bot, stock price predictor, or generic finance dashboard.

## Phase Scope

Phases 0 and 1 establish only the repo, API shell, local database, ORM models, migrations, and tests.

Out of scope for these phases:

- ingestion
- search
- embeddings
- event extraction
- narrative ranking
- frontend product workflows

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

## Backend

Run the API locally:

```bash
uvicorn app.main:app --reload --app-dir backend
```

Endpoints:

- `GET /health`
- `GET /api/version`

## Frontend

Run the placeholder frontend:

```bash
make frontend-dev
```

The frontend is intentionally minimal until API/data contracts exist.
