import subprocess
import os


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
        subprocess.run(
            [
                "fastapi",
                "dev",
                os.path.join(os.path.dirname(__file__), "app.py"),
                "--host=0.0.0.0",
                "--port=8000",
            ]
        )
    except KeyboardInterrupt as e:
        print("Dev server shutdown by user.")
