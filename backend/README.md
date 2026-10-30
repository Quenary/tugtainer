# Tugtainer Backend

The backend serves the UI and runs container check, update, health, and cleanup jobs.

The repo uses [uv](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer).

- Install uv and create a virtualenv with `uv venv`
- Activate it with `source .venv/bin/activate` (`.venv/scripts/activate` on Windows)
- Install dependencies with `uv sync --locked`
- Install hooks with `pre-commit install`
- Create `.env` in the repo root with at least:

```bash
DB_URL=sqlite+aiosqlite:///./tugtainer.db
PASSWORD_FILE=password_hash
AGENT_SECRET=CHANGE_ME!
```

- Run the backend with `uv run python -m backend.dev`, or the agent with `uv run python -m agent.dev`

Lint, types, and tests are in [CONTRIBUTING.md](../docs/CONTRIBUTING.md).

A model change needs a migration:

```bash
python -m alembic -c backend/alembic.ini revision --autogenerate -m "comment"
```
