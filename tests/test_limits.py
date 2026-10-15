"""Limits that keep the AI bill bounded even when cookies are dropped or accounts are farmed."""

from fastapi.testclient import TestClient

from api.quota import TOTAL, QuotaStore, client_counter

from tests.test_api import EQUATION, ApiTestCase, read_events


class LimitTests(ApiTestCase):
    ai = ApiTestCase.ai.__class__(api_key="test-key")
    limit_guest, limit_user = 1, 5

    def from_ip(self, ip: str) -> TestClient:
        """A new client (no cookies, like a script) from ``ip``."""
        return TestClient(self.app, client=(ip, 50_000))

    def ask(self, client: TestClient):
        response = self.send(client, EQUATION)
        if response.status_code == 202:
            read_events(client, response.json()["job_id"])
        return response

    def test_dropping_the_guest_cookie_does_not_reset_the_limit(self):
        self.state.daily_limit_guest_ip = 3
        codes = [self.ask(self.from_ip("203.0.113.5")).status_code for _ in range(5)]
        self.assertEqual(codes, [202, 202, 202, 429, 429])
        refused = self.send(self.from_ip("203.0.113.5"), EQUATION).json()["detail"]
        self.assertIn("Mạng của bạn", refused)
        # Another network has its own allowance, and accounts on this one are unaffected.
        self.assertEqual(self.ask(self.from_ip("198.51.100.7")).status_code, 202)
        user = self.from_ip("203.0.113.5")
        self.register(user)
        self.assertEqual(self.ask(user).status_code, 202)

    def test_the_server_total_caps_everyone_and_counts_nothing_when_full(self):
        self.state.daily_limit_total = 2
        user = self.from_ip("203.0.113.5")
        self.register(user)
        self.assertEqual(self.ask(user).status_code, 202)
        self.assertEqual(self.ask(self.from_ip("198.51.100.7")).status_code, 202)
        refused = self.ask(user)
        self.assertEqual(refused.status_code, 429)
        self.assertIn("lượt AI chung", refused.json()["detail"])
        # All or nothing: the refused turn did not use up the user's own allowance.
        user_id = user.get("/api/auth/me").json()["user"]["id"]
        self.assertEqual(self.state.quota.used(user_id), 1)
        self.assertEqual(self.state.quota.used(TOTAL), 2)

    def test_sign_ups_are_limited_per_ip(self):
        self.state.registrations_per_ip = 2
        self.assertEqual(self.register(self.from_ip("203.0.113.5"), "an01").status_code, 201)
        self.assertEqual(self.register(self.from_ip("203.0.113.5"), "an01").status_code, 409)  # taken: not counted
        self.assertEqual(self.register(self.from_ip("203.0.113.5"), "an02").status_code, 201)
        refused = self.register(self.from_ip("203.0.113.5"), "an03")
        self.assertEqual(refused.status_code, 429)
        self.assertIn("quá nhiều tài khoản", refused.json()["detail"])
        self.assertEqual(self.register(self.from_ip("198.51.100.7"), "an03").status_code, 201)

    def test_counters_stay_out_of_the_admin_charts(self):
        self.state.admin_username, self.state.admin_password = "Admin", "quantri123"
        self.state.create_first_admin()
        self.ask(self.from_ip("203.0.113.5"))  # one guest turn: also ~total and ~ai:<ip>
        admin = self.client()
        admin.post("/api/auth/login", json={"username": "Admin", "password": "quantri123"})
        stats = admin.get("/api/admin/stats?days=7").json()
        self.assertEqual((stats["series"]["ai_users"][-1], stats["series"]["ai_guests"][-1]), (0, 1))
        self.assertEqual(stats["totals"]["ai_turns"], 1)
        self.assertEqual(stats["top_users"], [])
        self.assertEqual(admin.get("/api/admin/users").json()["users"][0]["quota"]["used"], 0)


class ConsumeAllTests(ApiTestCase):
    def test_all_or_nothing(self):
        quota = QuotaStore(self.data / "q.sqlite3")
        self.assertIsNone(quota.consume_all([("a", 5), (client_counter("ai", "1.2.3.4"), 1)]))
        self.assertEqual(quota.consume_all([("a", 5), (client_counter("ai", "1.2.3.4"), 1)]),
                         "~ai:1.2.3.4")
        self.assertEqual(quota.used("a"), 1)  # rolled back with the full counter
