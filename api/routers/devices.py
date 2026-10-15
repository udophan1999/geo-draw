"""Phones that receive push notifications: the app registers its APNs token after sign-in
(and as a guest), and removes it before signing out."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from geo_draw.devices import PRODUCTION

from ..deps import Owner, app_state, get_owner

router = APIRouter(prefix="/devices", tags=["devices"])

_TOKEN = re.compile(r"^[0-9a-fA-F]{64,200}$")


class DeviceRegistration(BaseModel):
    token: str
    platform: Literal["ios"] = "ios"
    environment: Literal["sandbox", "production"] = PRODUCTION


def _valid(token: str) -> str:
    if not _TOKEN.match(token):
        raise HTTPException(422, "Mã thiết bị không hợp lệ.")
    return token.lower()


@router.post("", status_code=204)
def register_device(body: DeviceRegistration, request: Request,
                    owner: Owner = Depends(get_owner)) -> None:
    app_state(request).devices.register(owner.identity, _valid(body.token), body.platform,
                                        body.environment)


@router.delete("/{token}", status_code=204)
def remove_device(token: str, request: Request, owner: Owner = Depends(get_owner)) -> None:
    app_state(request).devices.remove(_valid(token), owner.identity)
