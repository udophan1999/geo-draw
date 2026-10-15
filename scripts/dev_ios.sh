#!/usr/bin/env bash
# Build and run the iOS app (mobile/ios) in the Simulator, or run its tests.
#
#   scripts/dev_ios.sh            Build, then open the app in the Simulator (default: run)
#   scripts/dev_ios.sh run        Same
#   scripts/dev_ios.sh test       Unit tests + UI tests (starts a test API with a fake AI on
#                                 :8797 for the UI tests, and stops it afterwards)
#   scripts/dev_ios.sh open       Generate the project and open it in Xcode
#
# Options (run and test):
#   --sim "iPhone 17 Pro"         Simulator name (default: iPhone 17 Pro)
#   --os 26.5                     iOS version of that simulator (default: the newest one)
#   --api http://host:port        Server for the app (run only; default: the Debug build's
#                                 http://127.0.0.1:8000, i.e. `./start.sh dev`)
#
# Needs Xcode and XcodeGen (`brew install xcodegen`).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
IOS="$ROOT/mobile/ios"
BUNDLE_ID="com.tvcsoft.mathmate"
TEST_API_PORT=8797

log() { printf '\033[1;34m[ios]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[ios]\033[0m %s\n' "$*" >&2; exit 1; }

MODE="run"
case "${1:-}" in run | test | open) MODE="$1"; shift ;; esac
SIM="iPhone 17 Pro"
OS=""
API=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sim) SIM="${2:?--sim cần tên simulator}"; shift 2 ;;
    --os) OS="${2:?--os cần phiên bản iOS}"; shift 2 ;;
    --api) API="${2:?--api cần một URL}"; shift 2 ;;
    *) die "Không hiểu tham số: $1. Cách dùng: scripts/dev_ios.sh [run|test|open] [--sim TÊN] [--os X.Y] [--api URL]" ;;
  esac
done

command -v xcodebuild >/dev/null || die "Cần cài Xcode."
command -v xcodegen >/dev/null || die "Cần cài XcodeGen: brew install xcodegen"

# The project is generated from project.yml (the .xcodeproj is not committed) -------------
generate() {
  local project="$IOS/MathMate.xcodeproj/project.pbxproj"
  if [ ! -f "$project" ] || [ -n "$(find "$IOS/project.yml" "$IOS/MathMate" "$IOS/MathMateTests" \
       "$IOS/MathMateUITests" -newer "$project" -print -quit 2>/dev/null)" ]; then
    log "Tạo project Xcode từ project.yml..."
    (cd "$IOS" && xcodegen generate --quiet)
  fi
}

if [ "$MODE" = open ]; then
  generate
  open "$IOS/MathMate.xcodeproj"
  exit 0
fi

# The simulator: by name, and by iOS version when given (else the newest) -----------------
UDID=$(xcrun simctl list devices available -j | python3 -c '
import json, sys
name, os_version = sys.argv[1], sys.argv[2]
found = []
for runtime, devices in json.load(sys.stdin)["devices"].items():
    if ".iOS-" not in runtime:
        continue
    version = tuple(int(part) for part in runtime.rsplit(".iOS-", 1)[1].split("-"))
    if os_version and version[:len(os_version.split("."))] != tuple(int(p) for p in os_version.split(".")):
        continue
    found += [(version, d["udid"]) for d in devices if d["name"] == name]
print(max(found)[1] if found else "")
' "$SIM" "$OS")
[ -n "$UDID" ] || die "Không tìm thấy simulator «${SIM}»${OS:+ chạy iOS $OS}. Xem danh sách: xcrun simctl list devices available"
DESTINATION="platform=iOS Simulator,arch=$(uname -m),id=$UDID"
log "Simulator: $SIM${OS:+ (iOS $OS)} — $UDID"

generate

# Tests -----------------------------------------------------------------------------------
if [ "$MODE" = test ]; then
  SERVER_PID=""
  stop_server() { [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true; }
  trap stop_server EXIT
  if ! curl -sf -m 2 "http://127.0.0.1:$TEST_API_PORT/api/health" >/dev/null; then
    [ -x "$ROOT/.venv/bin/python" ] || die "Chưa có .venv: chạy ./start.sh một lần để cài môi trường Python."
    log "Mở API thử nghiệm (AI giả, dữ liệu tạm) ở cổng $TEST_API_PORT..."
    "$ROOT/.venv/bin/python" "$ROOT/web/e2e/server.py" "$TEST_API_PORT" >/dev/null 2>&1 &
    SERVER_PID=$!
    for _ in $(seq 1 60); do
      curl -sf -m 1 "http://127.0.0.1:$TEST_API_PORT/api/health" >/dev/null && break
      sleep 0.5
    done
    curl -sf -m 2 "http://127.0.0.1:$TEST_API_PORT/api/health" >/dev/null || die "API thử nghiệm không khởi động được."
  fi
  log "Chạy test..."
  xcodebuild test -project "$IOS/MathMate.xcodeproj" -scheme MathMate -destination "$DESTINATION" \
    -derivedDataPath "$IOS/build" 2>&1 \
    | grep -E "error:|✘|✔ Test run|Test Case .*(passed|failed)|TEST (SUCCEEDED|FAILED)|BUILD FAILED" || true
  exit "${PIPESTATUS[0]}"
fi

# Run -------------------------------------------------------------------------------------
HEALTH="${API:-http://127.0.0.1:8000}/api/health"
if ! curl -sf -m 2 "$HEALTH" >/dev/null; then
  log "Chú ý: máy chủ chưa chạy ở ${API:-http://127.0.0.1:8000}. Mở nó ở một cửa sổ khác: ./start.sh dev"
fi

log "Build app..."
if ! xcodebuild build -project "$IOS/MathMate.xcodeproj" -scheme MathMate -configuration Debug \
     -destination "$DESTINATION" -derivedDataPath "$IOS/build" -quiet; then
  die "Build lỗi (xem thông báo ở trên)."
fi
APP="$IOS/build/Build/Products/Debug-iphonesimulator/MathMate.app"
[ -d "$APP" ] || die "Không tìm thấy $APP sau khi build."

log "Mở Simulator..."
xcrun simctl boot "$UDID" 2>/dev/null || true
open -a Simulator --args -CurrentDeviceUDID "$UDID"
xcrun simctl bootstatus "$UDID" -b >/dev/null
xcrun simctl install "$UDID" "$APP"
# A running copy may have been started with other arguments (e.g. by the UI tests): restart.
xcrun simctl terminate "$UDID" "$BUNDLE_ID" 2>/dev/null || true
if [ -n "$API" ]; then
  xcrun simctl launch "$UDID" "$BUNDLE_ID" -api "$API" >/dev/null
else
  xcrun simctl launch "$UDID" "$BUNDLE_ID" >/dev/null
fi
log "Đã mở MathMate (máy chủ: ${API:-http://127.0.0.1:8000})."
