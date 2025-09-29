# Backend part of Tugtainer

### Preparations

It is recommended to use python virtual environment `pip install python3-venv`.
You may also need following packages `pip3 install python-is-python3 python3-dev`.

### Run the app

- create .env file (next to that readme, in /backend directory) with at least this variables
```bash
DB_URL=sqlite+aiosqlite:///./tugtainer.db
PASSWORD_FILE=password_hash
```
- create venv `python -m venv venv`
- activate with `source venv/bin/activate` or `venv/scripts/activate`
- install deps `pip install -r requirements.txt`
- run app with ```python dev.py``` or ```python start.py```

### Migrations

Do not forget to create new migrations on models change with `alembic revision --autogenerate -m "some column add to some table"`