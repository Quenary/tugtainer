from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse, RedirectResponse
from backend.config import Config
from backend.core.auth.auth_provider import AuthProvider
from backend.core.auth.auth_provider_chore import (
    AUTH_PASSWORD_PROVIDER,
    auth_provider_by_name,
    active_auth_provider,
    is_authorized,
)
from backend.exception import TugNoAuthProviderException
from backend.helpers.delay_to_minimum import delay_to_minimum
from backend.schemas.auth_schema import PasswordSetRequestBody


router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    path="/is_disabled",
    description="Check if auth disabled (DISABLE_AUTH env var)",
    response_model=bool,
)
async def is_disabled() -> bool:
    return Config.DISABLE_AUTH


@router.get(
    path="/{provider}/enabled",
    description="Check if auth provider is enabled",
    response_model=bool,
)
async def is_provider_enabled(
    provider: AuthProvider | None = Depends(auth_provider_by_name),
) -> bool:
    if not provider:
        raise TugNoAuthProviderException()
    return await provider.is_enabled()


@router.post(path="/{provider}/login")
@delay_to_minimum(1)
async def login(
    request: Request,
    response: Response,
    provider: AuthProvider | None = Depends(auth_provider_by_name),
):
    if not provider:
        raise TugNoAuthProviderException()
    return await provider.login(request, response)


@router.post(path="/refresh")
async def refresh(
    request: Request,
    response: Response,
    provider: AuthProvider | None = Depends(active_auth_provider),
):
    if not provider:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Unauthorized"
        )
    return await provider.refresh(request, response)


@router.post(path="/logout")
async def logout(
    request: Request,
    response: Response,
    provider: AuthProvider | None = Depends(active_auth_provider),
):
    if provider:
        return await provider.logout(request, response)
    return PlainTextResponse(status_code=status.HTTP_200_OK)


@router.get(
    path="/is_authorized",
    description="Check if session is authorized",
    response_model=bool,
)
async def is_authorized_req(
    _=Depends(is_authorized),
):
    return PlainTextResponse(status_code=status.HTTP_200_OK)


@router.post(
    path="/set_password",
    description="Set password for web UI. Password can be set only if password is not set yet or if user is authorized.",
)
async def set_password(
    request: Request, payload: PasswordSetRequestBody
):
    return await AUTH_PASSWORD_PROVIDER.set_password(request, payload)


@router.get(
    path="/is_password_set",
    description="Check if password is set",
    response_model=bool,
)
def is_password_set() -> bool:
    return AUTH_PASSWORD_PROVIDER.is_password_set()


@router.get(
    path="/{provider}/login", description="Login with provider"
)
async def provider_login(
    request: Request,
    response: Response,
    provider: AuthProvider | None = Depends(auth_provider_by_name),
) -> RedirectResponse:
    if not provider:
        raise TugNoAuthProviderException()
    return await provider.login(request, response)


@router.get(
    path="/{provider}/callback",
    description="Auth provider callback endpoint",
)
async def provider_callback(
    request: Request,
    response: Response,
    provider: AuthProvider | None = Depends(auth_provider_by_name),
):
    if not provider:
        raise TugNoAuthProviderException()
    return await provider.callback(request, response)
