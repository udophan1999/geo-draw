"""Admin page: manage accounts and edit the tutor's system prompts. Admins only."""

from __future__ import annotations

import shutil
import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from geo_draw.accounts import (
    ADMIN, MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, ROLES, UserInfo,
)
from geo_draw.tutor_prompts import EDITABLE_PROMPTS, GUARDRAIL, MAX_PROMPT_LENGTH, PROGRESS_RULE

from ..deps import Owner, app_state, require_admin
from ..state import AppState

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class UserUpdate(BaseModel):
    role: str | None = None
    disabled: bool | None = None
    # A number sets this user's own daily limit; null with reset_limit=true goes back to
    # the server default.
    daily_limit: int | None = Field(default=None, ge=0, le=100_000)
    reset_limit: bool = False


class PasswordReset(BaseModel):
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class PromptUpdate(BaseModel):
    value: str = Field(max_length=MAX_PROMPT_LENGTH)


def _user_json(state: AppState, user: UserInfo, stats: dict, used: dict) -> dict:
    conversations, last_active = stats.get(user.user_id, (0, None))
    return {
        "id": user.user_id,
        "name": user.name,
        "role": user.role,
        "disabled": user.disabled,
        "created_at": user.created_at,
        "last_login": user.last_login or None,
        "last_active": last_active,
        "conversations": conversations,
        "quota": {"used": used.get(user.user_id, 0),
                  "limit": state.daily_limit(False, user.daily_limit),
                  "custom": user.daily_limit is not None},
    }


def _target(state: AppState, user_id: str) -> UserInfo:
    user = state.accounts.get_user(user_id)
    if user is None:
        raise HTTPException(404, "Không tìm thấy tài khoản.")
    return user


def _not_self(admin: Owner, user_id: str, action: str) -> None:
    # Acting on others only keeps at least one admin (the one acting) at all times.
    if admin.user_id == user_id:
        raise HTTPException(409, f"Bạn không thể {action} chính tài khoản của mình.")


def _day(timestamp: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(timestamp))  # the quota's day, too


def _range(days: int) -> tuple[list[str], dict[str, int], float]:
    """The last ``days`` local dates (oldest first), their positions, and the first one's start."""
    if days not in (7, 30, 90):
        raise HTTPException(422, "Chỉ hỗ trợ 7, 30 hoặc 90 ngày.")
    today = date.fromisoformat(_day(time.time()))
    labels = [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]
    return labels, {day: i for i, day in enumerate(labels)}, time.mktime(
        date.fromisoformat(labels[0]).timetuple())


@router.get("/stats")
def stats(request: Request, days: int = 30) -> dict:
    """The overview page: totals and daily series over the last ``days`` days.

    Conversation figures cover accounts only (guests' conversations are not kept in one
    place with SQLite); AI turns cover accounts and guests.
    """
    state = app_state(request)
    labels, index, since = _range(days)

    users = state.accounts.list_users()
    names = {u.user_id: u.name for u in users}
    new_users = [0] * days
    for user in users:
        if (i := index.get(_day(user.created_at))) is not None:
            new_users[i] += 1

    ai_users, ai_guests = [0] * days, [0] * days
    ai_by_user: dict[str, int] = {}
    for owner, day, count in state.quota.daily_since(labels[0]):
        if (i := index.get(day)) is None or owner.startswith("~"):  # ~total, ~ai:<ip>…
            continue
        if owner.startswith("guest:"):
            ai_guests[i] += count
        else:
            ai_users[i] += count
            ai_by_user[owner] = ai_by_user.get(owner, 0) + count

    new_conversations = [0] * days
    outcomes = {"solved": 0, "solution": 0, "in_progress": 0}
    conversations_by_user: dict[str, int] = {}
    for owner, created, mode, solved in state.conversations.created_since(since):
        if owner not in names:  # guests, or accounts deleted since
            continue
        if (i := index.get(_day(created))) is not None:
            new_conversations[i] += 1
        conversations_by_user[owner] = conversations_by_user.get(owner, 0) + 1
        outcome = "solved" if solved else "solution" if mode == "solution" else "in_progress"
        outcomes[outcome] += 1

    active = {owner for owner in conversations_by_user} | set(ai_by_user)
    active |= {u.user_id for u in users if u.last_login and u.last_login >= since}
    top = sorted(set(ai_by_user) | set(conversations_by_user),
                 key=lambda uid: (-ai_by_user.get(uid, 0), -conversations_by_user.get(uid, 0)))
    return {
        "days": labels,
        "series": {"new_users": new_users, "new_conversations": new_conversations,
                   "ai_users": ai_users, "ai_guests": ai_guests},
        "totals": {
            "users": len(users),
            "admins": sum(u.is_admin for u in users),
            "locked": sum(u.disabled for u in users),
            "new_users": sum(new_users),
            "active_users": len(active & set(names)),
            "conversations": sum(count for owner, (count, _) in state.conversations.owner_stats().items()
                                 if owner in names),
            "new_conversations": sum(new_conversations),
            "ai_turns": sum(ai_users) + sum(ai_guests),
            "ai_guest_turns": sum(ai_guests),
        },
        "outcomes": outcomes,
        "top_users": [{"id": uid, "name": names[uid], "ai_turns": ai_by_user.get(uid, 0),
                       "conversations": conversations_by_user.get(uid, 0)}
                      for uid in top if uid in names][:5],
    }


