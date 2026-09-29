"""FastAPI app. Dev: `uvicorn api.main:app --reload` (from the repo root), docs at /docs."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from geo_draw.ai_codegen import load_dotenv, settings_from_env
from geo_draw.examples import MATH_EXAMPLES
from geo_draw.geometry_knowledge import GEOMETRY_HELP_VI

from .deps import GUEST_COOKIE, new_guest_id, valid_guest_id
from .routers import auth, conversations, editor, files, messages, settings
from .state import ROOT, AppState

GUEST_MAX_AGE = 60 * 60 * 24 * 30


def create_app(data_dir: Path | None = None, web_dist: Path | None = ROOT / "web" / "dist",
               **state_options) -> FastAPI:
    """``data_dir`` defaults to ``$GEO_DRAW_DATA_DIR`` or ``generated/``.

    When the React app has been built (``npm --prefix web run build``), ``web_dist`` is served
    too, so production needs only this one server.
    """
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
        """Sample problems for the empty chat: ``topic``, ``name``, ``problem``."""
        return MATH_EXAMPLES

    @api.get("/help", tags=["meta"])
    def geometry_help() -> dict:
        """The THCS drawing conventions shown in the settings dialog (Markdown)."""
        return {"markdown": GEOMETRY_HELP_VI.strip()}

    @api.get("/health", tags=["meta"])
    def health() -> dict:
        return {"ok": True}

    app.include_router(api)
    if web_dist is not None and (web_dist / "index.html").is_file():
        _serve_web_app(app, web_dist.resolve())
    return app


def _serve_web_app(app: FastAPI, dist: Path) -> None:
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404, "Không tìm thấy.")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):
            return FileResponse(file)  # favicon and other files in web/public
        # Client-side routes (/login, /c/<id>, ...) all load the single-page app.
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
