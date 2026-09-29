import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_draw.accounts import MAX_FAILED_ATTEMPTS, AccountStore, valid_password


class AccountStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_names_are_unique_ignoring_case_and_spaces(self):
        self.store.create("Nguyễn Văn An", "secret1")
        self.assertTrue(self.store.name_exists("  nguyễn   văn AN "))
        with self.assertRaises(ValueError):
            self.store.create("NGUYỄN VĂN AN", "secret2")

    def test_suggestions_are_free_names(self):
        self.store.create("An", "secret1")
        self.store.create("An 2", "secret1")
        suggestions = self.store.suggest_names("An")
        self.assertEqual(suggestions, ["An 3", "An 4", "An 5"])
        self.assertFalse(any(self.store.name_exists(name) for name in suggestions))

    def test_password_length_is_checked(self):
        self.assertTrue(valid_password("abc123"))
        self.assertTrue(valid_password("mật khẩu dài"))
        for bad in ("", "12345", "x" * 65):
            self.assertFalse(valid_password(bad), bad)
        with self.assertRaises(ValueError):
            self.store.create("An", "123")
        self.assertFalse(self.store.name_exists("An"))

    def test_verify_checks_password_and_does_not_store_it_in_plain_text(self):
        user_id = self.store.create("An", "pass2468")
        self.assertEqual(self.store.verify("an", "pass2468"), user_id)
        self.assertIsNone(self.store.verify("An", "pass1357"))
        self.assertIsNone(self.store.verify("Bình", "pass2468"))
        self.assertNotIn(b"pass2468", self.store.db_path.read_bytes())

    def test_repeated_failures_lock_the_name(self):
        self.store.create("An", "pass2468")
        for _ in range(MAX_FAILED_ATTEMPTS):
            self.assertIsNone(self.store.verify("An", "wrongpass"))
        self.assertGreater(self.store.locked_seconds("An"), 0)
        self.assertIsNone(self.store.verify("An", "pass2468"))
        with patch("geo_draw.accounts.time.time", return_value=10**12):
            self.assertEqual(self.store.locked_seconds("An"), 0)
            self.assertIsNotNone(self.store.verify("An", "pass2468"))

    def test_sessions_map_tokens_to_users_until_ended(self):
        user_id = self.store.create("An", "pass2468")
        token = self.store.start_session(user_id)
        self.assertEqual(self.store.session_user(token), user_id)
        self.assertIsNone(self.store.session_user("guess"))
        self.assertIsNone(self.store.session_user(""))
        self.store.end_session(token)
        self.assertIsNone(self.store.session_user(token))
        self.assertEqual(self.store.display_name(user_id), "An")


if __name__ == "__main__":
    unittest.main()
