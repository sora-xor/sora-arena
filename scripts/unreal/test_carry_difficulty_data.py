"""Difficulty-specific carry policy survives generation without implicit Normal."""
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, carry_drop_policy

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("easy", "normal", "hard")


class CarryDifficultyTests(unittest.TestCase):
    def test_authored_seed_rice_values(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_02.json").read_text())
        beat = chapter["beats"][4]
        expected = {"easy": False, "normal": False, "hard": True}
        self.assertEqual(beat["params"]["carry"]["drop_on_hit"], expected)
        self.assertEqual(beat["task"]["drop_on_hit"], expected)

    def test_uniform_and_per_difficulty_policies_are_preserved_for_every_beat(self):
        for path in sorted((ROOT / "Content/Data/campaign").glob("chapter_*.json")):
            for beat in json.loads(path.read_text())["beats"]:
                raw = beat["params"].get("carry", {}).get("drop_on_hit", False)
                expected = dict.fromkeys(NAMES, raw) if isinstance(raw, bool) else raw
                with self.subTest(beat=beat["id"]):
                    self.assertEqual(beat["task"]["drop_on_hit"], expected)
                    self.assertEqual(set(expected), set(NAMES))
                    self.assertTrue(all(type(value) is bool for value in expected.values()))
                    self.assertEqual(carry_drop_policy(raw, "test"), expected)

    def test_missing_extra_and_malformed_values_are_rejected(self):
        valid = dict.fromkeys(NAMES, False)
        bad = [None, [], "false", 0, 1, {**valid, "nightmare": True}]
        bad += [{key: value for key, value in valid.items() if key != name} for name in NAMES]
        bad += [{**valid, name: value} for name in NAMES for value in (None, 0, 1, "false", [])]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(BuildError):
                carry_drop_policy(value, "test")


if __name__ == "__main__":
    unittest.main()
