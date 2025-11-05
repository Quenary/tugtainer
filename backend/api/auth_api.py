from fastapi import (
    APIRouter,
    Depends,
    Response,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse
from backend.core.auth.auth_provider_chore import (
    AUTH_OIDC_PROVIDER,
    AUTH_PASSWORD_PROVIDER,
    is_authorized,
)
from backend.helpers.delay_to_minimum import delay_to_minimum
from backend.schemas.auth_schema import PasswordSetRequestBody


router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


# For now endpoints are tied to a specific provider
# Maybe they should be more universal


@router.post(path="/login")
@delay_to_minimum(1)
async def login(request: Request, response: Response):
    return await AUTH_PASSWORD_PROVIDER.login(request, response)


@router.post(path="/refresh")
async def refresh(request: Request, response: Response):
    return await AUTH_PASSWORD_PROVIDER.refresh(request, response)


@router.post(path="/logout")
async def logout(request: Request, response: Response):
    return await AUTH_PASSWORD_PROVIDER.logout(request, response)


@router.get(
    path="/is_authorized",
    description="Check if session is authorized",
    response_model=bool,
)
def is_authorized_req(_=Depends(is_authorized)):
    return PlainTextResponse(status_code=status.HTTP_200_OK)


@router.post(
    path="/set_password",
    description="Set password for web UI. Password can be set only if password is not set yet or if user is authorized.",
)
def set_password(request: Request, payload: PasswordSetRequestBody):
    return AUTH_PASSWORD_PROVIDER.set_password(request, payload)


@router.get(
    path="/is_password_set",
    description="Check if password is set",
    response_model=bool,
)
def is_password_set() -> bool:
    return AUTH_PASSWORD_PROVIDER.is_password_set()


@router.get(
    path="/oidc/enabled",
    description="Check if OIDC authentication is enabled",
    response_model=bool,
)
async def oidc_enabled() -> bool:
    return await AUTH_OIDC_PROVIDER.is_enabled()


@router.get(
    path="/oidc/login",
    description="Initiate OIDC login flow",
)
async def oidc_login(request: Request, response: Response):
    return await AUTH_OIDC_PROVIDER.login(request, response)


@router.get(
    path="/oidc/callback",
    description="Handle OIDC callback",
)
async def oidc_callback(
    request: Request,
    response: Response,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    return await AUTH_OIDC_PROVIDER.oidc_callback(
        request, response, code, state, error
    )
