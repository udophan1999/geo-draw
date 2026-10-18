#!/usr/bin/env bash
# Build and run the Android app (mobile/android) on an emulator or a phone, or run its tests.
#
#   scripts/dev_android.sh            Build, install and open the app (default: run)
#   scripts/dev_android.sh run        Same
#   scripts/dev_android.sh test       Unit tests (JVM) + UI tests on the device (starts a test API
#                                     with a fake AI on :8797 for the UI tests, stops it afterwards)
#   scripts/dev_android.sh unit       Unit tests only (JVM, no device)
#   scripts/dev_android.sh open       Open mobile/android in Android Studio
#
# Options (run and test):
#   --avd Pixel_XL_API_35             Emulator to start when no device is connected
#                                     (default: the first one of `emulator -list-avds`)
#   --device SERIAL                   Device to use when several are connected (see `adb devices`)
#   --api http://127.0.0.1:8797       Server for the app (run only; default: http://127.0.0.1:8000,
#                                     i.e. `./start.sh dev`). Give the computer's address: the
#                                     script turns it into 10.0.2.2 for an emulator, and uses
#                                     `adb reverse` for a phone on USB.
#
# Needs the Android SDK (Android Studio installs it; ANDROID_HOME, default ~/Library/Android/sdk)
# and JDK 17 (Android Studio's own, or `brew install --cask temurin@17`).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
ANDROID="$ROOT/mobile/android"
PACKAGE="com.tvcsoft.mathmate"
TEST_API_PORT=8797

log() { printf '\033[1;32m[android]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[android]\033[0m %s\n' "$*" >&2; exit 1; }

MODE="run"
case "${1:-}" in run | test | unit | open) MODE="$1"; shift ;; esac
AVD=""
SERIAL=""
API=""
while [ $# -gt 0 ]; do
  case "$1" in
    --avd) AVD="${2:?--avd cần tên emulator}"; shift 2 ;;
    --device) SERIAL="${2:?--device cần serial của máy}"; shift 2 ;;
    --api) API="${2:?--api cần một URL}"; shift 2 ;;
    *) die "Không hiểu tham số: $1. Cách dùng: scripts/dev_android.sh [run|test|unit|open] [--avd TÊN] [--device SERIAL] [--api URL]" ;;
  esac
done

# Tools -----------------------------------------------------------------------------------
if [ "$MODE" = open ]; then
  [ -d "/Applications/Android Studio.app" ] || die "Không thấy Android Studio trong /Applications."
  open -a "Android Studio" "$ANDROID"
  exit 0
fi

export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
[ -d "$ANDROID_HOME" ] || die "Không thấy Android SDK ở $ANDROID_HOME. Cài Android Studio, hoặc đặt ANDROID_HOME."
ADB="$ANDROID_HOME/platform-tools/adb"
EMULATOR="$ANDROID_HOME/emulator/emulator"
[ -x "$ADB" ] || die "Thiếu adb: cài 'Android SDK Platform-Tools' trong SDK Manager."

# AGP 8 needs JDK 17: the system one if it is 17, else one macOS knows, else Android Studio's.
java_major() { "$1/bin/java" -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1; }
if [ -z "${JAVA_HOME:-}" ] || [ "$(java_major "$JAVA_HOME")" != 17 ]; then
  if JDK=$(/usr/libexec/java_home -v 17 2>/dev/null); then
    export JAVA_HOME="$JDK"
  elif [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
    export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  else
    die "Cần JDK 17: brew install --cask temurin@17 (hoặc cài Android Studio)."
  fi
fi

gradle() { (cd "$ANDROID" && ./gradlew "$@"); }

if [ "$MODE" = unit ]; then
  log "Unit test (JVM)..."
  gradle :app:testDebugUnitTest -q
  log "Unit test qua."
  exit 0
fi

# The device: the one asked for, else a connected one, else a new emulator ------------------
devices() { "$ADB" devices | awk 'NR > 1 && $2 == "device" { print $1 }'; }
if [ -z "$SERIAL" ]; then
  SERIAL=$(devices | head -1)
  if [ "$(devices | wc -l | tr -d ' ')" -gt 1 ]; then
    log "Có nhiều máy đang kết nối, dùng $SERIAL (chọn máy khác bằng --device)."
  fi
fi
if [ -z "$SERIAL" ]; then
  [ -x "$EMULATOR" ] || die "Không có máy nào kết nối và thiếu emulator: cài 'Android Emulator' trong SDK Manager."
  [ -n "$AVD" ] || AVD=$("$EMULATOR" -list-avds | head -1)
  [ -n "$AVD" ] || die "Chưa có emulator nào: tạo một cái trong Android Studio (Device Manager)."
  log "Mở emulator $AVD..."
  "$EMULATOR" -avd "$AVD" -no-snapshot-save -no-boot-anim >/dev/null 2>&1 &
  "$ADB" wait-for-device
  SERIAL=$(devices | head -1)
fi
ADB_DEVICE=("$ADB" -s "$SERIAL")
for _ in $(seq 1 120); do
  [ "$("${ADB_DEVICE[@]}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ] && break
  sleep 1
done
EMULATED=false
case "$SERIAL" in emulator-*) EMULATED=true ;; esac
log "Thiết bị: $SERIAL$($EMULATED && echo ' (emulator)' || echo ' (máy thật)')"

# The app sees the computer at 10.0.2.2 from an emulator; a phone goes through `adb reverse`.
device_url() {
  local url="$1" port
  port=$(printf '%s' "$url" | sed -n 's#^https\{0,1\}://[^/:]*:\([0-9]*\).*#\1#p')
  case "$url" in
    http://127.0.0.1:* | http://localhost:*)
      if $EMULATED; then
        printf '%s' "$url" | sed -E 's#//(127\.0\.0\.1|localhost)#//10.0.2.2#'
      else
        "${ADB_DEVICE[@]}" reverse "tcp:$port" "tcp:$port" >/dev/null
        printf '%s' "$url" | sed 's#//localhost#//127.0.0.1#'
      fi ;;
    *) printf '%s' "$url" ;;
  esac
}

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
  TEST_API=$(device_url "http://127.0.0.1:$TEST_API_PORT")
  log "Unit test (JVM) + UI test trên $SERIAL (API: $TEST_API)..."
  ANDROID_SERIAL="$SERIAL" gradle :app:testDebugUnitTest :app:connectedDebugAndroidTest \
    "-Pandroid.testInstrumentationRunnerArguments.api=$TEST_API" -q
  log "Test qua."
  exit 0
fi

# Run -------------------------------------------------------------------------------------
HOST_API="${API:-http://127.0.0.1:8000}"
if ! curl -sf -m 2 "$HOST_API/api/health" >/dev/null; then
  log "Chú ý: máy chủ chưa chạy ở $HOST_API. Mở nó ở một cửa sổ khác: ./start.sh dev"
fi
APP_API=$(device_url "$HOST_API")

log "Build và cài app..."
ANDROID_SERIAL="$SERIAL" gradle :app:installDebug -q
# A running copy may have been started with other extras (e.g. by the UI tests): restart.
"${ADB_DEVICE[@]}" shell am force-stop "$PACKAGE"
"${ADB_DEVICE[@]}" shell am start -n "$PACKAGE/.MainActivity" --es api "$APP_API" >/dev/null
log "Đã mở MathMate (máy chủ: $APP_API)."
