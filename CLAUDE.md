# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Vietnamese math tutor (THCS–THPT) that also draws geometry figures. A student sends a problem (text or photo). The tutor, ported from the MathLovers project, gives Socratic hints level by level, or a worked solution when asked. For plane-geometry problems the figure is drawn automatically with Manim: DeepSeek writes a `GeoScene` module, or a local regex parser handles simple figures without any API call. UI strings, error messages and the README are in Vietnamese; keep new user-facing text in Vietnamese.

The app is shown to users as **MathMate** (`geo_draw/branding.py` `APP_NAME`, `web/src/lib/brand.ts`, `web/index.html`). User-facing text says "MathMate" or "AI" and never names the AI provider; "DeepSeek" appears only in code, config and the legacy Streamlit UI. The repo and package keep the name geo-draw.

## Commands

No virtualenv is committed. The README uses Windows paths (`.venv-codex`/`.venv`); on macOS/Linux create one with `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

```bash
./start.sh                                             # build web if changed + serve API and app on :8000 (PORT, HOST env)
./start.sh dev                                         # uvicorn --reload on :8000 + Vite on :5173 (Ctrl+C stops both)
uvicorn api.main:app --reload                          # API server (http://localhost:8000, docs at /docs)
nvm use && npm --prefix web install                    # frontend deps (Node 22)
npm --prefix web run dev                               # React dev server (http://localhost:5173, proxies /api to :8000)
npm --prefix web run build                             # build web/dist; uvicorn then serves the app itself
npx --prefix web tsc -b web && npm --prefix web run lint    # type-check + oxlint
streamlit run app.py                                   # legacy Streamlit UI (http://localhost:8501)
python -m unittest discover -s tests -v                # all tests
python -m unittest tests.test_geometry_primitives -v   # one file
python -m unittest tests.test_ai_codegen.AiCodegenTests.test_missing_referenced_figure_stops_before_ai_generation  # one test
```

There is no linter or build step. The theme (blue primary color, minimal toolbar) is set in `.streamlit/config.toml`, which is committed; only `.streamlit/secrets.toml` is gitignored. Static renders need only Manim (labels use `Text`, so no LaTeX is required). Video output needs FFmpeg.

DeepSeek configuration is read from `.env` (see `.env.example`: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_VISION_MODEL`, `DEEPSEEK_BASE_URL`) by a small custom `load_dotenv` in `ai_codegen.py`. The API only ever uses this server key; the legacy Streamlit UI still lets users type a key in its settings. Never write the key into scenes, logs or code. The API also reads `GEO_DRAW_DAILY_LIMIT_USER` (default 100), `GEO_DRAW_DAILY_LIMIT_GUEST` (default 10), `GEO_DRAW_COOKIE_SECURE=1` (for HTTPS) and `GEO_DRAW_DATA_DIR`.

## Architecture

### Layout

- `geo_draw/`: the shared core, with no Streamlit imports: geometry, AI code generation, rendering, accounts and chat conversations (`conversations.py`). Two modules serve the UIs directly:
  - `tutor.py` + `tutor_prompts.py`: the math tutor (see **Math tutor** below). `is_geometry_problem` decides whether a figure is drawn automatically.
  - `chat.py`: `run_figure_turn`, one drawing turn in the `figure` channel. It draws `compose_problem([problem, *figure requests])` with `previous_code` from the last drawing and reports through `on_event`.
  - `pipeline.py`: one drawing turn (DeepSeek or parser → render → up to 3 AI repairs), reporting progress through `on_progress(stage, label)`; it also holds `parser_scene` and `render_error_summary`.
  - `scene_info.py`: what the manual editor needs: label and segment names, `empty_manual_edits()`, and `load_edits`/`save_edits` for `edits.json`. A future `mobile/` app should reuse it.

**Migration in progress:** the Streamlit UI (`streamlit_app/`) is being replaced by a FastAPI server (`api/`) and a React + Vite + TypeScript + Tailwind + shadcn/ui app (`web/`). The plan and its phases live in `/Users/tonyphanx/.claude/plans/iridescent-nibbling-sutherland.md`. Keep new logic in `geo_draw/` so that the API, Streamlit and a future `mobile/` app can all share it. Frontend tooling needs Node 22 (`.nvmrc`); the `/usr/local/bin/node` on this machine is an old v18, so run `nvm use` first.

