from typing import Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import PlainTextResponse
from app.helpers.delay_to_minimum import delay_to_minimum
from app.config import Config
from app.helpers.now import now
from app.core.auth import (
    get_password_hash,
    verify_token,
    verify_password,
    create_token,
    is_authorized,
    read_password_hash,
    write_password_hash,
)
from app.schemas.auth import PasswordSetRequestBody, IsPasswordSetResponseBody


router: APIRouter = APIRouter(prefix="/auth", tags=["auth"])


@router.post(path="/login")
@delay_to_minimum(1)
async def login(response: Response, password: str):
    STORED_PASSWORD_HASH: str | None = read_password_hash()

    if not STORED_PASSWORD_HASH:
        raise HTTPException(status_code=401, detail="Password not set")

    if not verify_password(password, STORED_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid password")

    access_token: str = create_token(
        data={"type": "access"},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_LIFETIME_MIN),
    )
    refresh_token: str = create_token(
        data={"type": "refresh"},
        expires_delta=timedelta(minutes=Config.REFRESH_TOKEN_LIFETIME_MIN),
    )
    print(access_token)
    print(refresh_token)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=Config.ACCESS_TOKEN_LIFETIME_MIN * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=Config.REFRESH_TOKEN_LIFETIME_MIN * 60,
    )
    response.status_code = status.HTTP_200_OK
    return response


@router.post(path="/refresh")
async def refresh(request: Request, response: Response):
    refresh_token: str | None = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    payload: dict[str, Any] = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token: str = create_token(
        data={"type": "access"},
        expires_delta=timedelta(minutes=Config.ACCESS_TOKEN_LIFETIME_MIN),
    )
    new_refresh_token: str = create_token(
        data={"type": "refresh"},
        expires_delta=timedelta(minutes=Config.REFRESH_TOKEN_LIFETIME_MIN),
    )
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=Config.ACCESS_TOKEN_LIFETIME_MIN * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
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
def is_authorized_req(_ = Depends(is_authorized)):
    return PlainTextResponse(status_code=status.HTTP_200_OK)
    # try:
    #     _ = is_authorized(request)
    #     return True
    # except:
    #     return False


@router.post(
    path="/set_password",
    description="Set password for web UI. Password can be set only if password is not set yet or if user is authorized.",
)
def set_password(request: Request, payload: PasswordSetRequestBody):
    password_hash: str = get_password_hash(payload.password)

    if not read_password_hash():
        write_password_hash(password_hash)
        return PlainTextResponse(status_code=status.HTTP_201_CREATED)

    try:
        _ = is_authorized(request)
        write_password_hash(password_hash)
        return PlainTextResponse(status_code=status.HTTP_200_OK)
    except HTTPException as e:
        raise e


@router.get(
    path="/is_password_set",
    description="Check if password is set",
    response_model=bool,
)
def is_password_set():
    password_hash: str | None = read_password_hash()
    return password_hash not in [None, ""]
