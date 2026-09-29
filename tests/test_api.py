import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import create_app
from geo_draw.ai_codegen import AiSettings
from geo_draw.conversations import ASSISTANT, CHAT, FIGURE, USER
from geo_draw.renderer import render_scene
from geo_draw.tutor import REPLY_DRAWING, REPLY_SHOWN

from tests.test_pipeline import AI_SCENE

TRIANGLE = "Cho tam giác ABC vuông tại A, AB = 3, AC = 4."
EQUATION = "Giải phương trình $x^2 - 5x + 6 = 0$."
INTEGRAL = r"Tính tích phân $\int_1^{10} (x^2 + 1)\,dx$."
WORD_PROBLEM = "Một mảnh vườn hình chữ nhật có chu vi 34 m. Tính chiều dài và chiều rộng."
HINT_REPLY = ("Em thử nhớ lại ", "định lý Pythagore: $a^2 + b^2 = c^2$ nhé. ", "BC bằng bao nhiêu?")


def fake_stream(ai, messages, **_):
    """Stands in for DeepSeek: the tutor's reply arrives in three pieces."""
    yield from HINT_REPLY


def read_events(client: TestClient, job_id: str) -> list[tuple[str, object]]:
    events, kind = [], None
    with client.stream("GET", f"/api/jobs/{job_id}/events") as response:
        assert response.status_code == 200, response.read()
        for line in response.iter_lines():
            if line.startswith("event: "):
                kind = line[len("event: "):]
            elif line.startswith("data: "):
                events.append((kind, json.loads(line[len("data: "):])))
    return events


class ApiTestCase(unittest.TestCase):
    ai = AiSettings(api_key="")
    limit_guest, limit_user = 1, 2

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name)
        self.app = create_app(self.data, ai=self.ai, daily_limit_guest=self.limit_guest,
                              daily_limit_user=self.limit_user)
        self.state = self.app.state.geo
        tutor = patch("geo_draw.tutor.stream_chat", side_effect=fake_stream)
        self.tutor_stream = tutor.start()
        self.addCleanup(tutor.stop)

    def tearDown(self):
        self.state.jobs.shutdown(wait=True)  # let background jobs finish before the dir goes
        self._tmp.cleanup()

    def client(self) -> TestClient:
        return TestClient(self.app)

    def register(self, client: TestClient, name: str = "an7a", password: str = "hinhhoc1"):
        return client.post("/api/auth/register", json={"username": name, "password": password})

    def use_parser(self, client: TestClient) -> None:
        response = client.put("/api/settings", json={"mode": "parser", "model": "deepseek-v4-flash",
                                                      "quality": "l", "animate": False})
        self.assertEqual(response.status_code, 200)

    def send(self, client: TestClient, text: str, conversation_id: str | None = None,
             action: str | None = None):
        data = {"text": text}
        if conversation_id:
            data["conversation_id"] = conversation_id
        if action:
            data["action"] = action
        return client.post("/api/messages", data=data)

    def figure(self, client: TestClient, conversation_id: str, text: str = ""):
        return client.post(f"/api/conversations/{conversation_id}/figure", json={"text": text})


