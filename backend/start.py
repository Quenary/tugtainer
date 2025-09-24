import subprocess
import uvicorn


def run_migrations():
    print("Running Alembic migrations...")
    result = subprocess.run(["alembic", "upgrade", "head"], check=False)
    if result.returncode != 0:
        raise Exception("Alembic migrations failed. Exiting.")
    print("Alembic migrations completed.")


if __name__ == "__main__":
    run_migrations()
    uvicorn.run("app.app:app", host="0.0.0.0", port=8000)
