from fastapi import Request
from backend.core.auth.auth_oidc_provider import AuthOidcProvider
from backend.core.auth.auth_password_provider import (
    AuthPasswordProvider,
)
from backend.core.auth.auth_provider import AuthProvider
from backend.exception import TugNoAuthProviderException

AUTH_PASSWORD_PROVIDER = AuthPasswordProvider()
AUTH_OIDC_PROVIDER = AuthOidcProvider()
AUTH_PROVIDERS: dict[str, AuthProvider] = {
    "password": AUTH_PASSWORD_PROVIDER,
    "oidc": AUTH_OIDC_PROVIDER,
}


async def active_auth_provider() -> AuthProvider:
    for p in AUTH_PROVIDERS.values():
        if await p.is_enabled():
            return p
    raise TugNoAuthProviderException()


async def is_authorized(request: Request):
    """
    Dependency func that checks active auth provider auth state.
    Raises 401 if none is authorized.
    """
    provider = await active_auth_provider()
    _ = await provider.is_authorized(request)
    return True
