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
        # database_url=None: always SQLite in the temp dir, whatever DATABASE_URL says.
        # apns=None: never reach Apple, whatever APNS_* the .env holds.
        self.app = create_app(self.data, ai=self.ai, database_url=None, apns=None,
                              daily_limit_guest=self.limit_guest,
                              daily_limit_user=self.limit_user)
        self.state = self.app.state.geo
        tutor = patch("geo_draw.tutor.stream_chat", side_effect=fake_stream)
        self.tutor_stream = tutor.start()
        self.addCleanup(tutor.stop)
        titles = patch("geo_draw.tutor._request_chat", return_value="Tên bài toán")  # no network
        self.title_request = titles.start()
        self.addCleanup(titles.stop)

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


class AppClientTests(ApiTestCase):
    """The mobile apps: a Bearer token and an X-Guest-Id header instead of cookies."""
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 50, 50

    def app_client(self, guest_id: str | None = None, token: str | None = None) -> TestClient:
        client = self.client()
        client.headers["X-Client"] = "ios"
        if guest_id:
            client.headers["X-Guest-Id"] = guest_id
        if token:
            client.headers["Authorization"] = f"Bearer {token}"
        return client

    def test_sign_in_returns_a_token_and_sets_no_cookie(self):
        client = self.app_client()
        registered = self.register(client)
        self.assertEqual(registered.status_code, 201)
        token = registered.json()["token"]
        self.assertNotIn("geo_session", client.cookies)
        self.assertIsNone(client.get("/api/auth/me").json()["user"])

        signed_in = self.app_client(token=token)
        self.assertEqual(signed_in.get("/api/auth/me").json()["user"]["name"], "an7a")
        login = self.app_client().post("/api/auth/login",
                                       json={"username": "an7a", "password": "hinhhoc1"})
        self.assertEqual(login.status_code, 200)
        self.assertNotEqual(login.json()["token"], token)

        self.assertEqual(signed_in.post("/api/auth/logout").status_code, 204)
        self.assertIsNone(signed_in.get("/api/auth/me").json()["user"])
        second = self.app_client(token=login.json()["token"])
        self.assertEqual(second.get("/api/auth/me").json()["user"]["name"], "an7a")

    def test_app_config_tells_old_builds_to_update(self):
        self.assertEqual(self.client().get("/api/app-config").json(),
                         {"min_ios_build": 0, "ios_store_url": None})
        self.state.min_ios_build = 42
        self.assertEqual(self.client().get("/api/app-config").json()["min_ios_build"], 42)

    def test_the_web_never_gets_a_token(self):
        response = self.register(self.client())
        self.assertNotIn("token", response.json())
        bad = self.app_client(token="not-a-session")
        self.assertIsNone(bad.get("/api/auth/me").json()["user"])

    def test_bearer_works_for_conversations_and_job_events(self):
        token = self.register(self.app_client()).json()["token"]
        client = self.app_client(token=token)
        started = self.send(client, EQUATION)
        self.assertEqual(started.status_code, 202)
        kinds = [kind for kind, _ in read_events(client, started.json()["job_id"])]
        self.assertEqual(kinds[-1], "done")
        self.assertEqual(len(client.get("/api/conversations").json()), 1)
        self.assertEqual(self.app_client().get("/api/conversations").json(), [])

    def test_guest_id_travels_in_a_header(self):
        first = self.app_client().get("/api/auth/me")
        guest_id = first.headers["X-Guest-Id"]
        self.assertRegex(guest_id, r"^[0-9a-f]{24}$")
        self.assertNotIn("set-cookie", first.headers)

        guest = self.app_client(guest_id)
        again = guest.get("/api/auth/me")
        self.assertNotIn("X-Guest-Id", again.headers)  # a known id is not issued again
        started = self.send(guest, EQUATION)
        read_events(guest, started.json()["job_id"])
        self.assertEqual(len(self.app_client(guest_id).get("/api/conversations").json()), 1)
        self.assertEqual(self.app_client(guest_id).get("/api/auth/me").json()["quota"]["used"], 1)
        self.assertEqual(self.app_client().get("/api/conversations").json(), [])
        # A forged id never becomes a folder name: the caller gets a fresh id instead.
        forged = self.app_client("../../etc").get("/api/auth/me")
        self.assertRegex(forged.headers["X-Guest-Id"], r"^[0-9a-f]{24}$")


class AccountDeletionTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 50, 50

    def delete_account(self, client: TestClient, password: str):
        return client.request("DELETE", "/api/auth/me", json={"password": password})

    def test_a_user_deletes_their_own_account_and_data(self):
        client = self.client()
        self.register(client, "Lan")
        user_id = self.state.accounts.verify("Lan", "hinhhoc1")
        read_events(client, self.send(client, EQUATION).json()["job_id"])
        other = self.client()
        other.post("/api/auth/login", json={"username": "Lan", "password": "hinhhoc1"})

        wrong = self.delete_account(client, "sai-roi")
        self.assertEqual((wrong.status_code, wrong.json()["detail"]), (401, "Mật khẩu không đúng."))
        self.assertEqual(self.delete_account(client, "hinhhoc1").status_code, 204)
        self.assertEqual(self.state.conversations.list(user_id), [])
        self.assertFalse((self.state.users_dir / user_id).exists())
        for signed_out in (client, other):  # every session ends
            self.assertIsNone(signed_out.get("/api/auth/me").json()["user"])
        self.assertEqual(self.register(self.client(), "Lan").status_code, 201)

    def test_guests_cannot_and_wrong_passwords_lock(self):
        self.assertEqual(self.delete_account(self.client(), "x").status_code, 401)
        client = self.client()
        self.register(client)
        for _ in range(5):
            self.delete_account(client, "wrong!")
        self.assertEqual(self.delete_account(client, "hinhhoc1").status_code, 429)
        self.assertEqual(client.get("/api/auth/me").json()["user"]["name"], "an7a")

    def test_the_app_deletes_with_its_token(self):
        app = self.client()
        app.headers["X-Client"] = "ios"
        token = self.register(app).json()["token"]
        app.headers["Authorization"] = f"Bearer {token}"
        self.assertEqual(self.delete_account(app, "hinhhoc1").status_code, 204)
        self.assertIsNone(app.get("/api/auth/me").json()["user"])


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
        self.assertIn("MathMate AI", response.json()["detail"])

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


