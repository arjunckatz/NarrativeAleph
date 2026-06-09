# Narrative Alpha Backend

FastAPI backend for the Narrative Alpha foundation.

## Run

```bash
uvicorn app.main:app --reload --app-dir backend
```

## Test

```bash
pytest
```

## Migrate

```bash
cd backend
alembic upgrade head
```
