import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from geo_draw.renderer import render_scene


class RendererTests(unittest.TestCase):
    def test_animated_render_also_creates_png_preview(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scene = root / "scene.py"
            scene.write_text("class GeoScene: pass", encoding="utf-8")
            image = root / "preview.png"
            video = root / "animation.mp4"
            png_calls = 0

            def newest(_folder, pattern):
                nonlocal png_calls
                if pattern == "*.mp4":
                    return video
                png_calls += 1
                return image if png_calls > 1 else None

            completed = SimpleNamespace(returncode=0, stdout="ok", stderr="")
            with patch("geo_draw.renderer.subprocess.run", return_value=completed) as run, \
                    patch("geo_draw.renderer._newest", side_effect=newest):
                result = render_scene(scene, root / "media", animate=True)

            self.assertTrue(result.ok)
            self.assertEqual(result.image_path, image)
            self.assertEqual(result.video_path, video)
            self.assertEqual(run.call_count, 2)
            self.assertIn("-s", run.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
