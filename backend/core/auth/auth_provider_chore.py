from fastapi import HTTPException, Request, status
from backend.core.auth.auth_oidc_provider import AuthOidcProvider
from backend.core.auth.auth_password_provider import (
    AuthPasswordProvider,
)
from backend.core.auth.auth_provider import AuthProvider


AUTH_PASSWORD_PROVIDER = AuthPasswordProvider()
AUTH_OIDC_PROVIDER = AuthOidcProvider()
AUTH_PROVIDERS: list[AuthProvider] = [
    AUTH_PASSWORD_PROVIDER,
    AUTH_OIDC_PROVIDER,
]


async def is_authorized(request: Request):
    """
    Dependency func that checks all enabled auth providers state.
    Raises 401 if none is authorized.
    """
    for p in AUTH_PROVIDERS:
        try:
            if await p.is_enabled():
                _ = await p.is_authorized(request)
                return True
        except:
            pass
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
    )
