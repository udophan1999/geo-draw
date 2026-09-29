"""Paths, shared stores and constants for the web app."""

from __future__ import annotations

import os
from pathlib import Path

from geo_draw.accounts import AccountStore
from geo_draw.ai_codegen import load_dotenv
from geo_draw.history import HistoryStore


# Repository root: web/config.py -> web/ -> repo.
ROOT = Path(__file__).resolve().parent.parent
# GEO_DRAW_DATA_DIR lets test runs use a temporary folder instead of the real data.
GENERATED = Path(os.environ.get("GEO_DRAW_DATA_DIR") or ROOT / "generated")
USERS_DIR = GENERATED / "users"
SESSIONS_DIR = GENERATED / "sessions"
HISTORY = HistoryStore(USERS_DIR)
ACCOUNTS = AccountStore(USERS_DIR)
load_dotenv(ROOT / ".env")

EXAMPLES = {
    "Tam giác vuông": "Cho tam giác ABC vuông tại A, AB = 3, AC = 4.",
    "Tam giác + nhiều yêu cầu": (
        "Cho tam giác ABC vuông tại A, AB = 4, AC = 6. Gọi M là trung điểm BC. "
        "Kẻ đường cao AH. Qua M kẻ đường thẳng song song với AB, cắt AC tại N. "
        "Vẽ đường tròn tâm M đi qua B."
    ),
    "Đường tròn + tiếp tuyến": (
        "Cho đường tròn tâm O bán kính 3 và điểm A nằm ngoài đường tròn. "
        "Từ A kẻ hai tiếp tuyến AB, AC với đường tròn, B và C là các tiếp điểm. Vẽ OA, OB, OC."
    ),
    "Hình vuông": "Cho hình vuông ABCD cạnh 4. Vẽ hai đường chéo AC và BD, đánh dấu giao điểm O.",
    "Các đường đặc biệt và góc": (
        "Cho tam giác ABC có AB = 5, AC = 6 và góc BAC = 60°. Gọi M là trung điểm BC; "
        "vẽ trung tuyến AM. Kẻ đường cao AH, phân giác AD và đường trung trực của BC. "
        "Đánh dấu các góc bằng nhau và các góc vuông."
    ),
}
