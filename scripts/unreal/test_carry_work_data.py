"""The seed granary's authored seal gate is preserved and reachable."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, carry_gate, carry_dropoff_capacity, normalize_task
from validate_campaign import CampaignError, check_dropoff_capacity

ROOT = Path(__file__).resolve().parents[2]


class CarryWorkDataTests(unittest.TestCase):
    def test_seal_contract_and_point(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_02.json").read_text())
        beat, space = chapter["beats"][4], chapter["space"]["beats"][4]
        self.assertEqual(beat["task"]["carry_gate"], {
            "point": "seal_kura_sw", "hold_ms": 3000, "contest": "pause", "tool": "yari_ishizuki"})
        self.assertEqual(space["carry_gate"], space["pickups"][0])
        volume = next(v for v in space["volumes"] if v["event"] == "volume_enter:vol_kura_sw_door")
        self.assertEqual(volume["center"], space["carry_gate"])
        self.assertEqual(beat["task"]["carry_gate"], carry_gate(beat["ext"]["gate_interact"], "test"))

    def test_only_authored_gate_is_added(self):
        found = []
        for path in (ROOT / "Content/Data/campaign").glob("chapter_*.json"):
            chapter = json.loads(path.read_text())
            for beat, space in zip(chapter["beats"], chapter["space"]["beats"]):
                self.assertEqual(beat["task"]["carry_gate"] is None, space["carry_gate"] is None)
                if beat["task"]["carry_gate"]:
                    found.append(beat["id"])
        self.assertEqual(found, ["ch02.b05"])

    def test_invalid_gate_contracts_are_rejected(self):
        valid = {"interact_points": ["seal_kura_sw"], "per_point_s": 3, "contest": "pause", "tool": "yari_ishizuki"}
        bad = [{**valid, key: value} for key, values in {
            "interact_points": [[], ["a", "b"], None], "per_point_s": [0, -1, None, "3", True],
            "contest": ["decay", None], "tool": ["katana", None]}.items() for value in values]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(BuildError):
                carry_gate(raw, "test")


class CarryCapacityDataTests(unittest.TestCase):
    def setUp(self):
        self.beat = json.loads((ROOT / "Content/Data/campaign/chapter_02.json").read_text())["beats"][4]
        self.names = ["pack_horse_a", "pack_horse_b"]

    def test_authored_map_and_asymmetric_name_order(self):
        self.assertEqual(self.beat["task"]["dropoff_capacity"], dict.fromkeys(self.names, 2))
        check_dropoff_capacity(self.beat)
        self.beat["params"]["carry"]["x_dropoff_capacity"] = {"pack_horse_b": 3, "pack_horse_a": 1}
        self.beat["task"] = normalize_task(self.beat)
        self.assertEqual(list(self.beat["task"]["dropoff_capacity"].items()), [(self.names[0], 1), (self.names[1], 3)])
        check_dropoff_capacity(self.beat)
        # Extra capacity is allowed; it cannot create extra goods at runtime.
        self.assertEqual(carry_dropoff_capacity(dict.fromkeys(self.names, 3), self.names, 4, "test"),
                         dict.fromkeys(self.names, 3))

    def test_all_unmapped_carries_and_cargo_retain_derived_capacities(self):
        for path in (ROOT / "Content/Data/campaign").glob("chapter_*.json"):
            for beat in json.loads(path.read_text())["beats"]:
                with self.subTest(beat=beat["id"]):
                    check_dropoff_capacity(beat)
                    if "x_dropoff_capacity" not in beat["params"].get("carry", {}):
                        self.assertIsNone(beat["task"]["dropoff_capacity"])
                    if beat["type"] == "horseback_ride" and beat["task"]["goal"] == "deliveries":
                        self.assertEqual(beat["task"]["count"], len(beat["task"]["dropoffs"]))

    def test_wrong_missing_extra_names_and_invalid_capacities_are_rejected(self):
        valid = dict.fromkeys(self.names, 2)
        invalid = [None, [], "2", {}, {self.names[0]: 4}, {**valid, "extra": 1},
                   {"wrong_name": 2, self.names[1]: 2}, dict.fromkeys(self.names, 1)]
        invalid += [{**valid, self.names[0]: value} for value in (0, -1, True, 1.5, "2", None, 100, 2**31)]
        for value in invalid:
            beat = copy.deepcopy(self.beat)
            beat["params"]["carry"]["x_dropoff_capacity"] = value
            beat["task"]["dropoff_capacity"] = value
            with self.subTest(value=value), self.assertRaises(BuildError):
                normalize_task(beat)
            with self.subTest(validator=value), self.assertRaises(CampaignError):
                check_dropoff_capacity(beat)
        with self.assertRaises(BuildError):
            carry_dropoff_capacity(valid, [self.names[0], self.names[0]], 4, "test")
        beat = copy.deepcopy(self.beat)
        del beat["task"]["dropoff_capacity"]
        with self.assertRaises(CampaignError):
            check_dropoff_capacity(beat)

    def test_invalid_goods_counts_and_lost_authored_mapping_are_rejected(self):
        for count in (0, -1, True, 2.0, "4", None, 100):
            beat = copy.deepcopy(self.beat)
            beat["params"]["carry"]["count"] = count
            beat["task"]["count"] = count
            with self.subTest(count=count), self.assertRaises(BuildError):
                normalize_task(beat)
            with self.subTest(validator=count), self.assertRaises(CampaignError):
                check_dropoff_capacity(beat)
        for lost in (None, {self.names[0]: 1, self.names[1]: 3}):
            self.beat["task"]["dropoff_capacity"] = lost
            with self.subTest(lost=lost), self.assertRaises(CampaignError):
                check_dropoff_capacity(self.beat)


if __name__ == "__main__":
    unittest.main()
