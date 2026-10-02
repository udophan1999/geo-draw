"""The stores and the API on PostgreSQL. Skipped unless GEO_DRAW_TEST_DATABASE_URL is set:

    docker run -d --name mathmate-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=mathmate \\
        -p 55432:5432 postgres:16-alpine
    GEO_DRAW_TEST_DATABASE_URL=postgresql://postgres:test@localhost:55432/mathmate \\
        python -m unittest tests.test_postgres -v

Every test works in a fresh schema that is dropped afterwards, so never point this at a
database whose data matters more than a test run.
"""

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from geo_draw.accounts import AccountStore
from geo_draw.ai_codegen import AiSettings
from geo_draw.conversations import ASSISTANT, CHAT, USER, ConversationStore
from geo_draw.db import PostgresDatabase

URL = os.environ.get("GEO_DRAW_TEST_DATABASE_URL")


@unittest.skipUnless(URL, "set GEO_DRAW_TEST_DATABASE_URL to test PostgreSQL")
class PostgresTestCase(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.schema = f"test_{uuid.uuid4().hex[:12]}"
        with psycopg.connect(URL, autocommit=True) as connection:
            connection.execute(f"CREATE SCHEMA {self.schema}")
        self.url = f"{URL}{'&' if '?' in URL else '?'}options=-csearch_path%3D{self.schema}"
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        import psycopg

        with psycopg.connect(URL, autocommit=True) as connection:
            connection.execute(f"DROP SCHEMA {self.schema} CASCADE")
        self._tmp.cleanup()

    def database(self) -> PostgresDatabase:
        db = PostgresDatabase(self.url, max_size=4)
        self.addCleanup(db.close)
        return db


class PostgresStoreTests(PostgresTestCase):
    def test_accounts_sessions_and_lockout(self):
        store = AccountStore(self.root, self.database())
        user_id = store.create("An", "pass2468")
        with self.assertRaises(ValueError):
            store.create(" an ", "other123")  # same name ignoring case and spaces
        self.assertEqual(store.verify("an", "pass2468"), user_id)
        self.assertIsNone(store.verify("an", "wrong"))
        self.assertEqual(store.suggest_names("An"), ["An 2", "An 3", "An 4"])
        token = store.start_session(user_id)
        self.assertEqual(store.session_user(token), user_id)
        store.end_session(token)
        self.assertIsNone(store.session_user(token))
        for _ in range(5):
            store.verify("An", "wrongpass")
        self.assertGreater(store.locked_seconds("An"), 0)

    def test_conversations_and_messages(self):
        db = self.database()
        store = ConversationStore(self.root, db)
        first = store.create("alice", "Đề một")
        second = store.create("alice", "Đề hai")
        store.create("bob", "Của Bình")
        self.assertEqual([c.id for c in store.list("alice")], [second.id, first.id])
        store.update("alice", first.id, problem="x + 1 = 2", hint_level=3, solved=True)
        got = store.get("alice", first.id)
        self.assertEqual((got.problem, got.hint_level, got.solved), ("x + 1 = 2", 3, True))
        self.assertIsNone(store.get("bob", first.id))

        image = self.root / "alice" / "conversations" / first.id / "m" / "a.png"
        store.add_message(first.id, USER, "Đề", channel=CHAT, meta={"mode": "hint"})
        store.add_message(first.id, ASSISTANT, "Hình", image_path=image,
                          scene_path=image.with_name("scene.py"))
        messages = store.messages(first.id)
        self.assertEqual([m.role for m in messages], [USER, ASSISTANT])
        self.assertEqual(messages[0].meta, {"mode": "hint"})
        self.assertEqual(messages[1].image_path, image)
        self.assertTrue(messages[1].has_drawing)
        self.assertEqual([m.role for m in store.messages(first.id, CHAT)], [USER])
        # Timestamps keep their precision (REAL would round them to minutes).
        self.assertAlmostEqual(messages[0].created_at, got.created_at, delta=5)
        self.assertNotEqual(messages[0].created_at, messages[1].created_at)

        for _ in range(2):  # idempotent
            store.import_conversation("alice", "h1", "Cũ", 100.0, [(USER, "Đề cũ", None, None)])
        self.assertEqual(len(store.messages("h1")), 1)
        store.delete("alice", first.id)
        self.assertIsNone(store.get("alice", first.id))
        self.assertEqual(store.messages(first.id), [])

    def test_admin_queries(self):
        from api.quota import QuotaStore
        from geo_draw.app_config import ConfigStore

        db = self.database()
        accounts = AccountStore(self.root, db)
        self.assertIn("Đã tạo", accounts.ensure_admin("Admin", "quantri123"))
        user_id = accounts.create("An", "pass2468")
        accounts.set_daily_limit(user_id, 7)
        accounts.set_disabled(user_id, True)
        self.assertEqual([(u.name, u.role, u.disabled, u.daily_limit) for u in accounts.list_users()],
                         [("Admin", "admin", False, None), ("An", "user", True, 7)])
        self.assertEqual(accounts.admin_count(), 1)
        conversations = ConversationStore(self.root, db)
        conversations.create(user_id, "Một")
        conversations.create(user_id, "Hai")
        self.assertEqual(conversations.owner_stats()[user_id][0], 2)
        self.assertEqual(len(conversations.created_since(0)), 2)
        first = conversations.list(user_id)[0]
        conversations.add_message(first.id, "user", "Đề", channel="chat")
        conversations.add_message(first.id, "assistant", "Hình", image_path=self.root / "a.png",
                                  scene_path=self.root / "s.py")
        self.assertEqual(sorted((r[1], r[4]) for r in conversations.owner_messages(user_id)),
                         [("assistant", True), ("user", False)])
        conversations.delete_owner(user_id)
        self.assertNotIn(user_id, conversations.owner_stats())
        quota = QuotaStore(self.root / "usage.sqlite3", db)
        quota.consume(user_id, 5)
        self.assertEqual(quota.used_today(), {user_id: 1})
        self.assertEqual([row[0] for row in quota.daily_since("2000-01-01")], [user_id])
        self.assertEqual([count for _, count in quota.owner_days(user_id)], [1])
        config = ConfigStore(self.root, db)
        config.set("k", "một", "Admin")
        config.set("k", "hai", "Admin")  # ON CONFLICT … DO UPDATE
        self.assertEqual(config.values(), {"k": "hai"})

    def test_newer_columns_are_added_to_an_older_table(self):
        import psycopg

        with psycopg.connect(self.url, autocommit=True) as connection:
            connection.execute("CREATE TABLE conversations (id TEXT PRIMARY KEY, owner TEXT NOT NULL, "
                               "title TEXT NOT NULL, created_at DOUBLE PRECISION NOT NULL, "
                               "updated_at DOUBLE PRECISION NOT NULL)")
        store = ConversationStore(self.root, self.database())
        conversation = store.create("alice", "Đề")
        self.assertFalse(store.get("alice", conversation.id).solved)


class MigrationTests(PostgresTestCase):
    def test_sqlite_data_is_copied_once_with_portable_paths(self):
        from api.migrate_sqlite import migrate
        from api.quota import QuotaStore

        users_dir, guest_dir = self.root / "users", self.root / "sessions" / ("a" * 24)
        accounts = AccountStore(users_dir)
        user_id = accounts.create("Tony", "pass2468")
        token = accounts.start_session(user_id)
        mine = ConversationStore(users_dir)
        conversation = mine.create(user_id, "Tam giác ABC")
        image = users_dir / user_id / "conversations" / conversation.id / "m" / "a.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"png")
        mine.add_message(conversation.id, ASSISTANT, "Hình", image_path=image,
                         scene_path=image.with_name("scene.py"))
        # An old row with an absolute path from another machine.
        with mine.db.connect() as connection:
            connection.execute("UPDATE messages SET image_path = ?",
                               (f"/Users/someone/generated/users/{image.relative_to(users_dir)}",))
        guest = ConversationStore(guest_dir)
        guest.create("guest", "Của khách")
        QuotaStore(self.root / "usage.sqlite3").consume(user_id, 10)

        db = self.database()
        for _ in range(2):  # a second run adds nothing
            counts = migrate(self.root, db)
        self.assertEqual((counts["users"], counts["conversations"], counts["messages"]), (1, 2, 1))

        accounts = AccountStore(users_dir, db)
        self.assertEqual(accounts.verify("tony", "pass2468"), user_id)
        self.assertEqual(accounts.session_user(token), user_id)
        store = ConversationStore(users_dir, db)
        [moved] = store.messages(conversation.id)
        self.assertEqual(moved.image_path, image)  # resolved under this data folder
        self.assertEqual([c.title for c in ConversationStore(guest_dir, db).list("guest-" + "a" * 24)],
                         ["Của khách"])
        self.assertEqual(QuotaStore(self.root / "usage.sqlite3", db).used(user_id), 1)


@unittest.skipUnless(URL, "set GEO_DRAW_TEST_DATABASE_URL to test PostgreSQL")
class PostgresApiTests(PostgresTestCase):
    def setUp(self):
        super().setUp()
        from api.main import create_app

        self.app = create_app(self.root, ai=AiSettings(api_key="test-key"), database_url=self.url)
        self.state = self.app.state.geo
        self.addCleanup(self.state.close)
        self.addCleanup(lambda: self.state.jobs.shutdown(wait=True))
        stream = patch("geo_draw.tutor.stream_chat", side_effect=lambda *a, **k: iter(["Gợi ý", "\n[[bac:2]]"]))
        title = patch("geo_draw.tutor._request_chat", return_value="Phương trình bậc nhất")
        for p in (stream, title):
            p.start()
            self.addCleanup(p.stop)

    def run_turn(self, client, text):
        started = client.post("/api/messages", data={"text": text}).json()
        with client.stream("GET", f"/api/jobs/{started['job_id']}/events") as events:
            for _ in events.iter_lines():
                pass
        return started["conversation"]["id"]

    def test_users_and_guests_on_postgres(self):
        from fastapi.testclient import TestClient

        # Clients without `with`: the app's shutdown (which closes the pool) runs in cleanup.
        user = TestClient(self.app)
        self.assertEqual(user.post("/api/auth/register", json={"username": "Tony", "password": "pass2468"}).status_code, 201)
        conversation_id = self.run_turn(user, "Giải phương trình 2x + 1 = 5")
        detail = user.get(f"/api/conversations/{conversation_id}").json()
        self.assertEqual(detail["conversation"]["title"], "Phương trình bậc nhất")
        self.assertEqual(detail["conversation"]["hint_level"], 2)
        self.assertEqual([m["role"] for m in detail["messages"]], [USER, ASSISTANT])
        self.assertEqual(user.get("/api/auth/me").json()["quota"]["used"], 1)

        guest_a, guest_b = TestClient(self.app), TestClient(self.app)
        guest_conversation = self.run_turn(guest_a, "Giải phương trình x - 3 = 0")
        self.assertEqual(guest_a.get(f"/api/conversations/{guest_conversation}").status_code, 200)
        # The tables are shared: another guest must not see it, nor the user's.
        self.assertEqual(guest_b.get(f"/api/conversations/{guest_conversation}").status_code, 404)
        self.assertEqual(guest_b.get(f"/api/conversations/{conversation_id}").status_code, 404)
        self.assertEqual(guest_b.get("/api/conversations").json(), [])


if __name__ == "__main__":
    unittest.main()
