# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Streamlit app that takes a Vietnamese middle-school (THCS) plane-geometry problem, as text or as an image, and draws the figure with Manim. The main path sends the problem to DeepSeek, which writes a `GeoScene` Manim module. A local regex parser handles simple figures without any API call. UI strings, error messages and the README are in Vietnamese; keep new user-facing text in Vietnamese.

## Commands

No virtualenv is committed. The README uses Windows paths (`.venv-codex`/`.venv`); on macOS/Linux create one with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

```bash
streamlit run app.py                                   # run the app (http://localhost:8501)
python -m unittest discover -s tests -v                # all tests
python -m unittest tests.test_geometry_primitives -v   # one file
python -m unittest tests.test_ai_codegen.AiCodegenTests.test_missing_referenced_figure_stops_before_ai_generation  # one test
```

There is no linter or build step. The theme (blue primary color, minimal toolbar) is set in `.streamlit/config.toml`, which is committed; only `.streamlit/secrets.toml` is gitignored. Static renders need only Manim (labels use `Text`, so no LaTeX is required). Video output needs FFmpeg.

DeepSeek configuration is read from `.env` (see `.env.example`: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_VISION_MODEL`, `DEEPSEEK_BASE_URL`) by a small custom `load_dotenv` in `ai_codegen.py`. The key can also be entered in the sidebar. Never write the key into scenes, logs or code.

## Architecture

### Layout

- `geo_draw/`: the shared core, with no Streamlit imports: geometry, AI code generation, rendering, accounts and history. A future `mobile/` app should reuse it.
- `web/`: the Streamlit UI.
  - `web/app.py`: routing. The login page is shown until the user signs in or chooses anonymous mode; after that the main page is shown.
  - `web/config.py`: data paths, the shared `ACCOUNTS` and `HISTORY` stores, and the example problems.
  - `web/session.py`: per-session state: the current user, the workspace folder, and saving or restoring the last drawing.
  - `web/auth.py`: login, register and logout callbacks.
  - `web/rendering.py`: `parser_scene` and `render_error_summary`.
  - `web/views/`: the pages, `login.py` and `main.py`. The folder is not called `pages/`, because Streamlit treats a `pages/` folder as multipage routing.
  - `web/components/`: the paste-image component, the zoomable image, the manual editor and the sidebar sections (`DrawOptions` comes from `options_section`).
- `app.py` at the root only calls `web.app.main()`, so the app is still started with `streamlit run app.py` from the repo root. The Manim subprocess imports `geo_draw` from the working directory, so the app must be started from the repo root.

Modules import each other as modules (`from web import session` → `session.workspace()`). The dependency order is `config` → `session`/`auth`/`rendering` → `components` → `views` → `app`; keep it one-way.

### Rendering

Every render is a **subprocess**: `renderer.render_scene` runs `python -m manim render <scene.py> GeoScene` into a fresh `<workspace>/media/run-<uuid>/` directory (see below). The separate directory exists because Windows keeps displayed files locked. State passes from the app to the scene only through environment variables:
- `GEO_DRAW_LABEL_OFFSETS`: per-label nudges, read by `safe_point_label`.
- `GEO_DRAW_MANUAL_EDITS`: hidden labels, points and segments, added segments, stroke widths and manual constructions (perpendicular, angle bisector, perpendicular bisector, median). These are applied inside `fit_scene_to_frame`.

Because of this, the "Chỉnh hình thủ công" editor (`web/components/manual_editor.py`) re-renders the *same* scene file locally without calling DeepSeek. Any new manual-edit feature must be added in three places: `session.empty_manual_edits()`, the env var, and the handling code in `geometry_primitives.py`.

### Two generation paths

1. **Parser path** (no API): `parser.parse_problem` (regex, produces `Problem`) → `engine.build_figure` (coordinates, produces `Figure`) → `scene_builder.write_scene` (emits a simple Manim module).
2. **AI path** (`ai_codegen.generate_manim_code`):
   - `missing_reference_figure_points` refuses early when the problem refers to a numbered "Hình" whose points are never located in the text. `_drawing_facts_text` removes the proof goals ("Chứng minh…") so that they don't count as drawing facts.
   - DeepSeek is called with `SYSTEM_PROMPT`, which is built from the inline rules, `MIDDLE_SCHOOL_GEOMETRY_RULES` and `DRAWING_ERROR_MEMORY` from `geometry_knowledge.py`.
   - The reply goes through `extract_python`, then `_ensure_light_theme` (injects `apply_light_theme(self)`), then `sanitize_code` (auto-injects parallel and ordinary-polygon verifier calls), then `validate_code`.
   - When validation fails, the error is sent back to DeepSeek, up to 3 retries in the same conversation.
   - In `web/views/main.py` (`_draw`), a failed Manim render triggers up to 3 more `generate_manim_code(..., repair_log=...)` calls that include the render log and the previous code. The README says "once"; the code is authoritative.

`extract_problem_from_image` uses the vision model for OCR only. It returns the problem text, which the user reviews before drawing.

### Safety and correctness gate: `validate_code`

`validate_code` (about 1000 lines in `ai_codegen.py`) is an AST-based check. It is not a sandbox. It enforces two things:
- **Safety**: only `manim`, `numpy` and `geo_draw` imports; blocked names such as `open`, `eval`, `os` and `getattr`; blocked node types such as `Try`, `While`, `With` and `Delete`; no statements at module level.
- **Geometric completeness and correctness** against the problem text: every named point must be an uppercase variable with a Dot and a `safe_point_label`; no `DashedLine`; the verified helpers must be used with the right arguments; right-angle, equal-segment, midpoint and angle markers must match the given facts; `fit_scene_to_frame(self)` must run last.

The error messages it raises are sent back to the LLM verbatim, so they need to be actionable.

### Verified helpers: `geometry_primitives.py`

The AI-generated scenes import these helpers. Examples: `safe_point_label`, `interior_angle_marker`, `equal_segment_marks`, `midpoint_marker`, `angle_bisector_segment`, `perpendicular_intersection_marker`, `equilateral_triangle_check`, `ordinary_polygon_check`, `layout_spacing_check` and `fit_scene_to_frame`.

`apply_light_theme` clears the module-global `_NAMED_POINTS` registry and patches `scene.add` to force black ink. `safe_point_label` records each point in that registry, and the manual edits look points up by name there.

Helpers raise `ValueError`s with codes such as `GEOMETRY_LAYOUT_CROWDED`, `GEOMETRY_ACCIDENTAL_SPECIAL`, `GEOMETRY_INVALID_SEGMENT` and `GEOMETRY_PARALLEL_NO_SEGMENT`. The repair prompt and `web.rendering.render_error_summary` match on these codes, so keep them stable.

### Users, workspaces and history

The app opens on a separate login screen (`web/views/login.py`); `web/app.py` renders the main page only when the user is signed in or has clicked "Dùng ngay, không cần đăng nhập" (`session_state["anonymous_mode"]`). Anonymous users see the notice "Đăng nhập để lưu lại lịch sử hỏi đáp" on the main page, with a button back to the login screen. Signing in clears `render_state_restored`, so the account's last drawing is restored. Accounts are a username and password (6–64 characters), managed by `geo_draw/accounts.py` (`AccountStore`, `generated/users/accounts.sqlite3`). The login screen is one fixed-width (380px) card whose content is switched by `session_state["auth_view"]` (`"login"` or `"register"`); there are no tabs:
- **Đăng nhập** (`auth.submit_login`): for a wrong password and for an unknown username it shows the same message, "Sai tên đăng nhập hoặc mật khẩu." After 5 wrong passwords the username is locked for 5 minutes; the lock is stored in the database, not in the session.
- **Đăng ký** (`auth.submit_register`): usernames are unique ignoring case and extra spaces. A taken name shows an error plus three free suggestions; clicking a suggestion fills the username field.

Passwords are stored as salted PBKDF2 hashes; the column is still called `code_hash` so that existing databases keep working. After sign-in the URL carries a random session token (`?session=...`, looked up in the `sessions` table) so that a reload keeps the user signed in. Never put the name itself in the URL, because that would bypass the password. `auth.logout` deletes the token and clears the displayed drawing. `user_id` is `history.user_id_for(name.casefold())`.

All render files go in a per-user workspace (`session.workspace()`), never directly in `generated/`:
- Signed-in user: `generated/users/<user_id>/`. This folder persists across sessions.
- Anonymous user: `generated/sessions/<random id kept in session_state>/`. Nothing is restored after a restart.

Each workspace holds `scene.py`, `media/run-*/` and `last_render.json`; the last of these restores the last problem, scene and image after a Streamlit restart. For signed-in users, every successful drawing is also saved by `geo_draw/history.py` (`HistoryStore`): a row in `generated/users/history.sqlite3` plus copies of the scene and image under `<user_id>/history/<entry_id>/`. The copies are needed because the next drawing overwrites `scene.py`. The history list is in the sidebar, and opening an entry is a button `on_click` callback.

Use `session.empty_manual_edits()` to create or reset the manual-edits dict. Do not assign `st.session_state["problem"]` after the text area is created in the same run, because Streamlit raises `StreamlitWidgetAlreadyInstantiatedError` (see the comment in `session.save_render_state`); set it from a callback or earlier in the run. `generated/` is gitignored.

To drive the app in tests, use `streamlit.testing.v1.AppTest` and **always set `GEO_DRAW_DATA_DIR` to a temporary folder**. Without it, the run writes accounts, history and renders into the real `generated/` folder, which holds the user's data. To simulate a signed-in user, create the account with `AccountStore(...).create(...)` and `start_session(...)`, then set `at.query_params["session"] = token` before `run()`. When a test creates several `AppTest` instances in one process, delete the `web` and `web.*` entries from `sys.modules` before each one. Each AppTest has its own runtime, and the paste-image component is registered when its module is imported (the pattern Streamlit recommends). Without the reload you get "Component 'geo_draw_clipboard_image' is not registered"; this only happens in tests, not on a real server.

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
