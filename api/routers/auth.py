"""Username + password accounts with an HttpOnly session cookie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from geo_draw.accounts import (
    MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, normalize_name, valid_password,
)

from ..deps import SESSION_COOKIE, Owner, app_state, get_owner, user_owner
from ..schemas import Credentials

router = APIRouter(prefix="/auth", tags=["auth"])
SESSION_MAX_AGE = 60 * 60 * 24 * 30


def me_json(request: Request, owner: Owner) -> dict:
    state = app_state(request)
    limit = state.daily_limit_guest if owner.is_guest else state.daily_limit_user
    return {
        "user": None if owner.is_guest else {"id": owner.user_id, "name": owner.name},
        "quota": {"used": state.quota.used(owner.identity), "limit": limit},
        "ai_available": state.ai_available,
    }


def _signed_in(request: Request, response: Response, user_id: str) -> dict:
    state = app_state(request)
    token = state.accounts.start_session(user_id)
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, httponly=True,
                        samesite="lax", secure=state.cookie_secure, path="/")
    return me_json(request, user_owner(state, user_id))


@router.get("/me")
def me(request: Request, owner: Owner = Depends(get_owner)) -> dict:
    return me_json(request, owner)


@router.post("/register", status_code=201)
def register(body: Credentials, request: Request, response: Response):
    accounts = app_state(request).accounts
    name = normalize_name(body.username)
    if not name:
        raise HTTPException(422, "Hãy nhập tên đăng nhập.")
    if accounts.name_exists(name):
        return JSONResponse(status_code=409, content={
            "detail": f"Tên đăng nhập «{name}» đã có người dùng. Hãy chọn một tên khác.",
            "suggestions": accounts.suggest_names(name),
        })
    if not valid_password(body.password):
        raise HTTPException(
            422, f"Mật khẩu phải có từ {MIN_PASSWORD_LENGTH} đến {MAX_PASSWORD_LENGTH} ký tự."
        )
    try:
        user_id = accounts.create(name, body.password)
    except ValueError as exc:  # someone registered the same name a moment earlier
        raise HTTPException(409, str(exc)) from exc
    return _signed_in(request, response, user_id)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response) -> dict:
    accounts = app_state(request).accounts
    name = normalize_name(body.username)
    if not name or not body.password:
        raise HTTPException(422, "Hãy nhập tên đăng nhập và mật khẩu.")
    locked = accounts.locked_seconds(name)
    user_id = None if locked else accounts.verify(name, body.password)
    if user_id is None:
        locked = locked or accounts.locked_seconds(name)
        if locked:
            raise HTTPException(
                429, f"Nhập sai quá nhiều lần. Hãy thử lại sau {-(-locked // 60)} phút."
            )
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu.")
    return _signed_in(request, response, user_id)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE, "")
    if token:
        app_state(request).accounts.end_session(token)
    response.delete_cookie(SESSION_COOKIE, path="/")
