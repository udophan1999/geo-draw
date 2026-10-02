"""Admin accounts, the first admin from the environment, and the admin API."""

import tempfile
import unittest
from pathlib import Path

from geo_draw.accounts import ADMIN, USER, AccountStore
from geo_draw.app_config import ConfigStore
from geo_draw.tutor_prompts import (
    BASE_TUTOR_PROMPT, GUARDRAIL, SOLUTION_PROMPT, TUTOR_HINT, TUTOR_SOLUTION, build_system_prompt,
)
from geo_draw.conversations import HINT, SOLUTION

from tests.test_api import ApiTestCase, EQUATION, read_events


class AdminAccountTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_admin_is_created_once(self):
        self.assertIn("Đã tạo", self.store.ensure_admin("Quản Trị", "matkhau123"))
        admin = self.store.get_user(self.store.verify("quản trị", "matkhau123"))
        self.assertEqual((admin.name, admin.role), ("Quản Trị", ADMIN))
        # Once an admin exists, the environment is ignored (no second admin, no reset).
        self.assertIsNone(self.store.ensure_admin("Khác", "matkhau456"))
        self.assertFalse(self.store.name_exists("Khác"))

    def test_an_existing_account_is_promoted_and_keeps_its_password(self):
        user_id = self.store.create("Tony", "cu123456")
        self.assertIn("có sẵn", self.store.ensure_admin("tony", "moi123456"))
        self.assertEqual(self.store.get_user(user_id).role, ADMIN)
        self.assertEqual(self.store.verify("Tony", "cu123456"), user_id)

    def test_lock_reset_password_and_delete(self):
        user_id = self.store.create("An", "pass2468")
        token = self.store.start_session(user_id)
        self.assertGreater(self.store.get_user(user_id).last_login, 0)
        self.store.set_disabled(user_id, True)
        self.assertIsNone(self.store.session_user(token))  # signed out at once
        self.assertTrue(self.store.get_user(user_id).disabled)
        self.store.set_disabled(user_id, False)

        token = self.store.start_session(user_id)
        self.store.set_password(user_id, "moi24680")
        self.assertIsNone(self.store.session_user(token))
        self.assertIsNone(self.store.verify("An", "pass2468"))
        self.assertEqual(self.store.verify("An", "moi24680"), user_id)
        with self.assertRaises(ValueError):
            self.store.set_password(user_id, "ngan")

        self.store.set_daily_limit(user_id, 5)
        self.assertEqual(self.store.get_user(user_id).daily_limit, 5)
        self.store.set_daily_limit(user_id, None)
        self.assertIsNone(self.store.get_user(user_id).daily_limit)

        self.store.delete_user(user_id)
        self.assertIsNone(self.store.get_user(user_id))
        self.assertFalse(self.store.name_exists("An"))


