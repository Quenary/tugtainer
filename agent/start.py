import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
log_level = os.getenv("LOG_LEVEL", "WARNING").lower()


if __name__ == "__main__":
    uvicorn.run(
        "agent.app:app", host="0.0.0.0", port=8001, log_level=log_level
    )
