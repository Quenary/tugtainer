from abc import ABC, abstractmethod
from datetime import timedelta, datetime
from typing import Any, Literal
from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from backend.config import Config
from backend.helpers.now import now


class AuthProvider(ABC):
    @abstractmethod
    async def is_enabled(self) -> bool:
        """Whether provider enabled"""
        pass

    @abstractmethod
    async def login(
        self, request: Request, response: Response
    ) -> Any:
        """Login with provider"""
        pass

    @abstractmethod
    async def logout(
        self, request: Request, response: Response
    ) -> Any:
        """Logout with provider"""
        pass

    @abstractmethod
    async def refresh(
        self, request: Request, response: Response
    ) -> Any:
        """Refresh tokens with provider"""
        pass

    @abstractmethod
    async def is_authorized(self, request: Request) -> Literal[True]:
        """Whether user is authorized. Should raise 401 if not."""
        pass

    @abstractmethod
    async def callback(
        self, request: Request, response: Response
    ) -> Any:
        """Provider callback endpoint handler"""
        pass

    def _create_token(
        self, data: dict[str, Any], expires_delta: timedelta
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

    def _verify_token(self, token: str) -> dict:
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
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is invalid or expired",
            )
