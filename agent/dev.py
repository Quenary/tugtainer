import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
log_level = os.getenv("LOG_LEVEL", "INFO").lower()

if __name__ == "__main__":
    try:
        uvicorn.run(
            "agent.app:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            reload_dirs=[
                os.path.dirname(__file__),
                os.path.join(
                    os.path.dirname(__file__), "..", "shared"
                ),
            ],
            log_level=log_level,
        )
    except KeyboardInterrupt as e:
        print("Dev server shutdown by user.")
