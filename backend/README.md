# Tugtainer Backend

It is the main backend that responds to frontend requests and performs container's checking/updating.

This repository uses [uv package manager](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

- Install uv
- Create venv with `uv venv`
- Activate venv with `source .venv/bin/activate` or `.venv/scripts/activate`
- Install all deps with `uv sync --locked`
- In the root of the workspace, create an .env file with at least these variables
    ```bash
    DB_URL=sqlite+aiosqlite:///./tugtainer.db
    PASSWORD_FILE=password_hash
    ```
- Run the backend with `python -m backend.dev` or agent with `python -m agent.dev`

### Migrations

Do not forget to create new migrations on models change with `alembic -c backend/alembic.ini revision --autogenerate -m "..."`

### Useful things

- Clear python cache with `find . | grep -E "(/**pycache**$|\.pyc$|\.pyo$)" | xargs rm -rf`