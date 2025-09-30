from typing import Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from jose import jwt, JWTError
import bcrypt
import os
from app.config import Config
from app.helpers.now import now


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
    hashed_password: bytes = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password.decode("utf-8")


def verify_token(token: str) -> dict:
    """
    Verify token validity and return its payload.
    Raise 401 error if not valid.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, key=Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")


def create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """
    Create access or refresh token
    """
    to_encode: dict[str, Any] = data.copy()
    expire: datetime = now() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(
        claims=to_encode, key=Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM
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
