#!/usr/bin/env bash
# Deploy MathMate on the VPS by hand (the Jenkins pipeline does the same). Safe to re-run.
#   1. pull the latest code
#   2. rebuild and restart the production stack (docker-compose.prod.yml)
#   3. check the app is healthy and reaches its database
#
# Tables are created by the app when it starts (CREATE TABLE IF NOT EXISTS), so there is
# no migration step; the role only needs the rights to create them (see README).
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env)
PROBE="import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"
# A health check that also proves the database works: the server reads the users table.
DB_PROBE="from api.state import AppState; from pathlib import Path; s = AppState(Path('/data')); print(len(s.accounts.list_users()), 'tài khoản'); s.close()"

if [ ! -f .env ]; then
  cat >&2 <<'EOF'
LỖI: chưa có .env.

  cp .env.example .env   # rồi điền DEEPSEEK_API_KEY, DATABASE_URL, DB_NETWORK, APP_DOMAIN,
                         # ADMIN_USERNAME, ADMIN_PASSWORD

Tệp này KHÁC tệp Jenkins tạo ra (Jenkins tạo .env từ managed config rồi xóa sau mỗi lần
build). Giữ hai nơi giống nhau, kẻo deploy tay chạy với cấu hình cũ.
EOF
  exit 1
fi

echo "→ Lấy code mới nhất…"
git pull --ff-only

echo "→ Build và khởi động lại…"
"${COMPOSE[@]}" up --build -d --remove-orphans

echo "→ Chờ ứng dụng sẵn sàng…"
ok=""
for _ in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T app python -c "$PROBE" 2>/dev/null; then ok=1; break; fi
  sleep 2
done
if [ -z "$ok" ]; then
  # Re-run the probe with its error shown: the retry loop hides it, but it is the diagnosis.
  echo "✗ Ứng dụng không lên. Lỗi khi kiểm tra:" >&2
  "${COMPOSE[@]}" exec -T app python -c "$PROBE" >&2 || true
  echo "--- 50 dòng log cuối:" >&2
  "${COMPOSE[@]}" logs --tail=50 app >&2
  exit 1
fi

echo "→ Kiểm tra kết nối database…"
"${COMPOSE[@]}" exec -T app python -c "$DB_PROBE"

echo "→ Trạng thái:"
"${COMPOSE[@]}" ps

# Read only the one non-secret value needed: sourcing .env would put DEEPSEEK_API_KEY and
# DATABASE_URL into the shell, where `bash -x ./deploy.sh` would print them.
# \042 = " and \047 = '.
APP_DOMAIN="$(sed -n 's/^[[:space:]]*APP_DOMAIN=//p' .env | tr -d '\042\047' | head -1)"
echo "✓ Xong. MathMate chạy tại https://${APP_DOMAIN:-<chưa đặt APP_DOMAIN>} (qua Traefik, không mở cổng)."
