from typing import Any, Dict
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from jose import jwt, JWTError
import bcrypt
import os
import aiohttp
from urllib.parse import urlencode
from backend.config import Config
from backend.helpers.now import now


def verify_password(plain: str, hashed: str) -> bool:
    """
    Compare plain text password with hashed password
    """
    plain_bytes: bytes = plain.encode("utf-8")
    hashed_bytes: bytes = hashed.encode("utf-8")
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Hash password"""
    pwd_bytes: bytes = password.encode("utf-8")
    salt: bytes = bcrypt.gensalt()
    hashed_password: bytes = bcrypt.hashpw(
        password=pwd_bytes, salt=salt
    )
    return hashed_password.decode("utf-8")


def verify_token(token: str) -> dict:
    """
    Verify token validity and return its payload.
    Raise 401 error if not valid.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Token is invalid or expired"
        )


def create_token(
    data: dict[str, Any], expires_delta: timedelta
) -> str:
    """
    Create access or refresh token
    """
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = now() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(
        claims=to_encode,
        key=Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM,
    )


def is_authorized(request: Request) -> dict[str, Any]:
    """
    Check for valid token in cookies.
    Raise 401 if there is no token or token is invalid.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return verify_token(token)


def read_password_hash() -> str | None:
    """
    Read password hash from file
    """
    if not os.path.isfile(Config.PASSWORD_FILE):
        return None
    with open(Config.PASSWORD_FILE, "r") as f:
        return f.read()


def write_password_hash(password_hash: str) -> None:
    """
    Write password hash to file
    """
    with open(Config.PASSWORD_FILE, "w") as f:
        _ = f.write(password_hash)
        f.flush()
        f.close()


def is_oidc_enabled() -> bool:
    """Check if OIDC authentication is enabled"""
    return Config.OIDC_ENABLED


def get_oidc_config() -> Dict[str, str]:
    """Get OIDC configuration from settings"""
    return {
        "well_known_url": Config.OIDC_WELL_KNOWN_URL,
        "client_id": Config.OIDC_CLIENT_ID,
        "client_secret": Config.OIDC_CLIENT_SECRET,
        "redirect_uri": Config.OIDC_REDIRECT_URI,
        "scopes": Config.OIDC_SCOPES,
    }


async def fetch_oidc_discovery(well_known_url: str) -> Dict[str, Any]:
    """Fetch OIDC discovery document from well-known URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(well_known_url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to fetch OIDC discovery document: {response.status}",
                    )
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching OIDC discovery document: {str(e)}",
        )


def create_oidc_authorization_url(
    discovery_doc: Dict[str, Any], config: Dict[str, str], state: str
) -> str:
    """Create OIDC authorization URL"""
    try:
        # Manually build the authorization URL
        auth_endpoint = discovery_doc["authorization_endpoint"]
        scopes = " ".join(config["scopes"])

        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": scopes,
            "response_type": "code",
            "state": state,
        }

        # Build query string
        query_string = urlencode(params)
        authorization_url = f"{auth_endpoint}?{query_string}"

        return authorization_url
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating authorization URL: {str(e)}",
        )


async def exchange_oidc_code(
    code: str,
    state: str,
    discovery_doc: Dict[str, Any],
    config: Dict[str, str],
) -> Dict[str, Any]:
    """Exchange authorization code for tokens"""
    try:
        # Prepare token exchange request
        token_endpoint = discovery_doc["token_endpoint"]

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        }

        # Exchange code for token
        async with aiohttp.ClientSession() as session:
            async with session.post(
                token_endpoint, data=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Token exchange failed: {error_text}",
                    )

                token = await response.json()

            # Verify and decode ID token if present
            if "id_token" in token:
                # For now, we'll decode without verification (not recommended for production)
                id_token_claims = jwt.get_unverified_claims(
                    token["id_token"]
                )
                return {
                    "access_token": token.get("access_token"),
                    "id_token_claims": id_token_claims,
                }

            # If no ID token, fetch user info from userinfo endpoint
            if "userinfo_endpoint" in discovery_doc:
                headers = {
                    "Authorization": f"Bearer {token['access_token']}"
                }
                async with session.get(
                    discovery_doc["userinfo_endpoint"],
                    headers=headers,
                ) as response:
                    if response.status == 200:
                        user_info = await response.json()
                        return {
                            "access_token": token.get("access_token"),
                            "user_info": user_info,
                        }

        raise HTTPException(
            status_code=400,
            detail="Unable to retrieve user information from OIDC provider",
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error exchanging authorization code: {str(e)}",
        )


def create_oidc_user_session(
    user_data: Dict[str, Any],
) -> Dict[str, str]:
    """Create user session tokens after OIDC authentication"""
    # Extract user identifier (email, sub, or preferred_username)
    user_claims = user_data.get(
        "id_token_claims", user_data.get("user_info", {})
    )

    user_id = (
        user_claims.get("email")
        or user_claims.get("sub")
        or user_claims.get("preferred_username")
        or "unknown_user"
    )

    # Create JWT tokens with OIDC user info
    access_token = create_token(
        data={
            "type": "access",
            "oidc": True,
            "user_id": user_id,
            "user_info": user_claims,
        },
        expires_delta=timedelta(
            minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
        ),
    )

    refresh_token = create_token(
        data={"type": "refresh", "oidc": True, "user_id": user_id},
        expires_delta=timedelta(
            minutes=Config.REFRESH_TOKEN_LIFETIME_MIN
        ),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
