import io
import unittest

import pymupdf
from PIL import Image
from pillow_heif import from_pillow

from geo_draw.image_inputs import normalize_problem_file


class ImageInputTests(unittest.TestCase):
    def test_regular_raster_is_preserved(self):
        self.assertEqual(normalize_problem_file(b"png", "image/png"), [(b"png", "image/png")])

    def test_pdf_pages_are_rendered_to_ordered_png_images(self):
        document = pymupdf.open()
        for label in ("Trang 1", "Trang 2"):
            page = document.new_page(width=300, height=400)
            page.insert_text((40, 60), label)
        pdf = document.tobytes()
        document.close()

        pages = normalize_problem_file(pdf, "application/pdf")

        self.assertEqual(len(pages), 2)
        self.assertTrue(all(mime == "image/png" for _data, mime in pages))
        self.assertTrue(all(data.startswith(b"\x89PNG") for data, _mime in pages))

    def test_pdf_over_four_pages_is_rejected(self):
        document = pymupdf.open()
        for _ in range(5):
            document.new_page()
        pdf = document.tobytes()
        document.close()
        with self.assertRaisesRegex(ValueError, "tối đa 4 trang"):
            normalize_problem_file(pdf, "application/pdf")

    def test_heic_is_converted_to_png(self):
        source = Image.new("RGB", (32, 24), "white")
        heic = io.BytesIO()
        from_pillow(source).save(heic)

        [(png, mime)] = normalize_problem_file(heic.getvalue(), "image/heic")

        self.assertEqual(mime, "image/png")
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_unknown_or_empty_files_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "đang trống"):
            normalize_problem_file(b"", "image/png")
        with self.assertRaisesRegex(ValueError, "PNG, JPG"):
            normalize_problem_file(b"data", "text/plain")


if __name__ == "__main__":
    unittest.main()