class AuthTests(ApiTestCase):
    def test_guest_gets_a_cookie_and_guest_quota(self):
        client = self.client()
        me = client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertIn("geo_guest", client.cookies)
        self.assertEqual(me.json(), {"user": None, "quota": {"used": 0, "limit": 1},
                                     "ai_available": False})

    def test_register_login_logout(self):
        client = self.client()
        response = self.register(client, "  An 7A ")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["name"], "An 7A")
        self.assertIn("geo_session", client.cookies)
        self.assertEqual(client.get("/api/auth/me").json()["quota"]["limit"], 2)

        taken = self.register(self.client(), "an 7a")
        self.assertEqual(taken.status_code, 409)
        self.assertEqual(taken.json()["suggestions"], ["an 7a 2", "an 7a 3", "an 7a 4"])
        self.assertEqual(self.register(self.client(), "khac", "123").status_code, 422)

        self.assertEqual(client.post("/api/auth/logout").status_code, 204)
        self.assertIsNone(client.get("/api/auth/me").json()["user"])
        other = self.client()
        wrong = other.post("/api/auth/login", json={"username": "An 7A", "password": "sai-roi"})
        self.assertEqual((wrong.status_code, wrong.json()["detail"]),
                         (401, "Sai tên đăng nhập hoặc mật khẩu."))
        ok = other.post("/api/auth/login", json={"username": "AN 7A", "password": "hinhhoc1"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(other.get("/api/auth/me").json()["user"]["name"], "An 7A")

    def test_repeated_wrong_passwords_lock_the_account(self):
        self.register(self.client())
        client = self.client()
        for _ in range(5):
            client.post("/api/auth/login", json={"username": "an7a", "password": "wrong!"})
        locked = client.post("/api/auth/login", json={"username": "an7a", "password": "hinhhoc1"})
        self.assertEqual(locked.status_code, 429)


class ChatTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 50, 50

    def test_tutor_turn_streams_the_reply_and_saves_messages(self):
        client = self.client()
        self.register(client)
        started = self.send(client, EQUATION)
        self.assertEqual(started.status_code, 202)
        conversation_id = started.json()["conversation"]["id"]
        events = read_events(client, started.json()["job_id"])
        kinds = [kind for kind, _ in events]
        self.assertEqual(kinds, ["message", "progress", "delta", "delta", "delta", "message",
                                 "conversation", "done"])
        question, reply = events[0][1], events[5][1]
        self.assertEqual((question["role"], question["channel"], question["text"]),
                         (USER, CHAT, EQUATION))
        self.assertEqual(reply["text"], "".join(HINT_REPLY))
        self.assertEqual(reply["meta"]["hint_level"], 1)
        conversation = events[6][1]
        self.assertEqual((conversation["problem"], conversation["is_geometry"]), (EQUATION, False))

        deeper = self.send(client, "", conversation_id, action="deeper")
        read_events(client, deeper.json()["job_id"])
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        self.assertEqual(detail["conversation"]["hint_level"], 2)
        self.assertEqual([m["channel"] for m in detail["messages"]], [CHAT] * 4)
        solution = self.send(client, "", conversation_id, action="solution")
        read_events(client, solution.json()["job_id"])
        self.assertEqual(client.get(f"/api/conversations/{conversation_id}").json()
                         ["conversation"]["mode"], "solution")

    def test_geometry_problems_are_drawn_automatically(self):
        client = self.client()
        self.register(client)
        self.use_parser(client)
        started = self.send(client, TRIANGLE).json()
        events = read_events(client, started["job_id"])
        figure_jobs = [data["job_id"] for kind, data in events if kind == "figure_job"]
        self.assertEqual(len(figure_jobs), 1)
        drawing = [data for kind, data in read_events(client, figure_jobs[0]) if kind == "message"]
        self.assertTrue(drawing[-1]["has_drawing"])
        self.assertEqual(drawing[-1]["channel"], FIGURE)
        self.assertTrue(client.get(drawing[-1]["image_url"]).content.startswith(b"\x89PNG"))
        self.assertIn("class GeoScene", client.get(f"/api/messages/{drawing[-1]['id']}/scene").text)

        # A refinement redraws with the extra request; the tutor chat is untouched.
        conversation_id = started["conversation"]["id"]
        refine = self.figure(client, conversation_id, "Vẽ thêm trung điểm M của BC")
        self.assertEqual(refine.status_code, 202)
        events = read_events(client, refine.json()["job_id"])
        self.assertIn("M", [data for kind, data in events if kind == "message"][-1]["text"])
        messages = client.get(f"/api/conversations/{conversation_id}").json()["messages"]
        self.assertEqual([(m["channel"], m["role"]) for m in messages if m["channel"] == FIGURE],
                         [(FIGURE, ASSISTANT), (FIGURE, USER), (FIGURE, ASSISTANT)])
        self.assertEqual(len([m for m in messages if m["channel"] == CHAT]), 2)

    def test_problems_without_a_figure_are_never_drawn(self):
        client = self.client()
        self.use_parser(client)
        started = self.send(client, EQUATION).json()
        events = read_events(client, started["job_id"])
        self.assertNotIn("figure_job", [kind for kind, _ in events])
        # Refused outright, before any quota is spent, instead of inventing a triangle.
        response = self.figure(client, started["conversation"]["id"])
        self.assertEqual(response.status_code, 422)
        self.assertIn("không có hình", response.json()["detail"])

    def test_graphs_are_drawn_on_request_and_need_the_ai(self):
        client = self.client()
        self.use_parser(client)
        started = self.send(client, INTEGRAL).json()
        events = read_events(client, started["job_id"])
        self.assertNotIn("figure_job", [kind for kind, _ in events])
        response = self.figure(client, started["conversation"]["id"])
        self.assertEqual(response.status_code, 422)
        self.assertIn("DeepSeek", response.json()["detail"])

    def test_asking_for_a_drawing_in_the_chat_draws_it(self):
        client = self.client()
        self.use_parser(client)
        started = self.send(client, WORD_PROBLEM).json()
        read_events(client, started["job_id"])
        conversation_id = started["conversation"]["id"]
        system_prompt = self.tutor_stream.call_args.args[1][0]["content"]
        self.assertIn("CHƯA có hình vẽ", system_prompt)  # the tutor must not invent a figure
        tutor_calls = self.tutor_stream.call_count

        # "vẽ giúp mình": the app draws and answers itself; no tutor turn.
        ask = self.send(client, "Bạn vẽ giúp mình được không?", conversation_id)
        self.assertEqual(ask.status_code, 202)
        events = read_events(client, ask.json()["job_id"])
        figure_job = next(data["job_id"] for kind, data in events if kind == "figure_job")
        self.assertEqual(events[-2][1]["text"], REPLY_DRAWING)
        self.assertTrue([d for k, d in read_events(client, figure_job) if k == "message"][-1]["has_drawing"])
        self.assertEqual(self.tutor_stream.call_count, tutor_calls)

        # Asked again once the figure exists: no second drawing.
        again = read_events(client, self.send(client, "vẽ hình giúp em", conversation_id).json()["job_id"])
        self.assertNotIn("figure_job", [kind for kind, _ in again])
        self.assertEqual(again[-2][1]["text"], REPLY_SHOWN)

        # A specific request refines the figure and the tutor answers, knowing it is drawn.
        refine = self.send(client, "Kẻ thêm đường chéo AC", conversation_id)
        events = read_events(client, refine.json()["job_id"])
        figure_job = next(data["job_id"] for kind, data in events if kind == "figure_job")
        read_events(client, figure_job)
        self.assertEqual(self.tutor_stream.call_count, tutor_calls + 1)
        self.assertIn("đang vẽ hình", self.tutor_stream.call_args.args[1][0]["content"])

    def test_other_users_and_guests_cannot_see_a_conversation(self):
        alice = self.client()
        self.register(alice, "alice")
        self.use_parser(alice)
        started = self.send(alice, TRIANGLE).json()
        figure_job = next(d["job_id"] for k, d in read_events(alice, started["job_id"])
                          if k == "figure_job")
        drawing = [d for k, d in read_events(alice, figure_job) if k == "message"][-1]
        conversation_id = started["conversation"]["id"]

        bob = self.client()
        self.register(bob, "bob")
        guest = self.client()
        for client in (bob, guest):
            self.assertEqual(client.get(f"/api/conversations/{conversation_id}").status_code, 404)
            self.assertEqual(client.get(drawing["image_url"]).status_code, 404)
            self.assertEqual(client.get(f"/api/jobs/{started['job_id']}/events").status_code, 404)
            self.assertEqual(self.send(client, "Kẻ AM", conversation_id).status_code, 404)
            self.assertEqual(self.figure(client, conversation_id).status_code, 404)
            self.assertEqual(client.get("/api/conversations").json(), [])

    def test_rename_and_delete(self):
        client = self.client()
        started = self.send(client, EQUATION).json()  # as a guest
        read_events(client, started["job_id"])
        conversation_id = started["conversation"]["id"]
        renamed = client.patch(f"/api/conversations/{conversation_id}", json={"title": "PT bậc hai"})
        self.assertEqual(renamed.json()["title"], "PT bậc hai")
        self.assertEqual(client.delete(f"/api/conversations/{conversation_id}").status_code, 204)
        self.assertEqual(client.get("/api/conversations").json(), [])

    def test_bad_input_is_rejected(self):
        client = self.client()
        self.assertEqual(self.send(client, "   ").status_code, 422)
        self.assertEqual(self.send(client, "", action="deeper").status_code, 422)
        self.assertEqual(self.send(client, "x", action="nonsense").status_code, 422)
        bad = client.post("/api/messages", data={"text": "x"},
                          files={"image": ("de.txt", b"hello", "text/plain")})
        self.assertEqual(bad.status_code, 415)

    def test_a_crashing_turn_ends_with_failed(self):
        client = self.client()
        with patch("api.routers.messages.run_tutor_turn", side_effect=RuntimeError("boom")), \
                self.assertLogs("api.jobs", level="ERROR"):
            started = self.send(client, EQUATION).json()
            events = read_events(client, started["job_id"])
        self.assertEqual([kind for kind, _ in events], ["failed"])
        self.assertIn("Máy chủ gặp lỗi", events[0][1]["detail"])


class NoServerKeyTests(ApiTestCase):
    def test_the_tutor_needs_the_server_key_but_parser_drawing_does_not(self):
        client = self.client()
        response = self.send(client, TRIANGLE)
        self.assertEqual(response.status_code, 503)
        self.assertIn("DeepSeek API key", response.json()["detail"])
        self.assertEqual(client.get("/api/conversations").json(), [])


class QuotaTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 2, 5

    def test_guest_ai_turns_stop_at_the_daily_limit(self):
        client = self.client()
        first = self.send(client, TRIANGLE)  # tutor turn 1 + automatic AI drawing 2
        self.assertEqual(first.status_code, 202)
        with patch("api.routers.messages.run_figure_turn") as figure_turn:
            events = read_events(client, first.json()["job_id"])
            figure_job = next(d["job_id"] for k, d in events if k == "figure_job")
            read_events(client, figure_job)
        self.assertEqual(figure_turn.call_args.kwargs["ai"].api_key, "test-key")
        self.assertEqual(client.get("/api/auth/me").json()["quota"], {"used": 2, "limit": 2})
        second = self.send(client, "Em chưa hiểu", first.json()["conversation"]["id"])
        self.assertEqual(second.status_code, 429)
        self.assertIn("Đăng nhập để có thêm lượt", second.json()["detail"])
        # Parser drawings never count.
        self.use_parser(client)
        with patch("api.routers.messages.run_figure_turn"):
            self.assertEqual(self.figure(client, first.json()["conversation"]["id"]).status_code, 202)

    def test_quota_left_for_the_tutor_but_not_the_drawing_skips_the_drawing(self):
        self.state.daily_limit_guest = 1
        client = self.client()
        events = read_events(client, self.send(client, TRIANGLE).json()["job_id"])
        skipped = [data for kind, data in events if kind == "figure_skipped"]
        self.assertEqual(len(skipped), 1)
        self.assertIn("lượt", skipped[0]["detail"])
        self.assertEqual(events[-1][0], "done")


class EditorTests(ApiTestCase):
    def test_manual_edit_rerenders_and_saves(self):
        client = self.client()
        user_id = self.register(client).json()["user"]["id"]
        store = self.state.conversations
        conversation = store.create(user_id, "Tam giác")
        message_id, folder = store.new_message_dir(user_id, conversation.id)
        scene = folder / "scene.py"
        scene.write_text(AI_SCENE, encoding="utf-8")
        rendered = render_scene(scene, folder / "media", animate=False)
        self.assertTrue(rendered.ok, rendered.log[-500:])
        store.add_message(conversation.id, ASSISTANT, "Đã vẽ", message_id=message_id,
                          image_path=rendered.image_path, scene_path=scene)

        state = client.get(f"/api/messages/{message_id}/editor").json()
        self.assertEqual((state["labels"], state["segments"]), (["A", "B"], ["AB", "BC"]))
        edits = {**state["manual_edits"], "hidden_labels": ["A"]}
        before = client.get(f"/api/conversations/{conversation.id}").json()["messages"][0]
        after = client.post(f"/api/messages/{message_id}/render",
                            json={"label_offsets": {"B": [0.1, 0.0]}, "manual_edits": edits})
        self.assertEqual(after.status_code, 200)
        self.assertNotEqual(after.json()["image_url"], before["image_url"])
        saved = client.get(f"/api/messages/{message_id}/editor").json()
        self.assertEqual((saved["label_offsets"], saved["manual_edits"]["hidden_labels"]),
                         ({"B": [0.1, 0.0]}, ["A"]))
        self.assertEqual(self.client().get(f"/api/messages/{message_id}/editor").status_code, 404)


class SettingsTests(ApiTestCase):
    def test_streamlit_settings_files_are_understood(self):
        client = self.client()
        user_id = self.register(client).json()["user"]["id"]
        workspace = self.data / "users" / user_id
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "settings.json").write_text(json.dumps(
            {"mode": "Parser nhanh (không dùng API)", "model": "deepseek-v4-pro",
             "quality": "m", "animate": True}), encoding="utf-8")
        self.assertEqual(client.get("/api/settings").json(),
                         {"mode": "parser", "model": "deepseek-v4-pro", "quality": "m",
                          "animate": True})
        shutil.rmtree(workspace)
        self.assertEqual(client.get("/api/settings").json()["mode"], "ai")


if __name__ == "__main__":
    unittest.main()
