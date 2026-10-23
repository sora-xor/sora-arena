"""The cargo ride must retain its authored, validated continuous unload hold."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, normalize_task
from validate_campaign import CampaignError, check_cargo_unload

ROOT = Path(__file__).resolve().parents[2]


class CargoUnloadDataTests(unittest.TestCase):
    def setUp(self):
        self.beat = json.loads((ROOT / "Content/Data/campaign/chapter_04.json").read_text())["beats"][13]

    def test_authored_three_seconds_and_delivery_wave_survive(self):
        task = self.beat["task"]
        self.assertEqual(self.beat["params"]["cargo"]["unload_hold_s"], 3.0)
        self.assertEqual(task["unload_hold_ms"], 3000)
        self.assertEqual(normalize_task(self.beat), task)
        self.assertEqual(task["dropoffs"], ["hamlet_kami", "hamlet_naka", "hamlet_shimo"])
        self.assertEqual(task["count"], 3)
        self.assertEqual(task["waves"][1]["event"], "item_delivered:hamlet_naka")
        self.assertEqual(task["waves"][1]["trigger"], "event")
        check_cargo_unload(self.beat)

    def test_all_other_beats_have_no_unload_hold(self):
        found = []
        for path in (ROOT / "Content/Data/campaign").glob("chapter_*.json"):
            for beat in json.loads(path.read_text())["beats"]:
                check_cargo_unload(beat)
                if beat["task"]["unload_hold_ms"]:
                    found.append(beat["id"])
                else:
                    forged = copy.deepcopy(beat)
                    forged["task"]["unload_hold_ms"] = 3000
                    with self.subTest(beat=beat["id"]), self.assertRaises(CampaignError):
                        check_cargo_unload(forged)
        self.assertEqual(found, ["ch04.b14"])

    def test_invalid_authored_hold_is_rejected(self):
        for value in (None, True, False, "3", [], 0, -1, .0004, 1e-10, 3.0004,
                      float("inf"), float("nan"), (1 << 30) / 1000 + .001):
            beat = copy.deepcopy(self.beat)
            beat["params"]["cargo"]["unload_hold_s"] = value
            with self.subTest(normalize=value), self.assertRaises(BuildError):
                normalize_task(beat)
            with self.subTest(validate=value), self.assertRaises(CampaignError):
                check_cargo_unload(beat)
        del self.beat["params"]["cargo"]["unload_hold_s"]
        with self.assertRaises(BuildError):
            normalize_task(self.beat)
        with self.assertRaises(CampaignError):
            check_cargo_unload(self.beat)

    def test_missing_or_changed_normalized_duration_is_rejected(self):
        for value in (None, True, "3000", 3000.0, 0, -1, 2999, 3001, (1 << 30) + 1):
            beat = copy.deepcopy(self.beat)
            beat["task"]["unload_hold_ms"] = value
            with self.subTest(value=value), self.assertRaises(CampaignError):
                check_cargo_unload(beat)
        del self.beat["task"]["unload_hold_ms"]
        with self.assertRaises(CampaignError):
            check_cargo_unload(self.beat)

    def test_valid_duration_boundaries_are_not_hardcoded_to_three_seconds(self):
        for value in (1, 2999, 3000, 3001, 1 << 30):
            beat = copy.deepcopy(self.beat)
            beat["params"]["cargo"]["unload_hold_s"] = value / 1000
            beat["task"] = normalize_task(beat)
            self.assertEqual(beat["task"]["unload_hold_ms"], value)
            check_cargo_unload(beat)


if __name__ == "__main__":
    unittest.main()
