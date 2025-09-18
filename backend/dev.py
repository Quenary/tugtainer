import subprocess


# def run_migrations():
#     print("Running Alembic migrations...")
#     result = subprocess.run(["alembic", "upgrade", "head"], check=False)
#     if result.returncode != 0:
#         print("Alembic migrations failed (continuing anyway)")
#     else:
#         print("Alembic migrations completed")


if __name__ == "__main__":
    # run_migrations()
    try:
        subprocess.run(["fastapi", "dev", "app/app.py", "--host=0.0.0.0"])
    except KeyboardInterrupt as e:
        print("Dev server shutdown by user")
