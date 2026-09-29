"""FastAPI app. Dev: `uvicorn api.main:app --reload` (from the repo root), docs at /docs."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request

from geo_draw.ai_codegen import load_dotenv, settings_from_env
from geo_draw.examples import EXAMPLES

from .deps import GUEST_COOKIE, new_guest_id, valid_guest_id
from .routers import auth, conversations, editor, files, messages, settings
from .state import ROOT, AppState

GUEST_MAX_AGE = 60 * 60 * 24 * 30


def create_app(data_dir: Path | None = None, **state_options) -> FastAPI:
    """``data_dir`` defaults to ``$GEO_DRAW_DATA_DIR`` or ``generated/``."""
    load_dotenv(ROOT / ".env")
    if data_dir is None:
        data_dir = Path(os.environ.get("GEO_DRAW_DATA_DIR") or ROOT / "generated")
    state_options.setdefault("ai", settings_from_env())
    state = AppState(data_dir=data_dir, **state_options)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        state.jobs.shutdown()

    app = FastAPI(title="geo-draw API", version="1.0", lifespan=lifespan)
    app.state.geo = state

    @app.middleware("http")
    async def guest_cookie(request: Request, call_next):
        # Everyone gets a guest id, so guests keep their chats until the cookie expires.
        guest_id = request.cookies.get(GUEST_COOKIE)
        issued = None
        if not valid_guest_id(guest_id):
            guest_id = issued = new_guest_id()
        request.state.guest_id = guest_id
        response = await call_next(request)
        if issued:
            response.set_cookie(GUEST_COOKIE, issued, max_age=GUEST_MAX_AGE, httponly=True,
                                samesite="lax", secure=state.cookie_secure, path="/")
        return response

    api = APIRouter(prefix="/api")
    for module in (auth, settings, conversations, messages, files, editor):
        api.include_router(module.router)

    @api.get("/examples", tags=["meta"])
    def examples() -> list[dict]:
        return [{"name": name, "problem": problem} for name, problem in EXAMPLES.items()]

    @api.get("/health", tags=["meta"])
    def health() -> dict:
        return {"ok": True}

    app.include_router(api)
    return app


app = create_app()
