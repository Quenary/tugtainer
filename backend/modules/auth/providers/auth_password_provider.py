import os
from datetime import timedelta
from typing import Literal, cast

import bcrypt
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse

from backend.config import Config

from ..auth_schemas import PasswordSetRequestBody
from .auth_provider import AuthProvider


class AuthPasswordProvider(AuthProvider):
    async def is_enabled(self) -> bool:
        return not Config.DISABLE_AUTH and not Config.DISABLE_PASSWORD

    async def login(self, request: Request, response: Response) -> Response:
        await self.raise_of_disabled()

        try:
            body = await request.json()
            password = body.get("password", "")
        except Exception:
            password = ""

        stored_password_hash: str | None = self._read_password_hash()

        if not stored_password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set",
            )

        if not self._verify_password(password, stored_password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        access_token: str = self._create_token(
            data={
                "type": "access",
                "auth_provider": "password",
            },
            expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_LIFETIME_MIN),
        )
        refresh_token: str = self._create_token(
            data={
                "type": "refresh",
                "auth_provider": "password",
            },
            expires_delta=timedelta(minutes=Config.REFRESH_TOKEN_LIFETIME_MIN),
        )
        self._set_cookies(
            response,
            access_token,
            refresh_token,
        )
        response.status_code = status.HTTP_200_OK
        return response

    async def logout(self, request: Request, response: Response) -> Response:
        self._delete_cookies(response)
        response.status_code = status.HTTP_200_OK
        return response

    async def refresh(self, request: Request, response: Response) -> Response:
        await self.raise_of_disabled()

        refresh_token: str | None = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing",
            )

        payload = self._verify_token(refresh_token)
        if (
            payload.get("type") != "refresh"
            or payload.get("auth_provider") != "password"
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token type or provider",
            )

        new_access_token: str = self._create_token(
            data={
                "type": "access",
                "auth_provider": "password",
            },
            expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_LIFETIME_MIN),
        )
        new_refresh_token: str = self._create_token(
            data={
                "type": "refresh",
                "auth_provider": "password",
            },
            expires_delta=timedelta(minutes=Config.REFRESH_TOKEN_LIFETIME_MIN),
        )
        self._set_cookies(
            response,
            new_access_token,
            new_refresh_token,
        )
        response.status_code = status.HTTP_200_OK
        return response

    async def is_authorized(self, request: Request) -> Literal[True]:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )
        payload = self._verify_token(token)
        if (
            payload.get("type") != "access"
            or payload.get("auth_provider") != "password"
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type or provider",
            )

        return cast(Literal[True], True)

    async def callback(self, request: Request, response: Response) -> Response:
        raise NotImplementedError()

    async def set_password(
        self, request: Request, payload: PasswordSetRequestBody
    ) -> PlainTextResponse:
        """
        Set new password if there is no password yet or if user authorized.
        """

        def write_and_return() -> PlainTextResponse:
            password_hash: str = self._get_password_hash(payload.password)
            self._write_password_hash(password_hash)
            return PlainTextResponse(status_code=status.HTTP_201_CREATED)

        if not self._read_password_hash():
            return write_and_return()

        # Just verify authorization; will raise HTTPException if invalid
        await self.is_authorized(request)
        return write_and_return()

    def is_password_set(self) -> bool:
        """Check if a password is set"""
        password_hash: str | None = self._read_password_hash()
        return password_hash not in [None, ""]

    def _verify_password(self, plain: str, hashed: str) -> bool:
        """Compare plain text password with hashed password"""
        plain_bytes: bytes = plain.encode("utf-8")
        hashed_bytes: bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)

    def _get_password_hash(self, password: str) -> str:
        """Hash password"""
        pwd_bytes: bytes = password.encode("utf-8")
        salt: bytes = bcrypt.gensalt()
        hashed_password: bytes = bcrypt.hashpw(password=pwd_bytes, salt=salt)
        return hashed_password.decode("utf-8")

    def _read_password_hash(self) -> str | None:
        """Read password hash from file"""
        if not os.path.isfile(Config.PASSWORD_FILE):
            return None
        with open(Config.PASSWORD_FILE) as f:
            return f.read()

    def _write_password_hash(self, password_hash: str) -> None:
        """Write password hash to file"""
        with open(Config.PASSWORD_FILE, "w") as f:
            f.write(password_hash)
            f.flush()
