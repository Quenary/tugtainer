"""
Self-update helper.
Started by the backend as a one-shot container from the new image:
python -m shared.self_update /tugtainer/self_update/plan.json
It must not import anything from backend/.
"""

import logging
import sys
from pathlib import Path

from .self_update_docker import WhalesSelfUpdateDocker
from .self_update_runner import run_self_update
from .self_update_schemas import ESelfUpdateStatus


def main(argv: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="SELF-UPDATE - %(levelname)s - %(name)s: %(message)s",
    )
    if len(argv) != 2:
        logging.error("Usage: python -m shared.self_update <plan.json>")
        return 2
    state = run_self_update(WhalesSelfUpdateDocker(), Path(argv[1]))
    if state and state.status == ESelfUpdateStatus.SUCCEEDED:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