@router.get("/users")
def list_users(request: Request, q: str = "") -> dict:
    state = app_state(request)
    stats, used = state.conversations.owner_stats(), state.quota.used_today()
    needle = q.strip().casefold()
    users = [u for u in state.accounts.list_users() if needle in u.name.casefold()]
    return {
        "users": [_user_json(state, u, stats, used) for u in users],
        "default_limit": state.daily_limit_user,
    }


@router.get("/users/{user_id}")
def user_detail(user_id: str, request: Request, days: int = 30) -> dict:
    """One account: its row, usage over the last ``days`` days, and its conversations.

    Conversation contents are not included: the page shows activity, not what was said.
    """
    state = app_state(request)
    user = _target(state, user_id)
    labels, index, since = _range(days)

    ai_series = [0] * days
    ai_all = 0
    for day, count in state.quota.owner_days(user_id):
        ai_all += count
        if (i := index.get(day)) is not None:
            ai_series[i] += count

    # A "question" is a message the student sent to the tutor (the problem, an answer, a
    # follow-up, or a hint/solution button).
    questions, drawings = {}, {}
    questions_series = [0] * days
    questions_all = drawings_all = 0
    for cid, role, channel, created, drawing in state.conversations.owner_messages(user_id):
        if role == "user" and channel == "chat":
            questions[cid] = questions.get(cid, 0) + 1
            questions_all += 1
            if (i := index.get(_day(created))) is not None:
                questions_series[i] += 1
        elif drawing:
            drawings[cid] = drawings.get(cid, 0) + 1
            drawings_all += 1

    conversations = state.conversations.list(user_id, limit=10_000)
    levels = [0] * 5
    outcomes = {"solved": 0, "solution": 0, "in_progress": 0}
    for c in conversations:
        if c.solved:
            outcomes["solved"] += 1
        elif c.mode == "solution":
            outcomes["solution"] += 1
        else:
            outcomes["in_progress"] += 1
        levels[min(max(c.hint_level, 1), 5) - 1] += 1

    stats, used = state.conversations.owner_stats(), state.quota.used_today()
    return {
        **_user_json(state, user, stats, used),
        "default_limit": state.daily_limit_user,
        "days": labels,
        "series": {"ai": ai_series, "questions": questions_series},
        "totals": {
            "ai_turns": ai_all, "ai_turns_range": sum(ai_series),
            "questions": questions_all, "questions_range": sum(questions_series),
            "conversations": len(conversations),
            "conversations_range": sum(c.created_at >= since for c in conversations),
            "drawings": drawings_all, "active_days": sum(v > 0 for v in ai_series),
        },
        "outcomes": outcomes,
        "hint_levels": levels,
        # Not "conversations": that is the count, from _user_json above.
        "recent_conversations": [
            {"id": c.id, "title": c.title, "created_at": c.created_at, "updated_at": c.updated_at,
             "mode": c.mode, "hint_level": c.hint_level, "solved": c.solved,
             "questions": questions.get(c.id, 0), "drawings": drawings.get(c.id, 0)}
            for c in conversations[:50]
        ],
    }


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserUpdate, request: Request,
                admin: Owner = Depends(require_admin)) -> dict:
    state = app_state(request)
    user = _target(state, user_id)
    if body.role is not None:
        if body.role not in ROLES:
            raise HTTPException(422, "Vai trò không hợp lệ.")
        if body.role != ADMIN:
            _not_self(admin, user_id, "bỏ quyền quản trị của")
        state.accounts.set_role(user_id, body.role)
    if body.disabled is not None:
        if body.disabled:
            _not_self(admin, user_id, "khóa")
        state.accounts.set_disabled(user_id, body.disabled)
    if body.reset_limit:
        state.accounts.set_daily_limit(user_id, None)
    elif body.daily_limit is not None:
        state.accounts.set_daily_limit(user_id, body.daily_limit)
    user = _target(state, user.user_id)
    return _user_json(state, user, state.conversations.owner_stats(), state.quota.used_today())


