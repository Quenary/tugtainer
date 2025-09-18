import subprocess
import uvicorn
import os
import requests

# def run_migrations():
#     print("Running Alembic migrations...")
#     result = subprocess.run(["alembic", "upgrade", "head"], check=False)
#     if result.returncode != 0:
#         print("Alembic migrations failed (continuing anyway)")
#     else:
#         print("Alembic migrations completed")


if __name__ == "__main__":
    # run_migrations()
    log_level = os.getenv("LOG_LEVEL") or "warning"
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000, log_level=log_level)
