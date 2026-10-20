import unittest

from validate_ui_fonts import missing_characters


class CompositeCoverageTests(unittest.TestCase):
    def test_arabic_cannot_borrow_a_default_glyph(self):
        self.assertEqual(missing_characters("ق", {ord("ق"): "qaf"}, {}), ["ق"])

    def test_japanese_cannot_borrow_an_arabic_glyph(self):
        self.assertEqual(missing_characters("猫", {}, {ord("猫"): "cat"}), ["猫"])

    def test_mixed_notice_and_unsupported_character(self):
        self.assertEqual(missing_characters("猫 ق ★", {ord("猫"): "cat"}, {ord("ق"): "qaf"}), ["★"])
        self.assertEqual(missing_characters("猫 ق", {ord("猫"): "cat"}, {ord("ق"): "qaf"}), [])


if __name__ == "__main__":
    unittest.main()
