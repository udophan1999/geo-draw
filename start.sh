#!/usr/bin/env bash
# Start geo-draw from the repository root.
#
#   ./start.sh          Run: build the web app if its code changed, then serve the API and
#                       the app together on http://localhost:8000
#   ./start.sh dev      Develop: API with auto-reload on :8000 + Vite dev server on :5173
#
# Environment: PORT (default 8000), HOST (default 127.0.0.1; use 0.0.0.0 to allow other
# machines on the network), plus everything in .env (see .env.example).
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-run}"
PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

log() { printf '\033[1;34m[geo-draw]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[geo-draw]\033[0m %s\n' "$*" >&2; exit 1; }

case "$MODE" in run | dev) ;; *) die "Cách dùng: ./start.sh [dev]" ;; esac

# Python environment ---------------------------------------------------------------------
if [ ! -x .venv/bin/python ]; then
  command -v python3 >/dev/null || die "Cần cài Python 3.12 trước."
  log "Tạo môi trường Python (.venv)..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
elif ! .venv/bin/python -c "import fastapi, uvicorn, manim, multipart" 2>/dev/null; then
  log "Cài thư viện Python còn thiếu..."
  .venv/bin/pip install -q -r requirements.txt
fi

# Node 22 (via nvm when available; this machine's default `node` may be older) ------------
NVM_SH="${NVM_DIR:-$HOME/.nvm}/nvm.sh"
if [ -s "$NVM_SH" ]; then
  set +u  # nvm is not written for `set -u`
  # shellcheck disable=SC1090
  . "$NVM_SH"
  nvm use >/dev/null 2>&1 || nvm install
  set -u
fi
NODE_MAJOR=$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)
[ "$NODE_MAJOR" -ge 20 ] || die "Cần Node 22 (hiện có: $(node -v 2>/dev/null || echo 'chưa cài')). Cài bằng: nvm install 22"
if [ ! -d web/node_modules ]; then
  log "Cài thư viện giao diện (web/node_modules)..."
  npm --prefix web install
fi

[ -f .env ] || log "Chưa có tệp .env: chế độ DeepSeek AI sẽ tắt. Sao chép .env.example thành .env rồi điền key."

# Start ------------------------------------------------------------------------------------
if [ "$MODE" = dev ]; then
  log "API:       http://localhost:$PORT  (tài liệu API: /docs)"
  log "Giao diện: http://localhost:5173  (Ctrl+C để dừng cả hai)"
  .venv/bin/uvicorn api.main:app --reload --host "$HOST" --port "$PORT" &
  API_PID=$!
  trap 'kill "$API_PID" 2>/dev/null; wait "$API_PID" 2>/dev/null' EXIT
  GEO_DRAW_API_PORT="$PORT" npm --prefix web run dev
else
  # Rebuild only when the web app changed since the last build.
  if [ ! -f web/dist/index.html ] ||
     [ -n "$(find web/src web/public web/index.html web/package.json web/vite.config.ts \
               -newer web/dist/index.html -print -quit 2>/dev/null)" ]; then
    log "Build giao diện..."
    npm --prefix web run build
  fi
  log "Mở http://localhost:$PORT  (Ctrl+C để dừng)"
  exec .venv/bin/uvicorn api.main:app --host "$HOST" --port "$PORT"
fi
