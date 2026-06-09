# Narrative Alpha Phases 0-1 Plan

## Architecture Decisions

- Monorepo with `backend/` FastAPI and `frontend/` React + TypeScript.
- SQLAlchemy 2.x ORM instead of SQLModel for explicit production-style persistence.
- Alembic migrations from Phase 1 onward.
- Postgres for local infrastructure through Docker Compose.
- Keep Phase 0 and 1 boring: health/version API, database models, migrations, tests, and docs only.

## API Boundaries

Implemented in Phases 0-1:

- `GET /health`
- `GET /api/version`

Deferred:

- ingestion
- search
- event extraction
- narrative ranking
- asset price upload
- frontend-backend workflows

## Phase 0 Checklist

- Root monorepo files.
- FastAPI app with health and version endpoints.
- Pytest coverage for both endpoints.
- Ruff config.
- Docker Compose Postgres.
- Minimal Vite React + TypeScript placeholder.
- Local setup instructions.

## Phase 1 Checklist

- SQLAlchemy models for companies, prices, documents, chunks, events, narratives, evidence, and scores.
- Alembic initial schema migration.
- Metadata and migration tests.
- JSON storage for metadata and nullable embeddings.
- No retrieval, extraction, scoring, or ML behavior.

## Testing Checklist

- `make lint`
- `make test-backend`
- `make frontend-build`
- `make test`

## Commit Checkpoints

- `chore: scaffold narrative alpha monorepo`
- `feat(api): add health and version endpoints`
- `test(api): cover health and version endpoints`
- `chore(dev): add docker compose postgres and env template`
- `chore(frontend): scaffold react typescript app`
- `chore(tooling): add make targets and ruff config`
- `feat(db): add sqlalchemy models for narrative alpha core entities`
- `chore(db): add alembic initial schema migration`
- `test(db): cover model metadata and migration smoke test`
- `docs: add local setup instructions for phases 0 and 1`
