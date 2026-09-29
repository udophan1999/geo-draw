import tempfile
import unittest
from pathlib import Path

from geo_draw.history import HistoryStore, user_id_for


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = HistoryStore(self.root / "users")
        self.scene = self.root / "scene.py"
        self.image = self.root / "figure.png"
        self.scene.write_text("class GeoScene: pass\n", encoding="utf-8")
        self.image.write_bytes(b"png")

    def tearDown(self):
        self._tmp.cleanup()

    def test_user_id_is_stable_and_path_safe(self):
        first = user_id_for("google-oauth2|123/../x")
        self.assertEqual(first, user_id_for("google-oauth2|123/../x"))
        self.assertNotEqual(first, user_id_for("someone-else"))
        self.assertTrue(first.isalnum())

    def test_entry_keeps_copies_that_survive_workspace_overwrite(self):
        entry = self.store.add("alice", "Cho tam giác ABC.", "Parser", self.scene, self.image)
        self.scene.write_text("overwritten\n", encoding="utf-8")
        self.assertEqual(entry.scene_path.read_text(encoding="utf-8"), "class GeoScene: pass\n")
        self.assertEqual(entry.image_path.read_bytes(), b"png")
        self.assertTrue(entry.scene_path.is_relative_to(self.root / "users" / "alice"))

    def test_list_is_newest_first_and_scoped_to_user(self):
        older = self.store.add("alice", "Đề 1", "Parser", self.scene, self.image)
        newer = self.store.add("alice", "Đề 2", "Parser", self.scene, self.image)
        self.store.add("bob", "Đề của Bob", "Parser", self.scene, self.image)
        self.assertEqual([e.id for e in self.store.list("alice")], [newer.id, older.id])
        self.assertEqual([e.problem for e in self.store.list("bob")], ["Đề của Bob"])

    def test_get_does_not_return_another_users_entry(self):
        entry = self.store.add("alice", "Đề 1", "Parser", self.scene, self.image)
        self.assertEqual(self.store.get("alice", entry.id).problem, "Đề 1")
        self.assertIsNone(self.store.get("bob", entry.id))


if __name__ == "__main__":
    unittest.main()
