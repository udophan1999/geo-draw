"""Who is calling: a signed-in user (session cookie) or a guest (guest cookie)."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, Request

from geo_draw.conversations import Conversation, ConversationStore, Message

from .state import AppState

SESSION_COOKIE = "geo_session"
GUEST_COOKIE = "geo_guest"
GUEST_OWNER = "guest"
_GUEST_ID = re.compile(r"^[0-9a-f]{24}$")


def new_guest_id() -> str:
    return secrets.token_hex(12)


def valid_guest_id(value: str | None) -> bool:
    # Guest ids become folder names, so accept nothing but our own hex format.
    return bool(value and _GUEST_ID.match(value))


@dataclass
class Owner:
    user_id: str | None
    guest_id: str
    name: str | None
    store: ConversationStore
    workspace: Path

    @property
    def is_guest(self) -> bool:
        return self.user_id is None

    @property
    def store_owner(self) -> str:
        """The owner column used inside ``store``."""
        return self.user_id or GUEST_OWNER

    @property
    def identity(self) -> str:
        """A key that is unique across users and guests (quota, jobs)."""
        return self.user_id or f"guest:{self.guest_id}"


def app_state(request: Request) -> AppState:
    return request.app.state.geo


def user_owner(state: AppState, user_id: str) -> Owner:
    return Owner(user_id, "", state.accounts.display_name(user_id), state.conversations,
                 state.users_dir / user_id)


def get_owner(request: Request) -> Owner:
    state = app_state(request)
    token = request.cookies.get(SESSION_COOKIE, "")
    user_id = state.accounts.session_user(token) if token else None
    if user_id:
        state.import_history(user_id)
        return user_owner(state, user_id)
    guest_id = request.state.guest_id  # set by the guest-cookie middleware
    return Owner(None, guest_id, None, state.guest_store(guest_id),
                 state.sessions_dir / guest_id)


def owned_conversation(owner: Owner, conversation_id: str) -> Conversation:
    conversation = owner.store.get(owner.store_owner, conversation_id)
    if conversation is None:
        raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
    return conversation


def owned_message(owner: Owner, message_id: str) -> Message:
    message = owner.store.get_message(message_id)
    if message is None or owner.store.get(owner.store_owner, message.conversation_id) is None:
        raise HTTPException(404, "Không tìm thấy tin nhắn.")
    return message
