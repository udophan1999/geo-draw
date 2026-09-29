"""The signed-in user's (or guest's) conversations: list, open, rename, delete."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import Owner, get_owner, owned_conversation
from ..schemas import TitleUpdate, conversation_json, message_json

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations(owner: Owner = Depends(get_owner)) -> list[dict]:
    return [conversation_json(c) for c in owner.store.list(owner.store_owner, limit=200)]


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, owner: Owner = Depends(get_owner)) -> dict:
    conversation = owned_conversation(owner, conversation_id)
    return {
        "conversation": conversation_json(conversation),
        "messages": [message_json(m) for m in owner.store.messages(conversation.id)],
    }


@router.patch("/{conversation_id}")
def rename_conversation(conversation_id: str, body: TitleUpdate,
                        owner: Owner = Depends(get_owner)) -> dict:
    owned_conversation(owner, conversation_id)
    owner.store.rename(owner.store_owner, conversation_id, body.title)
    return conversation_json(owned_conversation(owner, conversation_id))


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, owner: Owner = Depends(get_owner)) -> None:
    owned_conversation(owner, conversation_id)
    owner.store.delete(owner.store_owner, conversation_id)