class MessageEditTests(ApiTestCase):
    ai = AiSettings(api_key="test-key")
    limit_guest, limit_user = 50, 50

    def edit(self, client: TestClient, message_id: str, text: str):
        return client.patch(f"/api/messages/{message_id}", json={"text": text})

    def chat(self, client: TestClient, conversation_id: str) -> list[dict]:
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        return [m for m in detail["messages"] if m["channel"] == CHAT]

    def start(self, client: TestClient) -> str:
        started = self.send(client, EQUATION).json()
        read_events(client, started["job_id"])
        return started["conversation"]["id"]

    def test_editing_the_last_message_answers_it_again(self):
        client = self.client()
        self.register(client)
        conversation_id = self.start(client)
        # The tutor's answer to "x = 2" raises the hint level; the edit must undo that.
        self.tutor_stream.side_effect = lambda *a, **k: iter(["Đúng rồi! [[bac:4]]"])
        read_events(client, self.send(client, "x = 2", conversation_id).json()["job_id"])
        detail = client.get(f"/api/conversations/{conversation_id}").json()
        self.assertEqual(detail["conversation"]["hint_level"], 4)
        last = self.chat(client, conversation_id)[-2]
        old_reply = self.chat(client, conversation_id)[-1]

        self.tutor_stream.side_effect = lambda *a, **k: iter(["Em xem lại nhé."])
        started = self.edit(client, last["id"], "x = 3")
        self.assertEqual(started.status_code, 202)
        events = read_events(client, started.json()["job_id"])
        self.assertEqual([kind for kind, _ in events],
                         ["message", "progress", "delta", "message", "conversation", "done"])
        self.assertEqual((events[0][1]["id"], events[0][1]["text"]), (last["id"], "x = 3"))
        self.assertTrue(events[0][1]["meta"]["edited"])

        chat = self.chat(client, conversation_id)
        self.assertEqual([m["text"] for m in chat[-2:]], ["x = 3", "Em xem lại nhé."])
        self.assertEqual(len(chat), 4)  # the problem, its reply, the edited answer, the new reply
        self.assertNotIn(old_reply["id"], [m["id"] for m in chat])
        self.assertEqual(client.get(f"/api/conversations/{conversation_id}").json()
                         ["conversation"]["hint_level"], 1)
        # The model saw the edited text, not the old one.
        sent = self.tutor_stream.call_args.args[1]
        self.assertEqual(sent[-1], {"role": "user", "content": "x = 3"})
        self.assertNotIn("x = 2", json.dumps(sent, ensure_ascii=False))
        self.assertEqual(client.get("/api/auth/me").json()["quota"]["used"], 3)

    def test_only_the_last_message_of_the_student_can_be_edited(self):
        client = self.client()
        self.register(client)
        conversation_id = self.start(client)
        read_events(client, self.send(client, "x = 2", conversation_id).json()["job_id"])
        problem, reply = self.chat(client, conversation_id)[:2]
        for message in (problem, reply):
            response = self.edit(client, message["id"], "khác")
            self.assertEqual(response.status_code, 409)
            self.assertIn("gần nhất", response.json()["detail"])
        last = self.chat(client, conversation_id)[-2]
        self.assertEqual(self.edit(client, last["id"], "   ").status_code, 422)
        # Someone else's message does not exist for this caller.
        stranger = self.client()
        self.register(stranger, "khach2")
        self.assertEqual(self.edit(stranger, last["id"], "x = 9").status_code, 404)
        self.assertEqual(client.get("/api/auth/me").json()["quota"]["used"], 2)

    def test_no_edit_while_the_tutor_is_answering(self):
        client = self.client()
        self.register(client)
        conversation_id = self.start(client)
        problem = self.chat(client, conversation_id)[0]
        self.state.tutor_jobs.add(conversation_id)
        response = self.edit(client, problem["id"], "Giải phương trình x + 1 = 0")
        self.assertEqual(response.status_code, 409)
        self.assertIn("đang trả lời", response.json()["detail"])

    def test_editing_the_first_message_changes_the_problem(self):
        client = self.client()
        self.register(client)
        conversation_id = self.start(client)
        problem = self.chat(client, conversation_id)[0]
        self.title_request.return_value = "Phương trình bậc nhất"
        events = read_events(client, self.edit(client, problem["id"], "Giải phương trình 2x = 6").json()["job_id"])
        conversation = [data for kind, data in events if kind == "conversation"][-1]
        self.assertEqual(conversation["problem"], "Giải phương trình 2x = 6")
        self.assertEqual(conversation["title"], "Phương trình bậc nhất")
        sent = self.tutor_stream.call_args.args[1]
        self.assertIn("Giải phương trình 2x = 6", sent[-1]["content"])

    def test_editing_a_geometry_problem_draws_it_again(self):
        client = self.client()
        self.register(client)
        self.use_parser(client)
        started = self.send(client, TRIANGLE).json()
        events = read_events(client, started["job_id"])
        read_events(client, next(d["job_id"] for k, d in events if k == "figure_job"))
        problem = self.chat(client, started["conversation"]["id"])[0]
        events = read_events(client, self.edit(client, problem["id"],
                                               "Cho tam giác ABC vuông tại A, AB = 5, AC = 12.").json()["job_id"])
        figure_jobs = [d["job_id"] for k, d in events if k == "figure_job"]
        self.assertEqual(len(figure_jobs), 1)
        drawing = [d for k, d in read_events(client, figure_jobs[0]) if k == "message"][-1]
        self.assertTrue(drawing["has_drawing"])


class NoServerKeyTests(ApiTestCase):
    def test_the_tutor_needs_the_server_key_but_parser_drawing_does_not(self):
        client = self.client()
        response = self.send(client, TRIANGLE)
        self.assertEqual(response.status_code, 503)
        self.assertIn("khóa AI", response.json()["detail"])
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
