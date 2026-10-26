from fastapi import APIRouter, Depends, HTTPException, status

from backend.config import Config
from backend.exception import TugSelfUpdateError
from backend.modules.auth.auth_util import is_authorized_req
from shared.self_update.self_update_schemas import SelfUpdateState

from .self_update_schemas import SelfUpdateStatusResponseBody
from .self_update_util import get_current_state, start_self_update

self_update_router = APIRouter(
    prefix="/self_update",
    tags=["self_update"],
    dependencies=[Depends(is_authorized_req)],
)


@self_update_router.get(
    "/status",
    description="Whether self-update is allowed, and its current or last state",
    response_model=SelfUpdateStatusResponseBody,
)
def get_status() -> SelfUpdateStatusResponseBody:
    return SelfUpdateStatusResponseBody(
        allowed=Config.ALLOW_SELF_UPDATE,
        state=get_current_state(),
    )


@self_update_router.post(
    "/start",
    description="Update the app container with a newer image of its tag",
    response_model=SelfUpdateState,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start() -> SelfUpdateState:
    if not Config.ALLOW_SELF_UPDATE:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Self-update is disabled. Set ALLOW_SELF_UPDATE=true to enable it.",
        )
    try:
        return await start_self_update()
    except TugSelfUpdateError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
