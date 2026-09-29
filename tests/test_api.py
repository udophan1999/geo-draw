import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import create_app
from geo_draw.ai_codegen import AiSettings
from geo_draw.conversations import ASSISTANT, USER
from geo_draw.renderer import render_scene

from tests.test_pipeline import AI_SCENE

TRIANGLE = "Cho tam giác ABC vuông tại A, AB = 3, AC = 4."


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

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = Path(self._tmp.name)
        self.app = create_app(self.data, ai=self.ai, daily_limit_guest=1, daily_limit_user=2)
        self.state = self.app.state.geo

    def tearDown(self):
        self.state.jobs.shutdown()
        self._tmp.cleanup()

    def client(self) -> TestClient:
        return TestClient(self.app)

    def register(self, client: TestClient, name: str = "an7a", password: str = "hinhhoc1"):
        return client.post("/api/auth/register", json={"username": name, "password": password})

    def use_parser(self, client: TestClient) -> None:
        response = client.put("/api/settings", json={"mode": "parser", "model": "deepseek-v4-flash",
                                                      "quality": "l", "animate": False})
        self.assertEqual(response.status_code, 200)

    def send(self, client: TestClient, text: str, conversation_id: str | None = None):
        data = {"text": text}
        if conversation_id:
            data["conversation_id"] = conversation_id
        return client.post("/api/messages", data=data)


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
    def test_parser_turn_streams_progress_and_saves_messages(self):
        client = self.client()
        self.register(client)
        self.use_parser(client)
        started = self.send(client, TRIANGLE)
        self.assertEqual(started.status_code, 202)
        conversation_id = started.json()["conversation"]["id"]
        events = read_events(client, started.json()["job_id"])
        kinds = [kind for kind, _ in events]
        self.assertEqual(kinds, ["message", "progress", "message", "done"])
        user_message, reply = events[0][1], events[2][1]
        self.assertEqual((user_message["role"], user_message["text"]), (USER, TRIANGLE))
        self.assertEqual(reply["role"], ASSISTANT)
        self.assertTrue(reply["has_drawing"])
        self.assertTrue(client.get(reply["image_url"]).content.startswith(b"\x89PNG"))
        self.assertIn("class GeoScene", client.get(f"/api/messages/{reply['id']}/scene").text)

        # A follow-up in the same conversation redraws with the extra request.
        follow = self.send(client, "Vẽ thêm trung điểm M của BC", conversation_id)
        events = read_events(client, follow.json()["job_id"])
        self.assertIn("M", events[-2][1]["text"])
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        self.assertEqual([m["role"] for m in detail["messages"]], [USER, ASSISTANT, USER, ASSISTANT])
        self.assertEqual([c["id"] for c in client.get("/api/conversations").json()],
                         [conversation_id])

    def test_other_users_and_guests_cannot_see_a_conversation(self):
        alice = self.client()
        self.register(alice, "alice")
        self.use_parser(alice)
        started = self.send(alice, TRIANGLE).json()
        reply = read_events(alice, started["job_id"])[-2][1]
        conversation_id = started["conversation"]["id"]

        bob = self.client()
        self.register(bob, "bob")
        guest = self.client()
        for client in (bob, guest):
            self.assertEqual(client.get(f"/api/conversations/{conversation_id}").status_code, 404)
            self.assertEqual(client.get(reply["image_url"]).status_code, 404)
            self.assertEqual(client.get(f"/api/jobs/{started['job_id']}/events").status_code, 404)
            self.assertEqual(self.send(client, "Kẻ AM", conversation_id).status_code, 404)
            self.assertEqual(client.get("/api/conversations").json(), [])

    def test_rename_and_delete(self):
        client = self.client()
        self.use_parser(client)  # as a guest
        started = self.send(client, TRIANGLE).json()
        read_events(client, started["job_id"])
        conversation_id = started["conversation"]["id"]
        renamed = client.patch(f"/api/conversations/{conversation_id}", json={"title": "Tam giác"})
        self.assertEqual(renamed.json()["title"], "Tam giác")
        self.assertEqual(client.delete(f"/api/conversations/{conversation_id}").status_code, 204)
        self.assertEqual(client.get("/api/conversations").json(), [])

    def test_bad_input_is_rejected(self):
        client = self.client()
        self.assertEqual(self.send(client, "   ").status_code, 422)
        bad = client.post("/api/messages", data={"text": "x"},
                          files={"image": ("de.txt", b"hello", "text/plain")})
        self.assertEqual(bad.status_code, 415)

    def test_ai_mode_without_server_key_is_unavailable(self):
        response = self.send(self.client(), TRIANGLE)  # default settings: AI mode
        self.assertEqual(response.status_code, 503)


class QuotaTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")

    def test_guest_ai_turns_stop_at_the_daily_limit(self):
        client = self.client()
        with patch("api.routers.messages.run_turn") as run_turn:
            first = self.send(client, TRIANGLE)
            self.assertEqual(first.status_code, 202)
            read_events(client, first.json()["job_id"])
            second = self.send(client, TRIANGLE)
        self.assertEqual(second.status_code, 429)
        self.assertIn("Đăng nhập để có thêm lượt", second.json()["detail"])
        self.assertEqual(run_turn.call_count, 1)
        self.assertEqual(run_turn.call_args.kwargs["ai"].api_key, "test-key")
        self.assertEqual(client.get("/api/auth/me").json()["quota"], {"used": 1, "limit": 1})
        # Parser turns never count.
        self.use_parser(client)
        with patch("api.routers.messages.run_turn"):
            self.assertEqual(self.send(client, TRIANGLE).status_code, 202)


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
