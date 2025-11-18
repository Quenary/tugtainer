# Tugtainer Backend

It is the main backend that responds to frontend requests and performs container's checking/updating.

### Preparations

It is recommended to use python virtual environment `pip install python3-venv`.
You may also need following packages `pip3 install python-is-python3 python3-dev`.

### Run the app

- Run install.sh script to prepare python environment or do it manually
- In the root of the workspace, create an .env file with at least these variables

```bash
DB_URL=sqlite+aiosqlite:///./tugtainer.db
PASSWORD_FILE=password_hash
```

- Run the app with `python -m backend.dev` or `python -m backend.start`

### Migrations

Do not forget to create new migrations on models change with `alembic -c backend/alembic.ini revision --autogenerate -m "..."`
