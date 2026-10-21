import unittest

from geo_draw.geometry_knowledge import GEOMETRY_HELP_VI, MIDDLE_SCHOOL_GEOMETRY_RULES
from geo_draw.math_symbols import THCS_MATH_SYMBOLS_VI
from geo_draw.tutor_prompts import build_system_prompt
from geo_draw.conversations import HINT, SOLUTION


class MathSymbolKnowledgeTests(unittest.TestCase):
    def test_requested_geometry_symbols_are_canonical(self):
        symbols = THCS_MATH_SYMBOLS_VI
        self.assertIn("(O): đường tròn tâm O", symbols)
        self.assertIn("R hoặc r: bán kính", symbols)
        self.assertIn("d: đường kính và d=2R", symbols)
        self.assertIn("C: chu vi", symbols)
        self.assertIn("S: diện tích", symbols)
        self.assertIn("V: thể tích", symbols)
        self.assertIn("C=2πR=πd", symbols)

    def test_all_thcs_domains_and_context_ambiguities_are_covered(self):
        symbols = THCS_MATH_SYMBOLS_VI
        for heading in (
            "SỐ, TẬP HỢP VÀ QUAN HỆ",
            "ĐẠI SỐ, PHƯƠNG TRÌNH VÀ BẤT PHƯƠNG TRÌNH",
            "HÀM SỐ VÀ MẶT PHẲNG TỌA ĐỘ",
            "HÌNH HỌC PHẲNG",
            "HÌNH KHỐI VÀ ĐẠI LƯỢNG HÌNH HỌC",
            "THỐNG KÊ VÀ XÁC SUẤT",
        ):
            self.assertIn(heading, symbols)
        self.assertIn("d có thể là đường kính, đường thẳng hay khoảng cách", symbols)
        self.assertIn("R có thể là bán kính, số thực hoặc khoảng", symbols)

    def test_tutor_and_drawing_engine_share_the_same_dictionary(self):
        self.assertIn(THCS_MATH_SYMBOLS_VI, build_system_prompt("Tính chu vi", HINT, 1))
        self.assertIn(THCS_MATH_SYMBOLS_VI, build_system_prompt("Tính chu vi", SOLUTION, 1))
        self.assertIn(THCS_MATH_SYMBOLS_VI, MIDDLE_SCHOOL_GEOMETRY_RULES)
        self.assertIn(THCS_MATH_SYMBOLS_VI, GEOMETRY_HELP_VI)


if __name__ == "__main__":
    unittest.main()
