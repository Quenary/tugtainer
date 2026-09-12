# AGENTS.md — Guidelines for AI Agents

For general contributing workflow and commit standards, see [docs/CONTRIBUTING.md](file:///home/quenary/repos/tugtainer/docs/CONTRIBUTING.md).

## 1. Architecture Overview

- **`backend/`** (FastAPI + SQLAlchemy 2.0 async + SQLite `tugtainer.db`):
  - `backend/app.py`: FastAPI entrypoint, `lifespan()` startup and shutdown.
  - `backend/const.py`: Global constants, default crontab expressions.
  - `backend/core/cron_manager.py`: Background cron manager (`aiocron`).
  - `backend/core/agent_client.py`: `AgentClientManager` HTTP client for Docker host agents.
  - `backend/core/jobs/`: Background job subsystems (`check/`, `update/`, `health/`, `cleanup/`).
  - `backend/modules/`: Domain modules with models, routers, and schemas (`containers/`, `hosts/`, `health/`, `settings/`, `public/`, `auth/`, `images/`).
  - `backend/alembic/`: SQLite database migrations.
- **`agent/`**: Lightweight daemon on Docker hosts (`python-on-whales` + FastAPI).
- **`shared/`**: Common Pydantic schemas (`shared/schemas/`) and utilities shared between backend and agent.
- **`frontend/`**: Angular SPA with PrimeNG.
- **`tests/`**: Dockerized Playwright E2E and integration tests.

## 2. Dev & Validation Commands

### Local Dev

```bash
# Backend: source .venv/bin/activate && python -m backend.dev
# Agent:   source .venv/bin/activate && python -m agent.dev
# Frontend: cd frontend && npm start
```

### Pre-commit Quality Checks

```bash
# Python lint & format
uv run ruff check --fix
uv run ruff format

# Python type checking
uv run mypy agent backend shared

# Python unit tests (PYTHONPATH=. is mandatory!)
PYTHONPATH=. uv run pytest backend/
# Single test file:
PYTHONPATH=. uv run pytest backend/core/jobs/cleanup/test_cleanup_containers.py

# Frontend checks
npm --prefix frontend run lint
npm --prefix frontend run prettier-check

# Integration / E2E (with cleanup)
npm --prefix tests run test:all
# Integration / E2E (if test app is already started)
npm --prefix tests run test:docker
```

## 3. Critical Gotchas & Patterns

1. **`PYTHONPATH=.` for pytest**:
   Packages `backend`, `agent`, and `shared` are top-level imports. Direct invocation without `PYTHONPATH=.` causes `ModuleNotFoundError`.
