import os
import subprocess

import uvicorn
from dotenv import load_dotenv

load_dotenv()
log_level = os.getenv("LOG_LEVEL", "INFO").lower()


def run_migrations():
    print("Running Alembic migrations...")
    result = subprocess.run(
        [
            "alembic",
            "-c",
            os.path.join(os.path.dirname(__file__), "alembic.ini"),
            "upgrade",
            "head",
        ]
    )
    if result.returncode != 0:
        raise Exception("Alembic migrations failed. Exiting.")
    print("Alembic migrations completed.")


if __name__ == "__main__":
    run_migrations()
    try:
        uvicorn.run(
            "backend.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[
                os.path.dirname(__file__),
                os.path.join(
                    os.path.dirname(__file__), "..", "shared"
                ),
            ],
            log_level=log_level,
        )
    except KeyboardInterrupt:
        print("Dev server shutdown by user.")
