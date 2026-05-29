# Quiz Service Backend

A FastAPI quiz service with real-time game play over WebSocket and SSE.

## Stack

- **FastAPI** + Uvicorn
- **PostgreSQL** via SQLAlchemy (async) + Alembic
- **Redis** for pub/sub and real-time state
- **uv** for dependency management

## Run

```bash
docker compose up --build
```

The API is served at `http://localhost:8000` (docs at `/docs`).

## Local development

```bash
uv sync --extra dev
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
uv run pytest
```
