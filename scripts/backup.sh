#!/usr/bin/env bash
# Back up MathMate: pg_dump of its database AND a tar of the mathmate-data volume (problem
# photos and drawings, which the database only points to). Prunes old local copies and can
# copy them off the VPS with rclone. Same approach as Wordime's scripts/backup.sh.
#
# The cron must NOT read the deploy .env (Jenkins deletes it after every build). Use a
# persistent file, chmod 600:
#   BACKUP_ENV_FILE=/opt/mathmate/backup.env ./scripts/backup.sh
# holding DATABASE_URL, BACKUP_DOCKER_NETWORK (= DB_NETWORK) and optionally RCLONE_REMOTE,
# BACKUP_RETENTION, RCLONE_RETENTION_DAYS.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE="${BACKUP_ENV_FILE:-.env}"
# Read only the variables this script needs (never `source` a file holding the API key).
read_var() { sed -n "s/^[[:space:]]*$1=//p" "$ENV_FILE" 2>/dev/null | tr -d '\042\047' | head -1; }
DATABASE_URL="${DATABASE_URL:-$(read_var DATABASE_URL)}"
BACKUP_DOCKER_NETWORK="${BACKUP_DOCKER_NETWORK:-$(read_var BACKUP_DOCKER_NETWORK)}"
BACKUP_DOCKER_NETWORK="${BACKUP_DOCKER_NETWORK:-$(read_var DB_NETWORK)}"
RCLONE_REMOTE="${RCLONE_REMOTE:-$(read_var RCLONE_REMOTE)}"
: "${DATABASE_URL:?Cần DATABASE_URL (trong $ENV_FILE) để sao lưu}"

RETENTION="${BACKUP_RETENTION:-$(read_var BACKUP_RETENTION)}"
RETENTION="${RETENTION:-48}"         # local copies of each kind (hourly cron: 2 days)
VOLUME="${BACKUP_VOLUME:-mathmate-data}"
OUT_DIR="backups"
# Backups hold students' data: readable by the owner only.
umask 077
mkdir -p "$OUT_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB_OUT="$OUT_DIR/mathmate-db-${STAMP}.sql.gz"
FILES_OUT="$OUT_DIR/mathmate-files-${STAMP}.tar.gz"

NET_ARG=()
[ -n "$BACKUP_DOCKER_NETWORK" ] && NET_ARG=(--network "$BACKUP_DOCKER_NETWORK")

# Write to a temp file and promote only on success: a failed dump must not leave a
# truncated file that looks like a backup and pushes a good one out of the retention.
TMP="$(mktemp "$OUT_DIR/.mathmate-${STAMP}.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

echo "→ pg_dump…"
# pg_dump 17 also dumps older servers. --clean --if-exists: the dump restores over an
# existing database, not only an empty one.
docker run --rm "${NET_ARG[@]}" --add-host host.docker.internal:host-gateway \
  -e PGCONNECT_TIMEOUT=10 postgres:17-alpine \
  pg_dump --clean --if-exists "$DATABASE_URL" | gzip > "$TMP"
[ -s "$TMP" ] || { echo "✗ pg_dump ra tệp rỗng — dừng" >&2; exit 1; }
mv "$TMP" "$DB_OUT"
echo "✓ $DB_OUT"

echo "→ Tệp ảnh và hình vẽ (volume $VOLUME)…"
docker volume inspect "$VOLUME" >/dev/null
docker run --rm -v "$VOLUME":/data:ro alpine tar czf - -C /data . > "$TMP"
[ -s "$TMP" ] || { echo "✗ tar ra tệp rỗng — dừng" >&2; exit 1; }
mv "$TMP" "$FILES_OUT"
trap - EXIT
echo "✓ $FILES_OUT"

for kind in db files; do
  ls -1t "$OUT_DIR"/mathmate-"$kind"-* 2>/dev/null | tail -n +$((RETENTION + 1)) | while read -r old; do
    echo "→ Xóa bản cũ $old"
    rm -f "$old"
  done
done

# Off-site copy (e.g. RCLONE_REMOTE=gdrive:mathmate-backups). A failure here never fails
# the backup: the local copies are already safe.
if [ -n "$RCLONE_REMOTE" ]; then
  if command -v rclone >/dev/null 2>&1; then
    if rclone copy "$DB_OUT" "$RCLONE_REMOTE/" && rclone copy "$FILES_OUT" "$RCLONE_REMOTE/"; then
      rclone delete "$RCLONE_REMOTE" --include 'mathmate-*' \
        --min-age "${RCLONE_RETENTION_DAYS:-30}d" || true
      echo "✓ Đã chép lên $RCLONE_REMOTE"
    else
      echo "✗ rclone lỗi — bản sao lưu trên máy vẫn còn" >&2
    fi
  else
    echo "✗ chưa cài rclone — bỏ qua bước chép ra ngoài" >&2
  fi
fi

# Restore (by hand):
#   gunzip -c backups/mathmate-db-….sql.gz | docker run --rm -i --network "$DB_NETWORK" \
#     postgres:17-alpine psql "$DATABASE_URL"
#   docker run --rm -i -v mathmate-data:/data alpine tar xzf - -C /data < backups/mathmate-files-….tar.gz
# Test a restore into a scratch database before you need one.
