"""The authored maai contract must survive generation and fail closed."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, maai_lesson
from validate_campaign import director_event_error

ROOT = Path(__file__).resolve().parents[2]


class MaaiDataTests(unittest.TestCase):
    def setUp(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_01.json").read_text())
        self.chapter = chapter
        self.beat = chapter["beats"][1]
        self.raw = copy.deepcopy(self.beat["ext"]["maai"])

    def test_authored_contract_is_not_discarded(self):
        expected = {"inner_cm": 166, "outer_cm": 224, "hold_ms": 500, "facing_permille": 700,
                    "hint_ms": 6000, "moves": [{"forward_cm": -120, "right_cm": 0},
                    {"forward_cm": 0, "right_cm": -150}, {"forward_cm": 80, "right_cm": 0}]}
        self.assertEqual(self.beat["task"]["maai"], expected)
        self.assertEqual(maai_lesson(self.raw, 3, "test"), expected)

    def test_incomplete_and_malformed_contracts_fail_closed(self):
        for key in self.raw:
            bad = copy.deepcopy(self.raw)
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(BuildError):
                maai_lesson(bad, 3, "test")
        for key, value in (("ring_inner_cm", 224), ("ring_outer_cm", 165), ("hold_ms", 0),
                           ("facing_dot_min", 1.1), ("hint_after_s", 0), ("mentor_moves", [])):
            bad = {**self.raw, key: value}
            with self.subTest(key=key), self.assertRaises(BuildError):
                maai_lesson(bad, 3, "test")
        for key, value in (("step", 3), ("step", True), ("move", "teleport"), ("move", []), ("cm", -10)):
            bad = copy.deepcopy(self.raw)
            bad["mentor_moves"][0][key] = value
            with self.subTest(move=key), self.assertRaises(BuildError):
                maai_lesson(bad, 3, "test")

    def test_events_require_a_measured_gate(self):
        for event in ("maai_step_ok", "gate_retry:maai_step"):
            self.assertIsNone(director_event_error({"on": event}, self.beat, 0, self.chapter))
            bad = copy.deepcopy(self.beat)
            bad["task"]["maai"] = None
            self.assertIsNotNone(director_event_error({"on": event}, bad, 0, self.chapter))


if __name__ == "__main__":
    unittest.main()
