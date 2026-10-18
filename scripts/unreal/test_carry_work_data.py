"""The seed granary's authored seal gate is preserved and reachable."""
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, carry_gate

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


if __name__ == "__main__":
    unittest.main()