@router.post("/users/{user_id}/password", status_code=204)
def reset_password(user_id: str, body: PasswordReset, request: Request) -> None:
    state = app_state(request)
    _target(state, user_id)
    try:
        state.accounts.set_password(user_id, body.password)
    except ValueError as exc:
        raise HTTPException(
            422, f"Mật khẩu phải có từ {MIN_PASSWORD_LENGTH} đến {MAX_PASSWORD_LENGTH} ký tự."
        ) from exc


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, request: Request, admin: Owner = Depends(require_admin)) -> None:
    """Delete the account with all its conversations, drawings and settings."""
    state = app_state(request)
    _target(state, user_id)
    _not_self(admin, user_id, "xóa")
    state.conversations.delete_owner(user_id)
    state.accounts.delete_user(user_id)
    workspace = state.users_dir / user_id  # settings.json and any files left
    shutil.rmtree(workspace, ignore_errors=True)


@router.get("/prompts")
def list_prompts(request: Request) -> dict:
    saved = app_state(request).config.all()
    return {
        "prompts": [
            {"key": key, "label": label, "description": description, "default": default,
             "value": saved[key][0] if key in saved else default, "custom": key in saved,
             "updated_at": saved[key][1] if key in saved else None,
             "updated_by": saved[key][2] if key in saved else None}
            for key, (label, description, default) in EDITABLE_PROMPTS.items()
        ],
        # Always appended in hint mode; shown read-only on the admin page.
        "fixed": [{"label": "Rào chắn không đưa đáp án", "text": GUARDRAIL},
                  {"label": "Báo tiến độ (ứng dụng tự đọc)", "text": PROGRESS_RULE}],
    }


@router.put("/prompts/{key}")
def save_prompt(key: str, body: PromptUpdate, request: Request,
                admin: Owner = Depends(require_admin)) -> dict:
    if key not in EDITABLE_PROMPTS:
        raise HTTPException(404, "Không có prompt này.")
    value = body.value.strip()
    if not value:
        raise HTTPException(422, "Prompt không được để trống. Muốn dùng lại bản gốc thì bấm Khôi phục mặc định.")
    state = app_state(request)
    if value == EDITABLE_PROMPTS[key][2]:
        state.config.delete(key)  # identical to the default: keep following the default
    else:
        state.config.set(key, value, admin.name or "")
    return list_prompts(request)


@router.delete("/prompts/{key}")
def reset_prompt(key: str, request: Request) -> dict:
    if key not in EDITABLE_PROMPTS:
        raise HTTPException(404, "Không có prompt này.")
    app_state(request).config.delete(key)
    return list_prompts(request)
