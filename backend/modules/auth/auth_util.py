from typing import cast

from fastapi import HTTPException, Request, status
from jose import jwt

from backend.config import Config
from backend.modules.auth.auth_schemas import AuthProviderType, TokenPayload

from .providers.auth_oidc_provider import AuthOidcProvider
from .providers.auth_password_provider import (
    AuthPasswordProvider,
)
from .providers.auth_provider import AuthProvider

AUTH_PASSWORD_PROVIDER = AuthPasswordProvider()
AUTH_OIDC_PROVIDER = AuthOidcProvider()
AUTH_PROVIDERS: dict[AuthProviderType, AuthProvider] = {
    "password": AUTH_PASSWORD_PROVIDER,
    "oidc": AUTH_OIDC_PROVIDER,
}


def _decode_token(token: str) -> TokenPayload | None:
    try:
        return cast(
            TokenPayload,
            jwt.decode(
                token,
                key=Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM],
            ),
        )
    except Exception:
        return None


def auth_provider_by_name(
    provider: AuthProviderType,
) -> AuthProvider | None:
    """
    Get auth provider by name.
    """
    return AUTH_PROVIDERS.get(provider)


def active_auth_provider(
    request: Request,
) -> AuthProvider | None:
    """
    Returns active auth provider.
    That is provider used for authentication, which name is stored in tokens.
    """
    tokens = [
        request.cookies.get("access_token"),
        request.cookies.get("refresh_token"),
    ]
    data: TokenPayload | None = None
    for t in tokens:
        if t and not data:
            data = _decode_token(t)
    if not data:
        return None
    provider = data.get("auth_provider")
    return auth_provider_by_name(provider)


async def is_authorized(request: Request):
    """
    Dependency func that checks active auth provider auth state.
    Returns True if auth disabled.
    Returns True if there is active provider, and user is authorized.
    Raises 401 if none is authorized.
    Raises 403 if active provider (in token) is disabled.
    """
    if Config.DISABLE_AUTH:
        return True
    provider = active_auth_provider(request)
    if not provider:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    await provider.raise_of_disabled()
    return await provider.is_authorized(request)
