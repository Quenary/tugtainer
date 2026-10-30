# AGENTS.md — Guidelines for AI Agents

This guide is the source of general rules for AI agents in this repository. Package guides add rules on top of it and do not repeat it.

## Read before editing

Before proposing a plan or editing code, read every document below that applies to the task.

- Repo workflow, commits, checks — [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- Backend — [backend/AGENTS.md](backend/AGENTS.md)
- Docker host agent — [agent/AGENTS.md](agent/AGENTS.md)
- Frontend — [frontend/AGENTS.md](frontend/AGENTS.md)
- Security — [docs/SECURITY.md](docs/SECURITY.md)
- Feature behavior — the matching file in `docs/` (`AUTH.md`, `CHECK_AND_UPDATE.md`, `HOOKS.md`, `SELF_UPDATE.md`, and the others)

When a change affects behavior, configuration, architecture, or contracts between packages, update the matching documentation in the same change. Follow [Documentation](docs/CONTRIBUTING.md#documentation).

General and cross-cutting docs live in `docs/`. Package docs live beside the code (`backend/README.md`, `agent/README.md`, `frontend/README.md`). The root `README.md` is the product overview. Extend the matching doc rather than duplicating long explanations in comments only.

## Architecture

- **`backend/`** (FastAPI + SQLAlchemy 2.0 async + SQLite `tugtainer.db`):
  - `backend/app.py`: FastAPI entrypoint, `lifespan()` startup and shutdown.
  - `backend/const.py`: Global constants, default crontab expressions.
  - `backend/core/cron_manager.py`: Background cron manager (`aiocron`).
  - `backend/core/agent_client.py`: `AgentClientManager` HTTP client for Docker host agents.
  - `backend/core/jobs/`: Background job subsystems (`check/`, `update/`, `health/`, `cleanup/`).
  - `backend/modules/`: Domain modules with models, routers, and schemas (`containers/`, `hosts/`, `health/`, `settings/`, `public/`, `auth/`, `images/`, `self_update/`).
  - `backend/alembic/`: SQLite database migrations.
- **`agent/`**: Lightweight daemon on Docker hosts (`python-on-whales` + FastAPI).
- **`shared/`**: Common Pydantic schemas (`shared/schemas/`) and utilities shared between backend and agent. `shared/self_update/` is the self-update helper run from the new app image; it imports nothing from `backend/`.
- **`frontend/`**: Angular SPA. UI primitives come from `@openng/optimus-ui`.
- **`tests/`**: Dockerized Playwright E2E and integration tests.

## Code principles

Apply a principle only when it makes this change simpler. Do not reshape the code just to satisfy it.

- **SOLID, KISS, DRY, YAGNI.** Follow the design already in the touched code. Prefer a clear, small change over a new abstraction or behavior the task does not need.
- **Scope.** Make the smallest change that fully solves the problem. Do not refactor unrelated code.

## Python

These rules apply to `backend/`, `agent/`, and `shared/`. Ruff and mypy are configured in the repo `pyproject.toml` (Ruff selects E, F, I, B, UP; mypy allows missing imports and unset optionals). Match the surrounding file.

- Prefer `list[str]`, `str | None`, and `Final`.
- Log with `logging`. Do not add `print` outside `dev.py`.
- Import `backend`, `agent`, and `shared` as top-level packages. Run pytest from the repo root with `PYTHONPATH=.`; without it pytest raises `ModuleNotFoundError`.

## Tests

- Cover the important behavior of the change. Parameterize cases that differ by inputs and expected results. Do not add tests for trivial getters.
- A bug fix gets a test that fails before the fix when that is practical.
- Python tests sit next to the code as `test_*.py`. Async tests use `@pytest.mark.asyncio`. Patch with `pytest-mock`.
- How a package sets up its tests is in that package's guide.

## Checks

After substantive edits, run the checks for the touched packages. Commands are in [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Commit messages follow Conventional Commits (see Commits there).

No AI attribution anywhere: commit messages, PR titles, and descriptions must not contain `Co-authored-by` trailers, `@cursor` or other agent mentions, or "Generated with …" lines, and an AI tool is never listed as an author. The agent is an assistant; the human author is responsible for the change.
