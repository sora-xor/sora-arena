"""Authored lamp controls must survive normalization into playable data."""
import json
from pathlib import Path
import unittest

from campaign_fieldcraft import _lamp

ROOT = Path(__file__).resolve().parents[2]


def fail(where, message):
    raise ValueError(f"{where}: {message}")


class LampAuthoring(unittest.TestCase):
    def test_ward_brazier_preserves_authored_permanent_four_metre_light(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_03.json").read_text())
        authored = chapter["beats"][2]["ext"]["static_lights"][0]
        normalized = _lamp(authored, fail, "ch03.b03")
        runtime = next(row for row in chapter["space"]["beats"][2]["fieldcraft"]["lamps"]
                       if row["id"] == "brazier_b03")
        self.assertEqual(normalized["radius_cm"], 400)
        self.assertEqual((normalized["snuff"], normalized["hold_ms"]), ("none", 0))
        self.assertEqual({key: runtime[key] for key in normalized}, normalized)

    def test_invalid_radius_is_rejected_instead_of_silently_using_kind_default(self):
        for radius in (0, -1, True, False, None, "400", 400.25,
                       float("nan"), float("inf"), -float("inf"), 2147483648):
            with self.subTest(radius=radius), self.assertRaises(ValueError):
                _lamp({"id": "lamp_test", "radius_cm": radius}, fail, "test")

    def test_explicit_reach_does_not_change_extinguish_mode_or_relight(self):
        lamp = _lamp({"id": "lamp_test", "radius_cm": 1234,
                      "extinguish": "interact_hold_s:2", "relight_s": 7}, fail, "test")
        self.assertEqual((lamp["radius_cm"], lamp["snuff"], lamp["hold_ms"], lamp["relight_ms"]),
                         (1234, "hold", 2000, 7000))
        shot = _lamp({"id": "lamp_test", "radius_cm": 800, "extinguishable": "arrow"}, fail, "test")
        self.assertEqual((shot["radius_cm"], shot["snuff"], shot["hold_ms"]), (800, "shot", 0))

    def test_unspecified_reach_retains_existing_andon_and_brazier_defaults(self):
        for name, radius in (("andon_example", 650), ("brazier_example", 600)):
            with self.subTest(name=name):
                lamp = _lamp(name, fail, "test")
                self.assertEqual((lamp["radius_cm"], lamp["snuff"], lamp["hold_ms"]), (radius, "hold", 1000))


if __name__ == "__main__":
    unittest.main()
