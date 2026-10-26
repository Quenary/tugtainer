from pydantic import BaseModel

from shared.self_update.self_update_schemas import SelfUpdateState


class SelfUpdateStatusResponseBody(BaseModel):
    allowed: bool
    # Current self-update, or the result of the last one
    # since the app started
    state: SelfUpdateState | None = None
