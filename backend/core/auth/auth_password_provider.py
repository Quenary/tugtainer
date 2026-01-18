from datetime import timedelta
from typing import Any, Literal, cast
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from backend.schemas.auth_schema import PasswordSetRequestBody
from .auth_provider import AuthProvider
from backend.config import Config
import bcrypt
import os


class AuthPasswordProvider(AuthProvider):
    async def is_enabled(self):
        return not Config.DISABLE_AUTH and not Config.DISABLE_PASSWORD

    async def login(self, request: Request, response: Response):
        try:
            body = await request.json()
            password = body.get("password", "")
        except Exception:
            password = ""

        STORED_PASSWORD_HASH: str | None = self._read_password_hash()

        if not STORED_PASSWORD_HASH:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password not set",
            )

        if not self._verify_password(password, STORED_PASSWORD_HASH):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        access_token: str = self._create_token(
            data={
                "type": "access",
                "auth_provider": "password",
            },
            expires_delta=timedelta(
                minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
            ),
        )
        refresh_token: str = self._create_token(
            data={
                "type": "refresh",
                "auth_provider": "password",
            },
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

    async def logout(self, request: Request, response: Response):
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.status_code = status.HTTP_200_OK
        return response

    async def refresh(self, request: Request, response: Response):
        refresh_token: str | None = request.cookies.get(
            "refresh_token"
        )
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing refresh token",
            )

        payload: dict[str, Any] = self._verify_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        new_access_token: str = self._create_token(
            data={
                "type": "access",
                "auth_provider": "password",
            },
            expires_delta=timedelta(
                minutes=Config.ACCESS_TOKEN_LIFETIME_MIN
            ),
        )
        new_refresh_token: str = self._create_token(
            data={
                "type": "refresh",
                "auth_provider": "password",
            },
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

    async def is_authorized(self, request: Request):
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
            )
        res = self._verify_token(token)
        return cast(Literal[True], bool(res))

    async def callback(
        self, request: Request, response: Response
    ) -> Any:
        raise NotImplementedError()

    async def set_password(
        self, request: Request, payload: PasswordSetRequestBody
    ):
        """
        Set new password if there is no password yet or if user authorized.
        """

        def write_and_return():
            password_hash: str = self._get_password_hash(
                payload.password
            )
            self._write_password_hash(password_hash)
            return PlainTextResponse(
                status_code=status.HTTP_201_CREATED
            )

        if not self._read_password_hash():
            return write_and_return()

        _ = await self.is_authorized(request)
        return write_and_return()

    def is_password_set(self) -> bool:
        """Check if a password is set"""
        password_hash: str | None = self._read_password_hash()
        return password_hash not in [None, ""]

    def _verify_password(self, plain: str, hashed: str) -> bool:
        """
        Compare plain text password with hashed password
        """
        plain_bytes: bytes = plain.encode("utf-8")
        hashed_bytes: bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)

    def _get_password_hash(self, password: str) -> str:
        """Hash password"""
        pwd_bytes: bytes = password.encode("utf-8")
        salt: bytes = bcrypt.gensalt()
        hashed_password: bytes = bcrypt.hashpw(
            password=pwd_bytes, salt=salt
        )
        return hashed_password.decode("utf-8")

    def _read_password_hash(self) -> str | None:
        """
        Read password hash from file
        """
        if not os.path.isfile(Config.PASSWORD_FILE):
            return None
        with open(Config.PASSWORD_FILE, "r") as f:
            return f.read()

    def _write_password_hash(self, password_hash: str) -> None:
        """
        Write password hash to file
        """
        with open(Config.PASSWORD_FILE, "w") as f:
            _ = f.write(password_hash)
            f.flush()
            f.close()
