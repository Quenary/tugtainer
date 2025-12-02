from fastapi import (
    APIRouter,
    Depends,
    Response,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse, RedirectResponse
from backend.core.auth.auth_provider import AuthProvider
from backend.core.auth.auth_provider_chore import (
    AUTH_OIDC_PROVIDER,
    AUTH_PASSWORD_PROVIDER,
    AUTH_PROVIDERS,
    active_auth_provider,
)
from backend.exception import TugNoAuthProviderException
from backend.helpers.delay_to_minimum import delay_to_minimum
from backend.schemas.auth_schema import PasswordSetRequestBody


router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    path="/{provider}/enabled",
    description="Check if auth provider is enabled",
    response_model=bool,
)
async def is_provider_enabled(provider: str) -> bool:
    _provider = AUTH_PROVIDERS.get(provider, None)
    if not _provider:
        raise TugNoAuthProviderException()
    return await _provider.is_enabled()


@router.post(path="/login")
@delay_to_minimum(1)
async def login(
    request: Request,
    response: Response,
    provider: AuthProvider = Depends(active_auth_provider),
):
    return await provider.login(request, response)


@router.post(path="/refresh")
async def refresh(
    request: Request,
    response: Response,
    provider: AuthProvider = Depends(active_auth_provider),
):
    return await provider.refresh(request, response)


@router.post(path="/logout")
async def logout(
    request: Request,
    response: Response,
    provider: AuthProvider = Depends(active_auth_provider),
):
    return await provider.logout(request, response)


@router.get(
    path="/is_authorized",
    description="Check if session is authorized",
    response_model=bool,
)
async def is_authorized_req(
    request: Request,
    provider: AuthProvider = Depends(active_auth_provider),
):
    _ = await provider.is_authorized(request)
    return PlainTextResponse(status_code=status.HTTP_200_OK)


@router.post(
    path="/set_password",
    description="Set password for web UI. Password can be set only if password is not set yet or if user is authorized.",
)
async def set_password(request: Request, payload: PasswordSetRequestBody):
    return await AUTH_PASSWORD_PROVIDER.set_password(request, payload)


@router.get(
    path="/is_password_set",
    description="Check if password is set",
    response_model=bool,
)
def is_password_set() -> bool:
    return AUTH_PASSWORD_PROVIDER.is_password_set()


@router.get(
    path="/oidc_auto_redirect",
    description="Check if OIDC auto redirect is enabled",
    response_model=bool,
)
async def oidc_auto_redirect() -> bool:
    from backend.config import Config
    return Config.OIDC_AUTO_REDIRECT


@router.get(
    path="/{provider}/login", description="Login with provider"
)
async def provider_login(
    request: Request,
    response: Response,
    provider: AuthProvider = Depends(active_auth_provider),
) -> RedirectResponse:
    return await provider.login(request, response)


@router.get(
    path="/{provider}/callback",
    description="Auth provider callback endpoint",
)
async def provider_callback(
    request: Request,
    response: Response,
    provider: AuthProvider = Depends(active_auth_provider),
):
    return await provider.callback(request, response)
