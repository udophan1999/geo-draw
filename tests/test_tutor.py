import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_draw.ai_codegen import AiSettings, stream_chat
from geo_draw.chat import run_figure_turn
from geo_draw.conversations import (
    ASSISTANT, CHAT, FIGURE, HINT, SOLUTION, USER, ConversationStore,
)
from geo_draw.tutor import (
    DEEPER, GENERIC, SHOW_SOLUTION, SPECIFIC, drawing_request, is_geometry_problem,
    record_canned_reply, run_tutor_turn, suggest_title,
)
from geo_draw.tutor_prompts import (
    FIGURE_DRAWING, FIGURE_NONE, FIGURE_SHOWN, GUARDRAIL, MAX_HINT_LEVEL, build_system_prompt,
)

AI = AiSettings(api_key="test-key")
TRIANGLE = "Cho tam giác ABC vuông tại A, AB = 3, AC = 4. Tính BC."


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def sse(*pieces: str) -> FakeResponse:
    lines = [": keep-alive\n", "\n"]
    for piece in pieces:
        chunk = {"choices": [{"delta": {"content": piece}}]}
        lines.append(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n")
    lines.append("data: [DONE]\n\n")
    return FakeResponse("".join(lines).encode("utf-8"))


class PromptTests(unittest.TestCase):
    def test_hint_prompt_has_the_level_and_the_guardrail(self):
        prompt = build_system_prompt(TRIANGLE, HINT, 2)
        self.assertIn(TRIANGLE, prompt)
        self.assertIn("BẬC GỢI Ý HIỆN TẠI: 2/5 (Nhớ kiến thức)", prompt)
        self.assertIn(GUARDRAIL, prompt)
        self.assertIn("[[bac:N]]", prompt)  # the tutor reports progress
        self.assertNotIn("[[bac:N]]", build_system_prompt(TRIANGLE, SOLUTION, 2))

    def test_levels_are_clamped(self):
        self.assertIn(f"{MAX_HINT_LEVEL}/{MAX_HINT_LEVEL}", build_system_prompt(TRIANGLE, HINT, 99))
        self.assertIn(f"1/{MAX_HINT_LEVEL}", build_system_prompt(TRIANGLE, HINT, 0))

    def test_the_prompt_says_whether_a_figure_exists(self):
        self.assertIn("CHƯA có hình vẽ", build_system_prompt(TRIANGLE, HINT, 1, FIGURE_NONE))
        self.assertIn("đang vẽ hình", build_system_prompt(TRIANGLE, HINT, 1, FIGURE_DRAWING))
        self.assertIn("đang hiển thị hình vẽ", build_system_prompt(TRIANGLE, SOLUTION, 1, FIGURE_SHOWN))
        self.assertIn("CHƯA có hình vẽ", build_system_prompt(TRIANGLE))  # default: no figure

    def test_solution_prompt_has_no_guardrail(self):
        prompt = build_system_prompt(TRIANGLE, SOLUTION, 3)
        self.assertIn("**Kết luận:**", prompt)
        self.assertNotIn("KHÔNG THỂ GHI ĐÈ", prompt)


class StreamChatTests(unittest.TestCase):
    def test_pieces_are_yielded_in_order(self):
        with patch("urllib.request.urlopen", return_value=sse("Chào ", "em! ", "$x^2$")) as urlopen:
            self.assertEqual(list(stream_chat(AI, [{"role": "user", "content": "hi"}])),
                             ["Chào ", "em! ", "$x^2$"])
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(body["stream"])

    def test_missing_key_is_an_error(self):
        with self.assertRaises(ValueError):
            list(stream_chat(AiSettings(api_key=""), []))


class TutorTurnTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConversationStore(Path(self._tmp.name))
        self.conversation = self.store.create("alice", "Đề mới")
        self.events = []

    def tearDown(self):
        self._tmp.cleanup()

    def turn(self, replies=("Gợi ý: ", "em nhớ định lý Pythagore chứ?"), **kwargs):
        prompts = []

        def fake_stream(ai, messages, **_):
            prompts.append(messages)
            yield from replies

        with patch("geo_draw.tutor.stream_chat", side_effect=fake_stream), \
                patch("geo_draw.tutor._request_chat", side_effect=ValueError("offline")):
            messages = run_tutor_turn(self.store, "alice", self.conversation.id, ai=AI,
                                      on_event=lambda kind, data: self.events.append((kind, data)),
                                      **kwargs)
        return messages, prompts[-1] if prompts else None

    def test_first_message_sets_the_problem_and_streams_the_reply(self):
        (question, reply), prompt = self.turn(text=TRIANGLE)
        conversation = self.store.get("alice", self.conversation.id)
        self.assertEqual((conversation.problem, conversation.title), (TRIANGLE, TRIANGLE))
        self.assertEqual((question.role, question.channel, question.text), (USER, CHAT, TRIANGLE))
        self.assertEqual((reply.role, reply.text), (ASSISTANT, "Gợi ý: em nhớ định lý Pythagore chứ?"))
        self.assertEqual(reply.meta["hint_level"], 1)
        kinds = [kind for kind, _ in self.events]
        self.assertEqual(kinds, ["message", "progress", "delta", "delta", "message", "conversation"])
        self.assertIn("Em chưa biết bắt đầu từ đâu", prompt[-1]["content"])
        self.assertIn("BẬC GỢI Ý HIỆN TẠI: 1/5", prompt[0]["content"])

    def test_deeper_and_solution_change_the_state(self):
        self.turn(text=TRIANGLE)
        _, prompt = self.turn(action=DEEPER)
        self.assertEqual(self.store.get("alice", self.conversation.id).hint_level, 2)
        self.assertIn("gợi ý sâu hơn", prompt[-1]["content"])
        self.assertEqual([m["role"] for m in prompt], ["system", "user", "assistant", "user"])
        _, prompt = self.turn(action=SHOW_SOLUTION)
        conversation = self.store.get("alice", self.conversation.id)
        self.assertEqual((conversation.mode, conversation.hint_level), (SOLUTION, 2))
        self.assertNotIn("KHÔNG THỂ GHI ĐÈ", prompt[0]["content"])
        self.assertEqual(len(self.store.messages(self.conversation.id, CHAT)), 6)

    def test_the_tutor_moves_the_level_as_the_student_progresses(self):
        self.turn(text=TRIANGLE, replies=("Đúng rồi. Em nhớ định lý nào?\n", "[[ba", "c:2]]"))
        reply = self.store.messages(self.conversation.id, CHAT)[-1]
        self.assertEqual(reply.text, "Đúng rồi. Em nhớ định lý nào?")
        self.assertEqual(reply.meta["hint_level"], 2)
        streamed = "".join(data["text"] for kind, data in self.events if kind == "delta")
        self.assertNotIn("[", streamed)
        self.assertEqual(self.store.get("alice", self.conversation.id).hint_level, 2)
        # A lower report never moves the bar back; [[xong]] marks the problem as solved.
        self.turn(text="BC = 5", replies=("Chính xác, BC = 5!", "\n[[bac:1]]"))
        self.assertEqual(self.store.get("alice", self.conversation.id).hint_level, 2)
        self.turn(text="Vậy BC = 5 ạ", replies=("Chính xác! Em đã giải xong.\n[[xong]]",))
        conversation = self.store.get("alice", self.conversation.id)
        self.assertTrue(conversation.solved)
        self.assertEqual(self.store.messages(self.conversation.id, CHAT)[-1].text,
                         "Chính xác! Em đã giải xong.")

    def test_progress_tags_are_ignored_in_solution_mode(self):
        self.turn(text=TRIANGLE)
        self.turn(action=SHOW_SOLUTION, replies=("**Kết luận:** BC = 5\n[[xong]]",))
        conversation = self.store.get("alice", self.conversation.id)
        self.assertFalse(conversation.solved)
        self.assertEqual(self.store.messages(self.conversation.id, CHAT)[-1].text, "**Kết luận:** BC = 5")

    def test_the_first_reply_gives_the_conversation_a_short_ai_title(self):
        long_problem = r"Tính tích phân sau: $\int_1^{10} (x^2 + 1)\,dx$ rồi so sánh với diện tích hình thang."
        with patch("geo_draw.tutor.stream_chat", return_value=iter(["Gợi ý"])), \
                patch("geo_draw.tutor._request_chat", return_value="Tên: “Tích phân x² + 1 từ 1 đến 10”.\n") as title:
            run_tutor_turn(self.store, "alice", self.conversation.id, text=long_problem, ai=AI)
        self.assertEqual(self.store.get("alice", self.conversation.id).title, "Tích phân x² + 1 từ 1 đến 10")
        self.assertIn("LaTeX", title.call_args.args[1][0]["content"])
        # Later turns keep the title.
        with patch("geo_draw.tutor.stream_chat", return_value=iter(["Đúng"])), \
                patch("geo_draw.tutor._request_chat") as title:
            run_tutor_turn(self.store, "alice", self.conversation.id, text="x = 2", ai=AI)
        title.assert_not_called()

    def test_unusable_ai_titles_keep_the_problem_as_title(self):
        for bad in ["$\\int_1^{10}$", "x" * 80, ""]:
            with patch("geo_draw.tutor._request_chat", return_value=bad):
                self.assertIsNone(suggest_title(TRIANGLE, AI), bad)
        with patch("geo_draw.tutor._request_chat", side_effect=ValueError("offline")):
            self.assertIsNone(suggest_title(TRIANGLE, AI))

    def test_ai_errors_become_a_saved_reply(self):
        def failing(ai, messages, **_):
            raise ValueError("DeepSeek trả về lỗi HTTP 401: bad key")
            yield  # pragma: no cover

        with patch("geo_draw.tutor.stream_chat", side_effect=failing):
            _, reply = run_tutor_turn(self.store, "alice", self.conversation.id, text=TRIANGLE, ai=AI)
        self.assertTrue(reply.meta["error"])
        self.assertIn("401", reply.text)
        self.assertEqual(self.store.get("alice", self.conversation.id).hint_level, 1)

    def test_a_photo_is_read_into_the_problem(self):
        with patch("geo_draw.tutor.extract_problem_from_image", return_value=TRIANGLE):
            (question, _), _ = self.turn(text="", image=b"png", image_type="image/png")
        self.assertEqual(question.text, TRIANGLE)
        self.assertTrue(question.image_path.is_file())
        self.assertEqual(self.store.get("alice", self.conversation.id).problem, TRIANGLE)

    def test_old_drawing_only_conversations_keep_their_problem(self):
        self.store.add_message(self.conversation.id, USER, TRIANGLE)  # legacy figure request
        (question, _), prompt = self.turn(text="Em không biết tính BC")
        self.assertEqual(self.store.get("alice", self.conversation.id).problem, TRIANGLE)
        self.assertEqual(question.text, "Em không biết tính BC")
        self.assertIn(TRIANGLE, prompt[0]["content"])


class FigureTurnTests(unittest.TestCase):
    def test_figure_uses_the_problem_then_refinements(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConversationStore(Path(tmp))
            conversation = store.create("alice", "Tam giác", problem=TRIANGLE)
            first = run_figure_turn(store, "alice", conversation.id, ai=None)
            self.assertTrue(first[-1].has_drawing, first[-1].log[-400:])
            follow = run_figure_turn(store, "alice", conversation.id, ai=None,
                                     text="Vẽ thêm trung điểm M của BC")
            self.assertEqual([(m.role, m.channel) for m in follow], [(USER, FIGURE), (ASSISTANT, FIGURE)])
            self.assertIn("M", follow[-1].text)
            self.assertEqual(store.messages(conversation.id, CHAT), [])


class MigrationTests(unittest.TestCase):
    def test_old_databases_get_the_new_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(Path(tmp) / "conversations.sqlite3")
            db.executescript(
                """CREATE TABLE conversations (id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                       title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL);
                   CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
                       role TEXT NOT NULL, text TEXT NOT NULL, image_path TEXT, scene_path TEXT,
                       video_path TEXT, log TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL);
                   INSERT INTO conversations VALUES ('c1', 'alice', 'Cũ', 1, 1);
                   INSERT INTO messages VALUES ('m1', 'c1', 'user', 'Cho tam giác ABC.',
                       NULL, NULL, NULL, '', 1);""")
            db.commit()
            db.close()
            store = ConversationStore(Path(tmp))
            conversation = store.get("alice", "c1")
            self.assertEqual((conversation.mode, conversation.hint_level, conversation.problem),
                             (HINT, 1, ""))
            self.assertEqual(store.problem_of(conversation), "Cho tam giác ABC.")
            self.assertEqual(store.messages("c1")[0].channel, FIGURE)


class DrawingRequestTests(unittest.TestCase):
    def test_kinds_of_requests(self):
        cases = {
            "Em nghĩ mình nên vẽ hình trước": GENERIC,
            "Bạn vẽ giúp mình được không?": GENERIC,
            "Vẽ thêm đường cao AH": SPECIFIC,
            "Em kẻ thêm AH vuông góc BC": SPECIFIC,
            "Em nghĩ về chu vi trước": None,  # "về", not "vẽ"
            "Em không biết vẽ": None,
            "a = 1, b = -5, c = 6": None,
        }
        for text, kind in cases.items():
            self.assertEqual(drawing_request(text), kind, text)

    def test_canned_replies_are_saved_without_ai(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConversationStore(Path(tmp))
            conversation = store.create("alice", "Đề", problem=TRIANGLE)
            question, answer = record_canned_reply(store, conversation.id, "Vẽ giúp mình", "Đang vẽ")
            self.assertEqual([(m.role, m.channel) for m in store.messages(conversation.id)],
                             [(USER, CHAT), (ASSISTANT, CHAT)])
            self.assertTrue(answer.meta["canned"])


class GeometryDetectionTests(unittest.TestCase):
    def test_plane_geometry_with_named_points(self):
        for text in (TRIANGLE, "Cho đường tròn tâm O bán kính 3", "Kẻ AH vuông góc với BC tại H",
                     "Cho hình bình hành ABCD, AC cắt BD tại O"):
            self.assertTrue(is_geometry_problem(text), text)

    def test_other_problems(self):
        for text in ("Giải phương trình $x^2 - 5x + 6 = 0$",
                     "Tìm m để đồ thị hàm số y = (m-1)x + 2 song song với đường thẳng y = 3x",
                     "Cho hình chóp S.ABCD có đáy là hình vuông",
                     "Một mảnh vườn hình chữ nhật có chu vi 34 m",
                     "Kể tên các số nguyên tố nhỏ hơn 20"):
            self.assertFalse(is_geometry_problem(text), text)


if __name__ == "__main__":
    unittest.main()
