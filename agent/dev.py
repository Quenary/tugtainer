import subprocess
import os

if __name__ == "__main__":
    try:
        subprocess.run(
            [
                "fastapi",
                "dev",
                os.path.join(os.path.dirname(__file__), "app.py"),
                "--host=0.0.0.0",
                "--port=8001",
            ]
        )
    except KeyboardInterrupt as e:
        print("Dev server shutdown by user.")
