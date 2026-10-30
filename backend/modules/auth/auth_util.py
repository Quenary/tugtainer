from typing import cast

import jwt
from fastapi import HTTPException, Request, status

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


def get_active_auth_provider_by_cookies(
    cookies: dict[str, str],
) -> AuthProvider | None:
    tokens = [
        cookies.get("access_token"),
        cookies.get("refresh_token"),
    ]
    data: TokenPayload | None = None
    for t in tokens:
        if t and not data:
            data = _decode_token(t)
    if not data:
        return None
    provider = data.get("auth_provider")
    return auth_provider_by_name(provider)


def get_active_auth_provider_by_req(
    request: Request,
) -> AuthProvider | None:
    """
    Returns active auth provider.
    That is provider used for authentication, which name is stored in tokens.
    """
    return get_active_auth_provider_by_cookies(request.cookies)


async def is_authorized_cookies(cookies: dict[str, str]) -> bool:
    """
    Check if cookies are valid and authorized.

    Returns True if auth is disabled.
    Returns True if authorized.

    Raises 401 if no provider in tokens or unauthorized.
    Raises 403 if active provider (in token) is disabled.
    """
    if Config.DISABLE_AUTH:
        return True
    provider = get_active_auth_provider_by_cookies(cookies)
    if not provider:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")
    await provider.raise_of_disabled()
    return await provider.is_authorized(cookies)


async def is_authorized_req(request: Request) -> bool:
    """
    Check if request has valid and authorized cookies.

    Returns True if auth is disabled.
    Returns True if authorized.

    Raises 401 if no provider in tokens or unauthorized.
    Raises 403 if active provider (in token) is disabled.
    """
    return await is_authorized_cookies(request.cookies)
