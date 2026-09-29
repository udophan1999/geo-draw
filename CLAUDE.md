# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit app that takes a Vietnamese middle-school (THCS) plane-geometry problem, as text or as an image, and draws the figure with Manim. The main path sends the problem to DeepSeek, which writes a `GeoScene` Manim module. A local regex parser handles simple figures without any API call. UI strings, error messages and the README are in Vietnamese; keep new user-facing text in Vietnamese.

## Commands

No virtualenv is committed. The README uses Windows paths (`.venv-codex`/`.venv`); on macOS/Linux create one with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

```bash
uvicorn api.main:app --reload                          # API server (http://localhost:8000, docs at /docs)
streamlit run app.py                                   # legacy Streamlit UI (http://localhost:8501)
python -m unittest discover -s tests -v                # all tests
python -m unittest tests.test_geometry_primitives -v   # one file
python -m unittest tests.test_ai_codegen.AiCodegenTests.test_missing_referenced_figure_stops_before_ai_generation  # one test
```

There is no linter or build step. The theme (blue primary color, minimal toolbar) is set in `.streamlit/config.toml`, which is committed; only `.streamlit/secrets.toml` is gitignored. Static renders need only Manim (labels use `Text`, so no LaTeX is required). Video output needs FFmpeg.

DeepSeek configuration is read from `.env` (see `.env.example`: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_VISION_MODEL`, `DEEPSEEK_BASE_URL`) by a small custom `load_dotenv` in `ai_codegen.py`. The API only ever uses this server key; the legacy Streamlit UI still lets users type a key in its settings. Never write the key into scenes, logs or code. The API also reads `GEO_DRAW_DAILY_LIMIT_USER` (default 50), `GEO_DRAW_DAILY_LIMIT_GUEST` (default 5), `GEO_DRAW_COOKIE_SECURE=1` (for HTTPS) and `GEO_DRAW_DATA_DIR`.

## Architecture

### Layout

- `geo_draw/`: the shared core, with no Streamlit imports: geometry, AI code generation, rendering, accounts and chat conversations (`conversations.py`). Two modules serve the UIs directly:
  - `chat.py`: `run_turn`, one chat message end to end: optional OCR, saving the messages, `compose_problem` of all user turns, and `previous_code` from the last drawing. It reports through `on_event`.
  - `pipeline.py`: one drawing turn (DeepSeek or parser → render → up to 3 AI repairs), reporting progress through `on_progress(stage, label)`; it also holds `parser_scene` and `render_error_summary`.
  - `scene_info.py`: what the manual editor needs: label and segment names, `empty_manual_edits()`, and `load_edits`/`save_edits` for `edits.json`. A future `mobile/` app should reuse it.

**Migration in progress:** the Streamlit UI (`streamlit_app/`) is being replaced by a FastAPI server (`api/`) and a React + Vite + TypeScript + Tailwind + shadcn/ui app (`web/`). The plan and its phases live in `/Users/tonyphanx/.claude/plans/iridescent-nibbling-sutherland.md`. Keep new logic in `geo_draw/` so that the API, Streamlit and a future `mobile/` app can all share it. Frontend tooling needs Node 22 (`.nvmrc`); the `/usr/local/bin/node` on this machine is an old v18, so run `nvm use` first.

- `api/`: FastAPI server. `create_app(data_dir, **AppState options)` builds one `AppState` (`api/state.py`), stored at `app.state.geo`, which holds the stores, the quota and the job manager; tests build their own app on a temp dir.
  - **Identity** (`api/deps.py`): an HttpOnly `geo_session` cookie (a token in `AccountStore`'s sessions table) means a signed-in user. Otherwise the caller is a guest, identified by a `geo_guest` cookie that middleware issues to everyone. `Owner` bundles the conversation store, the store's owner column, the workspace and `identity` (the key used for quota and jobs). Always load data through `owned_conversation` / `owned_message`, which return 404 for other people's data.
  - **Chat turn**: `POST /api/messages` (multipart: `text`, optional `conversation_id`, optional `image`) checks ownership, then quota, then starts `geo_draw.chat.run_turn` in `JobManager` (a pool of 2 threads) and returns `{conversation, job_id}` at once. `GET /api/jobs/{id}/events` is SSE with `message` (saved message JSON), `progress`, then `done` or `error`. The job saves its results itself, so a closed tab loses nothing.
  - **Quota** (`api/quota.py`): each AI turn (drawing or OCR) costs one unit of a daily limit per identity, stored in `usage.sqlite3`; it returns 429 when the limit is used up. Parser turns are free. When there is no server key, AI mode returns 503.
  - JSON shapes live in `api/schemas.py` (`message_json` adds `image_url`/`video_url` with a `?v=` cache-busting version, since a re-render writes a new file). Settings are stored per workspace in `settings.json`, with `mode` `"ai"`/`"parser"`; `load_settings` also accepts the Streamlit app's Vietnamese mode labels.
- `streamlit_app/`: the legacy Streamlit UI. It stays runnable until the React app reaches parity.
  - `streamlit_app/app.py`: routes and the access guard, built with `st.navigation(position="hidden")`. `/login` is the login/register page, `/dashboard` is the main page, and `/` redirects. Anyone who is not signed in and not in anonymous mode is sent to `/login`; anyone else who opens `/login` or `/` is sent to `/dashboard`. The redirects use `st.switch_page` and always carry `?session=<token>`. All access checks live here; views never redirect themselves. Pages are created inside `main()` on every run, because `st.Page` needs a script-run context.
  - `streamlit_app/config.py`: data paths, the shared `ACCOUNTS`, `CONVERSATIONS` and legacy `HISTORY` stores, and the example problems.
  - `streamlit_app/session.py`: per-session state: the current user, the workspace folder, the open conversation and which drawing is shown.
  - `streamlit_app/settings.py`: `DrawOptions` (mode, API key, model, quality, video), set in the settings dialog.
  - `streamlit_app/drawing.py`: a thin wrapper that shows `geo_draw.pipeline.draw` progress in `st.status`.
  - `streamlit_app/styles.py`: CSS for things Streamlit has no option for: the sidebar layout with the account box at the bottom, and one-line chat titles.
  - `streamlit_app/auth.py`: login, register and logout callbacks.
  - `streamlit_app/views/`: the pages, `login.py` and `dashboard.py`. The folder is not called `pages/`, because Streamlit treats a `pages/` folder as multipage routing.
  - `streamlit_app/components/`: the sidebar (chat list and account box), the settings dialog, the zoomable image and the manual editor.
- `app.py` at the root only calls `streamlit_app.app.main()`, so the app is still started with `streamlit run app.py` from the repo root. The Manim subprocess imports `geo_draw` from the working directory, so the app must be started from the repo root.

Modules import each other as modules (`from streamlit_app import session` → `session.workspace()`). The dependency order is `config` → `session` → `settings`/`auth`/`rendering` → `drawing` → `components` → `views` → `app`; keep it one-way.

### Rendering

Every render is a **subprocess**: `renderer.render_scene` runs `python -m manim render <scene.py> GeoScene` into a fresh `<message folder>/media/run-<uuid>/` directory (see below). The separate directory exists because Windows keeps displayed files locked. State passes from the app to the scene only through environment variables:
- `GEO_DRAW_LABEL_OFFSETS`: per-label nudges, read by `safe_point_label`.
- `GEO_DRAW_MANUAL_EDITS`: hidden labels, points and segments, added segments, stroke widths and manual constructions (perpendicular, angle bisector, perpendicular bisector, median). These are applied inside `fit_scene_to_frame`.

Because of this, the "Chỉnh hình thủ công" editor (`streamlit_app/components/manual_editor.py`) re-renders the *same* scene file locally without calling DeepSeek. Any new manual-edit feature must be added in three places: `scene_info.empty_manual_edits()`, the env var, and the handling code in `geometry_primitives.py`.

### Two generation paths

1. **Parser path** (no API): `parser.parse_problem` (regex, produces `Problem`) → `engine.build_figure` (coordinates, produces `Figure`) → `scene_builder.write_scene` (emits a simple Manim module).
2. **AI path** (`ai_codegen.generate_manim_code`):
   - `missing_reference_figure_points` refuses early when the problem refers to a numbered "Hình" whose points are never located in the text. `_drawing_facts_text` removes the proof goals ("Chứng minh…") so that they don't count as drawing facts.
   - DeepSeek is called with `SYSTEM_PROMPT`, which is built from the inline rules, `MIDDLE_SCHOOL_GEOMETRY_RULES` and `DRAWING_ERROR_MEMORY` from `geometry_knowledge.py`.
   - The reply goes through `extract_python`, then `_ensure_light_theme` (injects `apply_light_theme(self)`), then `sanitize_code` (auto-injects parallel and ordinary-polygon verifier calls), then `validate_code`.
   - When validation fails, the error is sent back to DeepSeek, up to 3 retries in the same conversation.
   - In `geo_draw/pipeline.py` (`draw`), a failed Manim render triggers up to 3 more `generate_manim_code(..., repair_log=...)` calls that include the render log and the previous code. The README says "once"; the code is authoritative.

`extract_problem_from_image` uses the vision model for OCR only. It returns the problem text, which the user reviews before drawing.

### Safety and correctness gate: `validate_code`

`validate_code` (about 1000 lines in `ai_codegen.py`) is an AST-based check. It is not a sandbox. It enforces two things:
- **Safety**: only `manim`, `numpy` and `geo_draw` imports; blocked names such as `open`, `eval`, `os` and `getattr`; blocked node types such as `Try`, `While`, `With` and `Delete`; no statements at module level.
- **Geometric completeness and correctness** against the problem text: every named point must be an uppercase variable with a Dot and a `safe_point_label`; no `DashedLine`; the verified helpers must be used with the right arguments; right-angle, equal-segment, midpoint and angle markers must match the given facts; `fit_scene_to_frame(self)` must run last.

The error messages it raises are sent back to the LLM verbatim, so they need to be actionable.

### Verified helpers: `geometry_primitives.py`

The AI-generated scenes import these helpers. Examples: `safe_point_label`, `interior_angle_marker`, `equal_segment_marks`, `midpoint_marker`, `angle_bisector_segment`, `perpendicular_intersection_marker`, `equilateral_triangle_check`, `ordinary_polygon_check`, `layout_spacing_check` and `fit_scene_to_frame`.

`apply_light_theme` clears the module-global `_NAMED_POINTS` registry and patches `scene.add` to force black ink. `safe_point_label` records each point in that registry, and the manual edits look points up by name there.

Helpers raise `ValueError`s with codes such as `GEOMETRY_LAYOUT_CROWDED`, `GEOMETRY_ACCIDENTAL_SPECIAL`, `GEOMETRY_INVALID_SEGMENT` and `GEOMETRY_PARALLEL_NO_SEGMENT`. The repair prompt and `geo_draw.pipeline.render_error_summary` match on these codes, so keep them stable.

### Users and accounts

The app opens on a separate login screen (`streamlit_app/views/login.py`); `streamlit_app/app.py` sends the user to `/dashboard` only when the user is signed in or has clicked "Dùng thử không cần tài khoản →" (`session_state["anonymous_mode"]`). Anonymous users see the notice "Đăng nhập để lưu lại lịch sử hỏi đáp" on the main page, with a button back to the login screen. Signing in clears `render_state_restored`, so the account's last drawing is restored. Accounts are a username and password (6–64 characters), managed by `geo_draw/accounts.py` (`AccountStore`, `generated/users/accounts.sqlite3`). The login screen is one fixed-width (380px) card whose content is switched by `session_state["auth_view"]` (`"login"` or `"register"`); there are no tabs:
- **Đăng nhập** (`auth.submit_login`): for a wrong password and for an unknown username it shows the same message, "Sai tên đăng nhập hoặc mật khẩu." After 5 wrong passwords the username is locked for 5 minutes; the lock is stored in the database, not in the session.
- **Đăng ký** (`auth.submit_register`): usernames are unique ignoring case and extra spaces. A taken name shows an error plus three free suggestions; clicking a suggestion fills the username field.

Passwords are stored as salted PBKDF2 hashes; the column is still called `code_hash` so that existing databases keep working. After sign-in the URL carries a random session token (`?session=...`, looked up in the `sessions` table) so that a reload keeps the user signed in. Never put the name itself in the URL, because that would bypass the password. `auth.logout` deletes the token and clears the displayed drawing. `user_id` is `history.user_id_for(name.casefold())`.

### Dashboard = chat

`/dashboard` (`streamlit_app/views/dashboard.py`) has two columns: the chat on the left and the drawing on the right. The sidebar holds "Cuộc trò chuyện mới", the list of conversations, and an account box at the bottom. For signed-in users the account box is a popover with "Cài đặt" (a `st.dialog`) and "Đăng xuất". For guests it shows "Đăng nhập để lưu lại lịch sử hỏi đáp", a login button and ⚙️.

- **Continuous chat**: the first user message is the problem, and later messages are extra requests. Every turn redraws `compose_problem(all user texts)` ("…\n\nYêu cầu bổ sung (áp dụng theo thứ tự): 1. …"). The previous drawing's code is passed as `generate_manim_code(..., previous_code=...)` so DeepSeek keeps the layout. To start a different problem, the user opens a new conversation.
- **Images**: `st.chat_input(accept_file=True)` handles 📎, drag-and-drop and Ctrl+V paste. An attached image goes through OCR, and the recognized text (plus any typed text) becomes that turn's request. OCR needs DeepSeek AI mode and a key.
- **Storage** (`geo_draw/conversations.py`): `ConversationStore` keeps conversations and messages in SQLite. Every message can own a folder `<root>/<owner>/conversations/<cid>/<mid>/` holding the pasted image, or the `scene.py` and `media/` of a drawing. A message is a drawing when it is an assistant message with both `scene_path` and `image_path`. Signed-in users use `config.CONVERSATIONS` (root `generated/users/`, owner = user_id). Guests get a store inside their session folder (`generated/sessions/<id>/`, owner `guest`), so nothing is kept after the session.
- **Right panel**: shows the newest drawing, or the one picked with "Xem hình này" (`session_state["viewing_message_id"]`), with zoom, video, the manual editor, the code and the log. The manual editor re-renders into that message's folder, calls `update_drawing`, and saves its state in `edits.json` next to the scene so that edits accumulate across reloads.
- **Settings**: kept in `session_state["settings"]`. For signed-in users they are also written to `<workspace>/settings.json` (`generated/users/<user_id>/`), but the API key is never written to disk. Signing in or out clears the open conversation and the settings, including a typed key.
- **Legacy history**: drawings saved by the old `HistoryStore` (`history.sqlite3`) are imported once per session as one-turn conversations with id `h<entry id>`. The import is idempotent.
- Streamlit keeps the imported `streamlit_app.*` modules in memory, so a running server may keep serving the old UI after an edit. Restart the server to be sure.

To drive the app in tests, use `streamlit.testing.v1.AppTest` and **always set `GEO_DRAW_DATA_DIR` to a temporary folder**. Without it, the run writes accounts, history and renders into the real `generated/` folder, which holds the user's data. To simulate a signed-in user, create the account with `AccountStore(...).create(...)` and `start_session(...)`, then set `at.query_params["session"] = token` before `run()`. `AppTest` always starts on the default route `/`, and its `switch_page()` only handles file-based pages. Before interacting with the dashboard, run the app once and then select the route with `at._page_hash = next(h for h, i in at._registered_pages.items() if i.get("url_pathname") == "dashboard")` (a private API). Without this step, every rerun goes through the `/` redirect and button clicks are lost. Check the URLs and redirects themselves in a real browser. When a test creates several `AppTest` instances in one process, delete the `web` and `streamlit_app.*` entries from `sys.modules` before each one. Each AppTest has its own runtime, and the paste-image component is registered when its module is imported (the pattern Streamlit recommends). Without the reload you get "Component 'geo_draw_clipboard_image' is not registered"; this only happens in tests, not on a real server.

## Drawing rules (from `.cursor/rules/geo-draw-regressions.mdc`, always applied)

These encode drawing bugs that were already fixed. Any change to the prompt, the validator or the helpers must preserve them. Every newly fixed geometry bug gets a regression test in `tests/` and, where relevant, a line in `DRAWING_ERROR_MEMORY`.

- Keep every fact and object stated in the problem; later constructions must never remove earlier ones.
- White background; strokes, dots, labels and marks are black. All lines are solid (no dashes), and segments have no arrowheads.
- Equilateral triangles are checked numerically before rendering. Do not automatically add tick marks to their sides.
- Angle markers go inside the polygon, one per angle. Unequal angles get different arc counts, and equal angles get the same arc style. When a vertex has several sub-angles, number them 1, 2 next to the arcs.
- An angle bisector is one solid stroke from the vertex, through any intersections, to the first boundary edge of the figure.
- Draw a right-angle square only for a *given* perpendicularity, never for something that is to be proved. Draw exactly one square per given relation.
- Equal segments share a tick count, and groups that are not equal never share a style. A midpoint marks both halves correctly with no extra ticks on top. If one half contains another named point, hide both ticks and verify by coordinates only. Midpoints of equal segments share a style; independent midpoint relations use different styles.
- Do not mark the equal sides of a parallelogram, rectangle, square or rhombus unless the problem asks for it. Parallel marks are for verification only, with no arrows on segments.
- Extend lines to meet at an intersection outside a segment when the problem says they intersect there.
- Every point in the problem is constructed, dotted and labelled. Labels never touch lines, extensions or marks. Inner intersection labels (E, F, G, H…) stay close to their dots.
- The figure must be balanced, roomy, fully inside the frame and still zoomable.
