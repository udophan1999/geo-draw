import tempfile
import unittest
from pathlib import Path

from geo_draw.conversations import (
    ASSISTANT, TITLE_LENGTH, USER, ConversationStore, compose_problem, make_title,
)


class ComposeProblemTests(unittest.TestCase):
    def test_single_request_is_the_problem(self):
        self.assertEqual(compose_problem(["  Cho tam giác ABC. "]), "Cho tam giác ABC.")
        self.assertEqual(compose_problem([]), "")

    def test_follow_ups_are_numbered_extra_requests(self):
        problem = compose_problem(["Cho tam giác ABC.", "", "Vẽ trung điểm M của BC", "Kẻ AM"])
        self.assertTrue(problem.startswith("Cho tam giác ABC.\n\nYêu cầu bổ sung"))
        self.assertIn("1. Vẽ trung điểm M của BC", problem)
        self.assertIn("2. Kẻ AM", problem)

    def test_titles_are_one_short_line(self):
        self.assertEqual(make_title("Cho\n tam   giác"), "Cho tam giác")
        self.assertLessEqual(len(make_title("x" * 200)), TITLE_LENGTH + 1)


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = ConversationStore(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_conversations_are_per_owner_and_newest_first(self):
        first = self.store.create("alice", "Đề 1")
        second = self.store.create("alice", "Đề 2")
        self.store.create("bob", "Đề của Bob")
        self.assertEqual([c.id for c in self.store.list("alice")], [second.id, first.id])
        self.assertIsNone(self.store.get("bob", first.id))
        # A new message moves the conversation to the top.
        self.store.add_message(first.id, USER, "Vẽ thêm")
        self.assertEqual(self.store.list("alice")[0].id, first.id)

    def test_messages_keep_order_and_files(self):
        conversation = self.store.create("alice", "Đề")
        message_id, folder = self.store.new_message_dir("alice", conversation.id)
        self.assertTrue(folder.is_dir())
        self.assertTrue(folder.is_relative_to(self.store.conversation_dir("alice", conversation.id)))
        scene, image = folder / "scene.py", folder / "figure.png"
        scene.write_text("x", encoding="utf-8")
        image.write_bytes(b"png")
        self.store.add_message(conversation.id, USER, "Cho tam giác ABC.")
        self.store.add_message(conversation.id, ASSISTANT, "Đã vẽ xong", message_id=message_id,
                               image_path=image, scene_path=scene, log="ok")
        self.store.add_message(conversation.id, ASSISTANT, "Lỗi render")
        messages = self.store.messages(conversation.id)
        self.assertEqual([m.role for m in messages], [USER, ASSISTANT, ASSISTANT])
        self.assertTrue(messages[1].has_drawing)
        self.assertEqual(messages[1].scene_path, scene)
        self.assertFalse(messages[0].has_drawing)
        self.assertFalse(messages[2].has_drawing)

    def test_update_drawing_rename_and_delete(self):
        conversation = self.store.create("alice", "Đề từ ảnh")
        message = self.store.add_message(conversation.id, ASSISTANT, "Đã vẽ",
                                         image_path=Path("a.png"), scene_path=Path("s.py"))
        self.store.update_drawing(message.id, Path("b.png"), None)
        self.assertEqual(self.store.messages(conversation.id)[0].image_path, Path("b.png"))
        self.store.rename("alice", conversation.id, "Cho hình vuông ABCD")
        self.assertEqual(self.store.get("alice", conversation.id).title, "Cho hình vuông ABCD")
        _, folder = self.store.new_message_dir("alice", conversation.id)
        self.store.delete("bob", conversation.id)  # not bob's: nothing happens
        self.assertIsNotNone(self.store.get("alice", conversation.id))
        self.store.delete("alice", conversation.id)
        self.assertIsNone(self.store.get("alice", conversation.id))
        self.assertEqual(self.store.messages(conversation.id), [])
        self.assertFalse(folder.exists())

    def test_import_is_idempotent(self):
        messages = [(USER, "Cho tam giác ABC.", None, None),
                    (ASSISTANT, "Parser", Path("f.png"), Path("s.py"))]
        for _ in range(2):
            self.store.import_conversation("alice", "hold1", "Cho tam giác ABC.", 100.0, messages)
        self.assertEqual(len(self.store.list("alice")), 1)
        imported = self.store.messages("hold1")
        self.assertEqual([m.role for m in imported], [USER, ASSISTANT])
        self.assertTrue(imported[1].has_drawing)


if __name__ == "__main__":
    unittest.main()
