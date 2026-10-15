"""API server for the Playwright tests: the real app on a throwaway data folder, with a fake
OpenAI-compatible AI, so no test ever reaches DeepSeek or the user's data in generated/.

Run from the repo root (playwright.config.ts does it): ``.venv/bin/python web/e2e/server.py <port>``.

The fake AI answers by the student's last message:
- contains "công thức dài": a reply with a very wide display formula (layout overflow checks);
- contains "lỗi ai": HTTP 500, so the tutor saves an error message;
- contains "đáp án mới": "Mình đã xem đáp án mới của em." (an edited message was answered);
- anything else: a short hint ending with ``[[bac:2]]``, streamed in several pieces.
Non-streaming calls (the conversation title) get "Bài thử nghiệm".
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LONG_FORMULA = "$$" + " + ".join(f"\\frac{{x_{{{i}}}^2}}{{{i}}}" for i in range(1, 60)) + "$$"
HINT_REPLY = "Mình cùng đọc kỹ đề nhé. Em hãy chuyển **3** sang vế phải. Em được phương trình nào? [[bac:2]]"


def _last_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
    return ""


class FakeAI(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # keep the test output quiet
        pass

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        text = _last_user_text(body.get("messages", [])).casefold()
        if "lỗi ai" in text:
            self._send(500, "application/json", json.dumps({"error": {"message": "fake failure"}}))
            return
        if "công thức dài" in text:
            reply = f"Biểu thức rất dài:\n\n{LONG_FORMULA}\n\nEm thấy gì? [[bac:1]]"
        elif "đáp án mới" in text:
            reply = "Mình đã xem đáp án mới của em. [[bac:1]]"
        else:
            reply = HINT_REPLY
        if not body.get("stream"):
            answer = {"choices": [{"message": {"role": "assistant", "content": "Bài thử nghiệm"}}]}
            self._send(200, "application/json", json.dumps(answer, ensure_ascii=False))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        pieces = [reply[i:i + 12] for i in range(0, len(reply), 12)]
        for piece in pieces:
            chunk = {"choices": [{"delta": {"content": piece}}]}
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")

    def _send(self, status: int, content_type: str, data: str) -> None:
        encoded = data.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeAI)
    threading.Thread(target=fake.serve_forever, daemon=True).start()

    data_dir = tempfile.mkdtemp(prefix="mathmate-e2e-")
    # Set before api.main is imported: it builds its app at import time, from
    # GEO_DRAW_DATA_DIR. load_dotenv never overrides a variable that is already set, so the
    # real key and DATABASE_URL in .env stay out of the tests.
    os.environ.update({
        "GEO_DRAW_DATA_DIR": data_dir,
        "DEEPSEEK_API_KEY": "e2e-fake-key",
        "DEEPSEEK_BASE_URL": f"http://127.0.0.1:{fake.server_port}",
        "DATABASE_URL": "",
        "ADMIN_USERNAME": "e2e-admin",
        "ADMIN_PASSWORD": "e2e-admin-pass",
        "GEO_DRAW_DAILY_LIMIT_USER": "1000",
        "GEO_DRAW_DAILY_LIMIT_GUEST": "1000",
        "GEO_DRAW_DAILY_LIMIT_GUEST_IP": "10000",
        "GEO_DRAW_REGISTER_LIMIT_IP": "10000",
        "GEO_DRAW_DAILY_LIMIT_TOTAL": "0",
    })
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)  # the Manim subprocess imports geo_draw from the working directory

    import uvicorn

    from api.main import app

    try:
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
