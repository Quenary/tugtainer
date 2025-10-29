import subprocess
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
log_level = os.getenv("LOG_LEVEL", "WARNING").lower()


def run_migrations():
    print("Running Alembic migrations...")
    result = subprocess.run(
        [
            "alembic",
            "-c",
            os.path.join(os.path.dirname(__file__), "alembic.ini"),
            "upgrade",
            "head",
        ],
        check=False,
    )
    if result.returncode != 0:
        raise Exception("Alembic migrations failed. Exiting.")
    print("Alembic migrations completed.")


if __name__ == "__main__":
    run_migrations()
    uvicorn.run(
        "backend.app:app", host="0.0.0.0", port=8000, log_level=log_level
    )