- `api/`: FastAPI server. `create_app(data_dir, **AppState options)` builds one `AppState` (`api/state.py`), stored at `app.state.geo`, which holds the stores, the quota and the job manager; tests build their own app on a temp dir.
  - **Identity** (`api/deps.py`): an HttpOnly `geo_session` cookie (a token in `AccountStore`'s sessions table) means a signed-in user. Otherwise the caller is a guest, identified by a `geo_guest` cookie that middleware issues to everyone. `Owner` bundles the conversation store, the store's owner column, the workspace and `identity` (the key used for quota and jobs). Always load data through `owned_conversation` / `owned_message`, which return 404 for other people's data.
  - **Turns run as jobs** (`api/routers/messages.py`) in `JobManager`, a pool of 2 threads, and return `{…, job_id}` at once. The job saves its results itself, so a closed tab loses nothing.
    - `POST /api/messages` (multipart: `text`, `conversation_id?`, `image?`, `action` = `ask`/`deeper`/`solution`/`hint`) starts a tutor turn after checking ownership, then the server key (503), then quota. On the first message of a plane-geometry problem it also starts a figure job and announces it as `figure_job` (or `figure_skipped` if quota or settings prevent it).
    - `POST /api/conversations/{id}/figure` (`{text}`) draws the figure or refines it.
    - `GET /api/jobs/{id}/events` is SSE with `progress`, `delta` (tutor text), `message` (saved message JSON), `conversation`, `figure_job`, then `done` or `failed` (not `error`, which `EventSource` reserves for connection problems).
  - **Quota** (`api/quota.py`): every tutor turn and every AI drawing costs one unit of a daily limit per identity, stored in `usage.sqlite3`; it returns 429 when the limit is used up. Parser drawings are free. The tutor always needs the server key (503 without it); the `mode` setting only chooses how figures are drawn.
  - JSON shapes live in `api/schemas.py` (`message_json` adds `image_url`/`video_url` with a `?v=` cache-busting version, since a re-render writes a new file). Settings are stored per workspace in `settings.json`, with `mode` `"ai"`/`"parser"`; `load_settings` also accepts the Streamlit app's Vietnamese mode labels.
- `web/`: React 19 + Vite + TypeScript, with Tailwind v4 and shadcn/ui (radix-nova preset; generated components live in `src/components/ui/`, add more with `npx shadcn@latest add <name>`). Routes (React Router 8, `src/main.tsx`): `/login` and `/register` (`routes/auth.tsx`), then `AppLayout`, which guards `/` and `/c/:conversationId` (`routes/ChatPage.tsx`). A visitor without an account is sent to `/login` unless they chose "Dùng thử", stored in localStorage (`lib/guest.ts`).
  - `lib/api.ts`: the typed API client and `followJob` (an `EventSource` on the job events). Reuse it for mobile.
  - `lib/queries.ts`: TanStack Query hooks and keys. `upsertMessage` patches a cached conversation from SSE events or re-renders.
  - `lib/chat.tsx`: `ChatProvider` sits above the routes and tracks running jobs. `pending[conversationId]` is a tutor turn (optimistic user bubble, progress label, `reply` streamed from `delta` events). `figures[conversationId]` is a drawing job, and figure jobs announced by `figure_job` are followed too. It navigates from `/` to `/c/:id` when a turn creates a conversation, and re-fetches the conversation when a job ends.
  - `components/`: `Sidebar` (conversation list with rename/delete, account menu at the bottom), `SettingsDialog`, `MathMarkdown` (react-markdown + remark-math + rehype-katex, for every message; `lib/math.ts` `normalizeMath` first turns `\[…\]`/`\(…\)` into `$$`/`$`, puts every `$$…$$` on its own lines, and replaces `\tag{n}` with `\qquad (n)`, because DeepSeek writes `$$…\tag{1}$$` mid-sentence and KaTeX rejects `\tag` inline), `chat/` (`MessageList` with the `chat` channel only, `TutorBar` (the strip on top of the Composer: Gợi ý/Lời giải switch, a 5-dot hint level and "Gợi ý sâu hơn"; the Composer's `actions` slot shows "Vẽ hình" when there is no figure panel), and `Composer` with paste/drag-drop/📎 images. The Composer also has a symbol bar that inserts Unicode (², √, ≤, ⊥, ∠…) and a ∑ formula editor, `chat/MathInput.tsx`. The editor is MathLive, lazy-loaded (a ~220 kB gzipped chunk), with a Word-like gallery of templates in `chat/formulaTemplates.ts`: 7 tabs, where `#?` is an empty slot and `#@` takes the selection. The gallery inserts through `mathfield.insert(latex, {selectionMode: 'placeholder'})`, and its tiles are drawn with `katex.renderToString`. and inserts the formula with surrounding spaces. Simple formulas become plain Unicode through `lib/plainMath.ts` `latexToPlain` (`BC^2=AB^2+AC^2` → `BC²=AB²+AC²`); others stay `$latex$`, and the Composer then shows a KaTeX "Xem trước" preview above the textarea. `fontsDirectory = null` reuses the KaTeX fonts that the chat page already loads, so there is no CDN.), and `drawing/` (`DrawingPanel` with versions, tabs and the "Yêu cầu chỉnh hình" box, shown only for geometry problems or once a figure exists; `ZoomImage`, `ManualEditor`, a port of the Streamlit editor that commits edits only after a successful re-render).
  - `lib/version.ts`: every build writes `/version.json` with the build id (Vite plugin in `vite.config.ts`, also compiled in as `__BUILD_ID__`). An open tab checks it on focus and every 5 minutes, and shows a "Tải lại" toast when it changed, so a stale tab never talks to a newer API with an old UI.
  - In production `api/main.py` serves `web/dist` when it exists, and unknown non-`/api` paths return `index.html`.
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

### Generation paths

`pipeline.draw` first calls `graphing.drawing_kind(problem)`:
- `"geometry"` goes to the parser or geometry AI path below;
- `"graph"` (hàm số, đồ thị, tích phân, `∫`, `y =`) goes to `graphing.generate_graph_code`. That path uses its own `GRAPH_PROMPT` (Axes, `axes.plot`, `axes.get_area`, `Text` labels only because there is no LaTeX) and `validate_graph_code`, which applies the safety checks and bans MathTex, `include_numbers` and the axis-label helpers. It needs the AI; the parser cannot draw graphs;
- `None` (for example a plain equation) is refused with `NOT_DRAWABLE`, without calling the AI. `api/routers/messages.start_figure_job` makes the same check before it spends quota. Without this, the geometry prompt invented a triangle for an integral.


1. **Parser path** (no API): `parser.parse_problem` (regex, produces `Problem`) → `engine.build_figure` (coordinates, produces `Figure`) → `scene_builder.write_scene` (emits a simple Manim module).
2. **AI path** (`ai_codegen.generate_manim_code`):
   - `missing_reference_figure_points` refuses early when the problem refers to a numbered "Hình" whose points are never located in the text. `_drawing_facts_text` removes the proof goals ("Chứng minh…") so that they don't count as drawing facts.
   - DeepSeek is called with `SYSTEM_PROMPT`, which is built from the inline rules, `MIDDLE_SCHOOL_GEOMETRY_RULES` and `DRAWING_ERROR_MEMORY` from `geometry_knowledge.py`.
   - The reply goes through `extract_python`, then `_ensure_light_theme` (injects `apply_light_theme(self)`), then `sanitize_code` (auto-injects parallel and ordinary-polygon verifier calls), then `validate_code`.
   - When validation fails, the error is sent back to DeepSeek, up to 3 retries in the same conversation.
   - In `geo_draw/pipeline.py` (`draw`), a failed Manim render triggers up to 3 more `generate_manim_code(..., repair_log=...)` calls that include the render log and the previous code.

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

### Math tutor (from MathLovers)

- **Conversations** (`geo_draw/conversations.py`) hold `problem`, `mode` (`hint` | `solution`) and `hint_level` (1–5). Messages have a `channel`: `chat` holds the tutor conversation, and `figure` holds drawing requests and drawings. They also carry a JSON `meta` (mode, level, `error`). Missing columns are added to old databases on open. Conversations from before the tutor have only `figure` messages; `problem_of()` returns their first request as the problem.
- **`run_tutor_turn`** (`geo_draw/tutor.py`):
  - A photo is read with `extract_problem_from_image`. The first message becomes the `problem` and the title.
  - The model gets `build_system_prompt(problem, mode, level)` plus the last 16 chat messages. The reply streams through `ai_codegen.stream_chat` (DeepSeek `stream: true`) as `delta` events.
  - AI errors are saved as an assistant message with `meta.error`.
- **Prompts** (`geo_draw/tutor_prompts.py`): the 5 hint levels are Hiểu đề → Nhớ kiến thức → Chiến lược → Bước đầu tiên → Sâu hơn nữa. In hint mode the MathLovers `GUARDRAIL` (no full solution, no final answer, end with exactly one question) is always appended. The solution prompt asks for numbered steps, a **Kết luận:** and a **Lưu ý**. Keep the UI level names (`web/src/components/chat/TutorBar.tsx`) in sync with `HINT_LEVELS`.
- **Figure awareness**: `run_tutor_turn(figure=…)` takes a callable returning `shown`, `drawing` or `none`, and the prompt tells the tutor which one is true. Without this, the tutor used to send students to a figure that did not exist. The API computes it from existing drawings and `AppState.figure_jobs` (conversation → marker, set *before* a figure job starts so that a fast job cannot leave it behind).
- **Drawing requests in the chat** (`tutor.drawing_request`, matched on *accented* text because accent-stripped "vẽ" equals "về"):
  - `generic` ("vẽ giúp mình", "nên vẽ hình trước") draws the figure, or says it is already there, and gets a canned reply saved by `record_canned_reply`. There is no tutor call and no tutor quota.
  - `specific` ("kẻ thêm đường cao AH") starts a refinement and still runs the tutor turn.
- **`is_geometry_problem`** needs named points (ABC, tâm O…) plus plane-figure words, or relation words when there are no algebra words. Solids are never drawn automatically. It works on accent-stripped text, so avoid ambiguous words such as "kẻ"/"kể".
- **Testing without DeepSeek**: patch `geo_draw.tutor.stream_chat` (the API tests do this in `setUp`). For browser runs, point `DEEPSEEK_BASE_URL` at a small OpenAI-compatible fake server.

### Dashboard = chat (legacy Streamlit UI; it only reads the `figure` channel)

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
