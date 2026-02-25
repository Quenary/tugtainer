from datetime import timedelta
import logging
from jose import jwt
from starlette.responses import RedirectResponse, Response
import secrets
from typing import Any, Literal, cast
from urllib.parse import urlencode
import aiohttp
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from backend.config import Config
from backend.core.auth.auth_provider import AuthProvider


class AuthOidcProvider(AuthProvider):
    async def is_enabled(self) -> bool:
        return not Config.DISABLE_AUTH and Config.OIDC_ENABLED

    async def login(
        self, request: Request, response: Response
    ) -> RedirectResponse:
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC authentication is not enabled",
            )

        config = self._get_oidc_config()

        if not all(
            [
                config["well_known_url"],
                config["client_id"],
                config["redirect_uri"],
            ]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OIDC configuration is incomplete",
            )

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Store state in session/cookie for verification later
        # For simplicity, we'll use a cookie (in production, consider using a database)

        try:
            discovery_doc = await self._fetch_oidc_discovery(
                config["well_known_url"]
            )
            authorization_url = self._create_oidc_authorization_url(
                discovery_doc, config, state
            )

            response = RedirectResponse(
                url=authorization_url,
                status_code=status.HTTP_302_FOUND,
            )
            response.set_cookie(
                key="oidc_state",
                value=state,
                httponly=True,
                samesite="lax",  # Changed from strict to lax for cross-origin redirects
                secure=Config.HTTPS,
                max_age=300,  # 5 minutes
            )
            return response

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error initiating OIDC login: {str(e)}",
            )

    async def logout(
        self, request: Request, response: Response
    ) -> Response:
        # TODO add logout call
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.status_code = status.HTTP_200_OK
        return response

    async def refresh(
        self, request: Request, response: Response
    ) -> Any:
        # TODO add refresh call
        raise NotImplementedError()

    async def is_authorized(self, request: Request):
        # TODO add check call
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )
        res = self._verify_token(token)
        return cast(Literal[True], bool(res))

    async def callback(
        self,
        request: Request,
        response: Response,
    ) -> RedirectResponse:
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        error = request.query_params.get("error", "")

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
        logging.debug(
            f"OIDC Callback - Received state: {state}, Stored state: {stored_state}"
        )
        logging.debug(
            f"OIDC Callback - All cookies: {dict(request.cookies)}"
        )
        if not stored_state or stored_state != state:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state parameter - received: {state}, stored: {stored_state}",
            )

        config = self._get_oidc_config()

        try:
            logging.debug(
                f"OIDC Callback - Code: {code}, State: {state}"
            )
            discovery_doc = await self._fetch_oidc_discovery(
                config["well_known_url"]
            )
            logging.debug(f"OIDC Discovery successful")
            user_data = await self._exchange_oidc_code(
                code, state, discovery_doc, config
            )
            logging.debug(
                f"OIDC Token exchange successful: {user_data}"
            )  # Debug print
            tokens = self._create_oidc_user_session(user_data)
            logging.debug(f"OIDC Session created")

            # Create response for redirect
            response = RedirectResponse(
                url="/containers", status_code=status.HTTP_302_FOUND
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

    def _get_oidc_config(self) -> dict[str, str]:
        """Get OIDC configuration from settings"""
        return {
            "well_known_url": Config.OIDC_WELL_KNOWN_URL,
            "client_id": Config.OIDC_CLIENT_ID,
            "client_secret": Config.OIDC_CLIENT_SECRET,
            "redirect_uri": Config.OIDC_REDIRECT_URI,
            "scopes": Config.OIDC_SCOPES,
        }

    async def _fetch_oidc_discovery(
        self, well_known_url: str
    ) -> dict[str, Any]:
        """Fetch OIDC discovery document from well-known URL"""
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(well_known_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to fetch OIDC discovery document: {response.status}",
                        )
        except aiohttp.ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching OIDC discovery document: {str(e)}",
            )

    def _create_oidc_authorization_url(
        self,
        discovery_doc: dict[str, Any],
        config: dict[str, str],
        state: str,
    ) -> str:
        """Create OIDC authorization URL"""
        try:
            # Manually build the authorization URL
            auth_endpoint = discovery_doc["authorization_endpoint"]
            scopes = config["scopes"]

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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error creating authorization URL: {str(e)}",
            )

    async def _exchange_oidc_code(
        self,
        code: str,
        state: str,
        discovery_doc: dict[str, Any],
        config: dict[str, str],
    ) -> dict[str, Any]:
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
            async with aiohttp.ClientSession(trust_env=True) as session:
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
                                "access_token": token.get(
                                    "access_token"
                                ),
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

    def _create_oidc_user_session(
        self,
        user_data: dict[str, Any],
    ) -> dict[str, str]:
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
        access_token = self._create_token(
            data={
                "type": "access",
                "auth_provider": "oidc",
                "oidc": True,
                "user_id": user_id,
                "user_info": user_claims,
            },
            expires_delta=timedelta(
                minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
            ),
        )

        refresh_token = self._create_token(
            data={
                "type": "refresh",
                "auth_provider": "oidc",
                "oidc": True,
                "user_id": user_id,
            },
            expires_delta=timedelta(
                minutes=Config.REFRESH_TOKEN_LIFETIME_MIN
            ),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