class PromptOverrideTests(unittest.TestCase):
    def test_edited_prompts_replace_the_defaults_but_not_the_guardrail(self):
        prompts = {TUTOR_HINT: "Bạn là cô giáo vui tính.", TUTOR_SOLUTION: "Giải thật ngắn."}
        hint = build_system_prompt("x + 1 = 2", HINT, 1, prompts=prompts)
        self.assertTrue(hint.startswith("Bạn là cô giáo vui tính."))
        self.assertNotIn(BASE_TUTOR_PROMPT, hint)
        self.assertIn(GUARDRAIL, hint)
        solution = build_system_prompt("x + 1 = 2", SOLUTION, 1, prompts=prompts)
        self.assertTrue(solution.startswith("Giải thật ngắn."))
        self.assertTrue(build_system_prompt("x", SOLUTION, 1, prompts={}).startswith(SOLUTION_PROMPT))

    def test_config_store_upserts(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ConfigStore(Path(folder))
            store.set("k", "một", "admin")
            store.set("k", "hai", "admin")
            self.assertEqual(store.values(), {"k": "hai"})
            store.delete("k")
            self.assertEqual(store.values(), {})


class AdminApiTests(ApiTestCase):
    ai = ApiTestCase.ai.__class__(api_key="test-key")

    def setUp(self):
        super().setUp()
        self.state.admin_username, self.state.admin_password = "Admin", "quantri123"
        self.state.create_first_admin()

    def admin(self):
        client = self.client()
        response = client.post("/api/auth/login", json={"username": "admin", "password": "quantri123"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], ADMIN)
        return client

    def user_id(self, admin, name):
        users = admin.get("/api/admin/users").json()["users"]
        return next(u["id"] for u in users if u["name"] == name)

    def test_only_admins_get_in(self):
        guest = self.client()
        self.assertEqual(guest.get("/api/admin/users").status_code, 401)
        user = self.client()
        self.register(user)
        self.assertEqual(user.get("/api/auth/me").json()["user"]["role"], USER)
        self.assertEqual(user.get("/api/admin/users").status_code, 403)
        self.assertEqual(user.get("/api/admin/prompts").status_code, 403)

    def test_list_search_and_stats(self):
        user = self.client()
        self.register(user, "Bình An")
        read_events(user, self.send(user, EQUATION).json()["job_id"])
        admin = self.admin()
        listing = admin.get("/api/admin/users").json()
        self.assertEqual(listing["default_limit"], self.limit_user)
        row = next(u for u in listing["users"] if u["name"] == "Bình An")
        self.assertEqual((row["conversations"], row["quota"]["used"], row["role"]), (1, 1, USER))
        self.assertIsNotNone(row["last_active"])
        self.assertEqual([u["name"] for u in admin.get("/api/admin/users?q=bình").json()["users"]],
                         ["Bình An"])

    def test_lock_limit_role_and_password(self):
        user = self.client()
        self.register(user, "Cường", "pass2468")
        admin = self.admin()
        user_id = self.user_id(admin, "Cường")

        # A lock signs the user out and stops logins (after the right password only).
        self.assertTrue(admin.patch(f"/api/admin/users/{user_id}", json={"disabled": True}).json()["disabled"])
        self.assertIsNone(user.get("/api/auth/me").json()["user"])
        self.assertEqual(user.post("/api/auth/login", json={"username": "Cường", "password": "pass2468"}).status_code, 403)
        self.assertEqual(user.post("/api/auth/login", json={"username": "Cường", "password": "sai12345"}).status_code, 401)
        admin.patch(f"/api/admin/users/{user_id}", json={"disabled": False})

        # An own limit replaces the default, and is enforced.
        row = admin.patch(f"/api/admin/users/{user_id}", json={"daily_limit": 0}).json()
        self.assertEqual(row["quota"], {"used": 0, "limit": 0, "custom": True})
        user.post("/api/auth/login", json={"username": "Cường", "password": "pass2468"})
        self.assertEqual(self.send(user, EQUATION).status_code, 429)
        row = admin.patch(f"/api/admin/users/{user_id}", json={"reset_limit": True}).json()
        self.assertEqual(row["quota"]["limit"], self.limit_user)

        self.assertEqual(admin.patch(f"/api/admin/users/{user_id}", json={"role": ADMIN}).json()["role"], ADMIN)
        self.assertEqual(user.get("/api/admin/users").status_code, 200)

        self.assertEqual(admin.post(f"/api/admin/users/{user_id}/password", json={"password": "ngan"}).status_code, 422)
        self.assertEqual(admin.post(f"/api/admin/users/{user_id}/password", json={"password": "moi24680"}).status_code, 204)
        self.assertIsNone(user.get("/api/auth/me").json()["user"])  # signed out everywhere
        self.assertEqual(user.post("/api/auth/login", json={"username": "Cường", "password": "moi24680"}).status_code, 200)

    def test_admins_cannot_lock_demote_or_delete_themselves(self):
        admin = self.admin()
        me = self.user_id(admin, "Admin")
        for body in ({"disabled": True}, {"role": USER}):
            self.assertEqual(admin.patch(f"/api/admin/users/{me}", json=body).status_code, 409)
        self.assertEqual(admin.delete(f"/api/admin/users/{me}").status_code, 409)
        self.assertEqual(admin.patch("/api/admin/users/nobody", json={"disabled": True}).status_code, 404)

    def test_delete_removes_the_account_and_its_data(self):
        user = self.client()
        self.register(user, "Dũng")
        conversation_id = self.send(user, EQUATION).json()["conversation"]["id"]
        admin = self.admin()
        user_id = self.user_id(admin, "Dũng")
        read_events(user, self.send(user, "x = 2", conversation_id).json()["job_id"])
        self.assertTrue((self.state.users_dir / user_id).exists())
        self.assertEqual(admin.delete(f"/api/admin/users/{user_id}").status_code, 204)
        self.assertEqual(self.state.conversations.list(user_id), [])
        self.assertFalse((self.state.users_dir / user_id).exists())
        self.assertIsNone(user.get("/api/auth/me").json()["user"])
        self.assertEqual(self.register(user, "Dũng").status_code, 201)  # the name is free again

    def test_edited_prompt_reaches_the_tutor(self):
        admin = self.admin()
        prompts = admin.get("/api/admin/prompts").json()
        self.assertEqual([p["key"] for p in prompts["prompts"]], [TUTOR_HINT, TUTOR_SOLUTION])
        self.assertFalse(prompts["prompts"][0]["custom"])
        self.assertEqual(len(prompts["fixed"]), 2)

        saved = admin.put(f"/api/admin/prompts/{TUTOR_HINT}", json={"value": "Bạn là thầy giáo nghiêm khắc."}).json()
        self.assertTrue(saved["prompts"][0]["custom"])
        self.assertEqual(saved["prompts"][0]["updated_by"], "Admin")
        read_events(admin, self.send(admin, EQUATION).json()["job_id"])
        system = self.tutor_stream.call_args.args[1][0]["content"]
        self.assertTrue(system.startswith("Bạn là thầy giáo nghiêm khắc."))
        self.assertIn(GUARDRAIL, system)

        self.assertEqual(admin.put(f"/api/admin/prompts/{TUTOR_HINT}", json={"value": "  "}).status_code, 422)
        self.assertEqual(admin.put("/api/admin/prompts/khac", json={"value": "x"}).status_code, 404)
        # Saving the default text, or resetting, goes back to following the default.
        self.assertFalse(admin.put(f"/api/admin/prompts/{TUTOR_HINT}",
                                   json={"value": BASE_TUTOR_PROMPT}).json()["prompts"][0]["custom"])
        admin.put(f"/api/admin/prompts/{TUTOR_HINT}", json={"value": "Tạm"})
        self.assertFalse(admin.delete(f"/api/admin/prompts/{TUTOR_HINT}").json()["prompts"][0]["custom"])


if __name__ == "__main__":
    unittest.main()
