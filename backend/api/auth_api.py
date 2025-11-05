from typing import Any
from datetime import timedelta
import secrets
import urllib.parse
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse, RedirectResponse
from backend.helpers.delay_to_minimum import delay_to_minimum
from backend.config import Config
from backend.helpers.now import now
from backend.core.auth_core import (
    get_password_hash,
    verify_token,
    verify_password,
    create_token,
    is_authorized,
    read_password_hash,
    write_password_hash,
    is_oidc_enabled,
    get_oidc_config,
    fetch_oidc_discovery,
    create_oidc_authorization_url,
    exchange_oidc_code,
    create_oidc_user_session,
)
from backend.schemas.auth_schema import PasswordSetRequestBody


router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


@router.post(path="/login")
@delay_to_minimum(1)
async def login(response: Response, password: str):
    STORED_PASSWORD_HASH: str | None = read_password_hash()

    if not STORED_PASSWORD_HASH:
        raise HTTPException(
            status_code=401, detail="Password not set"
        )

    if not verify_password(password, STORED_PASSWORD_HASH):
        raise HTTPException(
            status_code=401, detail="Invalid password"
        )

    access_token: str = create_token(
        data={"type": "access"},
        expires_delta=timedelta(
            minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
        ),
    )
    refresh_token: str = create_token(
        data={"type": "refresh"},
        expires_delta=timedelta(
            minutes=Config.REFRESH_TOKEN_LIFETIME_MIN
        ),
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="strict",
        secure=Config.HTTPS,
        domain=Config.DOMAIN,
        max_age=Config.ACCESS_TOKEN_LIFETIME_MIN * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="strict",
        secure=Config.HTTPS,
        domain=Config.DOMAIN,
        max_age=Config.REFRESH_TOKEN_LIFETIME_MIN * 60,
    )
    response.status_code = status.HTTP_200_OK
    return response


@router.post(path="/refresh")
async def refresh(request: Request, response: Response):
    refresh_token: str | None = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=401, detail="Missing refresh token"
        )

    payload: dict[str, Any] = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401, detail="Invalid refresh token"
        )

    new_access_token: str = create_token(
        data={"type": "access"},
        expires_delta=timedelta(
            minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
        ),
    )
    new_refresh_token: str = create_token(
        data={"type": "refresh"},
        expires_delta=timedelta(
            minutes=Config.REFRESH_TOKEN_LIFETIME_MIN
        ),
    )
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        samesite="strict",
        secure=Config.HTTPS,
        domain=Config.DOMAIN,
        max_age=Config.ACCESS_TOKEN_LIFETIME_MIN * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        samesite="strict",
        secure=Config.HTTPS,
        domain=Config.DOMAIN,
        max_age=Config.REFRESH_TOKEN_LIFETIME_MIN * 60,
    )
    response.status_code = status.HTTP_200_OK
    return response


@router.post(path="/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.status_code = status.HTTP_200_OK
    return response


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
    password_hash: str = get_password_hash(payload.password)

    if not read_password_hash():
        write_password_hash(password_hash)
        return PlainTextResponse(status_code=status.HTTP_201_CREATED)

    _ = is_authorized(request)
    write_password_hash(password_hash)
    return PlainTextResponse(status_code=status.HTTP_200_OK)


@router.get(
    path="/is_password_set",
    description="Check if password is set",
    response_model=bool,
)
def is_password_set():
    password_hash: str | None = read_password_hash()
    return password_hash not in [None, ""]


def get_current_user(request: Request) -> dict[str, Any]:
    """Dependency to get current user from access token"""
    access_token: str | None = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=401, detail="Missing access token"
        )

    payload: dict[str, Any] = verify_token(access_token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401, detail="Invalid access token"
        )

    return payload


@router.get(
    path="/user/info",
    description="Get current authenticated user information",
)
def get_user_info(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user_info = {
        "is_oidc": current_user.get("oidc", False),
        "user_id": current_user.get("user_id", ""),
    }

    # If OIDC user, include additional user info
    if current_user.get("oidc") and current_user.get("user_info"):
        oidc_info = current_user.get("user_info", {})
        user_info.update(
            {
                "email": oidc_info.get("email", ""),
                "name": oidc_info.get("name", ""),
                "preferred_username": oidc_info.get(
                    "preferred_username", ""
                ),
                "sub": oidc_info.get("sub", ""),
            }
        )

    return user_info


@router.get(
    path="/oidc/enabled",
    description="Check if OIDC authentication is enabled",
    response_model=bool,
)
def oidc_enabled():
    return is_oidc_enabled()


@router.get(
    path="/oidc/login",
    description="Initiate OIDC login flow",
)
async def oidc_login(request: Request):
    if not is_oidc_enabled():
        raise HTTPException(
            status_code=400,
            detail="OIDC authentication is not enabled",
        )

    config = get_oidc_config()

    if not all(
        [
            config["well_known_url"],
            config["client_id"],
            config["redirect_uri"],
        ]
    ):
        raise HTTPException(
            status_code=400, detail="OIDC configuration is incomplete"
        )

    # Generate state parameter for CSRF protection
    state = secrets.token_urlsafe(32)

    # Store state in session/cookie for verification later
    # For simplicity, we'll use a cookie (in production, consider using a database)

    try:
        discovery_doc = await fetch_oidc_discovery(
            config["well_known_url"]
        )
        authorization_url = create_oidc_authorization_url(
            discovery_doc, config, state
        )

        response = RedirectResponse(
            url=authorization_url, status_code=302
        )
        response.set_cookie(
            key="oidc_state",
            value=state,
            httponly=True,
            samesite="lax",  # Changed from strict to lax for cross-origin redirects
            secure=False,  # Set to False for HTTP testing
            max_age=300,  # 5 minutes
        )
        return response

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error initiating OIDC login: {str(e)}",
        )


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
    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OIDC authentication error: {error}",
        )

    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Missing authorization code or state parameter",
        )

    # Verify state parameter
    stored_state = request.cookies.get("oidc_state")
    print(
        f"OIDC Callback Debug - Received state: {state}, Stored state: {stored_state}"
    )  # Debug print
    print(
        f"OIDC Callback Debug - All cookies: {dict(request.cookies)}"
    )  # Debug print
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state parameter - received: {state}, stored: {stored_state}",
        )

    config = get_oidc_config()

    try:
        print(
            f"OIDC Callback - Code: {code}, State: {state}"
        )  # Debug print
        discovery_doc = await fetch_oidc_discovery(
            config["well_known_url"]
        )
        print(f"OIDC Discovery successful")  # Debug print
        user_data = await exchange_oidc_code(
            code, state, discovery_doc, config
        )
        print(
            f"OIDC Token exchange successful: {user_data}"
        )  # Debug print
        tokens = create_oidc_user_session(user_data)
        print(f"OIDC Session created")  # Debug print

        # Create response for redirect
        response = RedirectResponse(
            url="/containers", status_code=302
        )

        # Set authentication cookies
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            httponly=True,
            samesite="strict",
            secure=Config.HTTPS,
            domain=Config.DOMAIN if Config.DOMAIN else None,
            max_age=Config.ACCESS_TOKEN_LIFETIME_MIN * 60,
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            samesite="strict",
            secure=Config.HTTPS,
            domain=Config.DOMAIN if Config.DOMAIN else None,
            max_age=Config.REFRESH_TOKEN_LIFETIME_MIN * 60,
        )

        # Clear the state cookie
        response.delete_cookie("oidc_state")

        return response

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error processing OIDC callback: {str(e)}",
        )
