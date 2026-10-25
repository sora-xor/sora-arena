"""Authored chapter-six carrying permissions; these never grant weapon unlocks."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, infiltration_equipment

ROOT = Path(__file__).resolve().parents[2]


class InfiltrationLoadoutTests(unittest.TestCase):
    def setUp(self):
        self.chapter = json.loads((ROOT / "Content/Data/campaign/chapter_06.json").read_text())
        self.document = {"start_loadout": copy.deepcopy(self.chapter["ext"]["start_loadout"])}
        self.beats = copy.deepcopy(self.chapter["beats"])

    def test_every_checkpoint_has_the_authored_carried_arms(self):
        infiltration_equipment(self.document, self.beats, "ch06")
        for i, beat in enumerate(self.beats):
            expected = [0, 4]
            if i >= 2:
                expected += [18]
            if i >= 4:
                expected += [3]
            if i >= 6:
                expected += [13]
            if i >= 9:
                expected += [10]
            with self.subTest(beat=beat["id"]):
                self.assertEqual(beat["task"]["equipment_weapons"], sorted(expected))
                self.assertIsNone(beat["task"]["recovery"])
                self.assertEqual(beat, self.chapter["beats"][i], "generated data must be current")

    def test_permissions_do_not_change_unlocks_or_add_a_stringing_hold(self):
        before = copy.deepcopy(self.beats)
        for beat in self.beats:
            beat["task"]["equipment_weapons"] = None
        infiltration_equipment(self.document, self.beats, "ch06")
        self.assertEqual(self.beats, before)
        self.assertEqual(self.beats[2]["ext"]["setup"], {"string_bow_at_start": True, "string_anim_s": 3})
        self.assertTrue(self.beats[6]["optional"])
        self.assertEqual(self.beats[6]["unlocks"]["weapons"], [13])
        self.assertTrue(all(not b["unlocks"]["grants"] for b in self.beats))

    def test_start_loadout_fails_closed(self):
        for key, value in (("hip", False), ("hip", 0.0), ("side", 0), ("back", 19),
                           ("back_strung_at", "ch06.b02"), ("polearm", 9), ("firearm", 1),
                           ("quiver_arrows", 13), ("quiver_arrows", True), ("armor", "plate")):
            document = copy.deepcopy(self.document)
            document["start_loadout"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                infiltration_equipment(document, self.beats, "ch06")
        for key in self.document["start_loadout"]:
            document = copy.deepcopy(self.document)
            del document["start_loadout"][key]
            with self.subTest(missing=key), self.assertRaises(BuildError):
                infiltration_equipment(document, self.beats, "ch06")
        with self.assertRaises(BuildError):
            infiltration_equipment({}, self.beats, "ch06")

    def test_setup_drift_cannot_silently_release_the_bow(self):
        for setup in (None, {}, {"string_bow_at_start": 1, "string_anim_s": 3},
                      {"string_bow_at_start": False, "string_anim_s": 3},
                      {"string_bow_at_start": True, "string_anim_s": 2.99},
                      {"string_bow_at_start": True, "string_anim_s": True}):
            beats = copy.deepcopy(self.beats)
            beats[2]["ext"]["setup"] = setup
            with self.subTest(setup=setup), self.assertRaises(BuildError):
                infiltration_equipment(self.document, beats, "ch06")

    def test_handoff_drift_and_early_auto_grants_fail_closed(self):
        for index, key, value in ((3, "weapons", [3]), (4, "weapons", []),
                                  (6, "weapons", [13, 1]), (9, "weapons", [10.0]),
                                  (0, "grants", [13])):
            beats = copy.deepcopy(self.beats)
            beats[index]["unlocks"][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(BuildError):
                infiltration_equipment(self.document, beats, "ch06")
        for index in (4, 6, 9):
            beats = copy.deepcopy(self.beats)
            beats[index]["optional"] = not beats[index]["optional"]
            with self.subTest(optional=index), self.assertRaises(BuildError):
                infiltration_equipment(self.document, beats, "ch06")

    def test_bad_order_duplicates_and_recovery_are_rejected(self):
        variants = [self.beats[:-1], self.beats + [self.beats[-1]],
                    self.beats[:1] + [self.beats[2], self.beats[1]] + self.beats[3:]]
        recovery = copy.deepcopy(self.beats)
        recovery[2]["task"]["recovery"] = {"string_ms": 3000}
        for beats in variants + [recovery]:
            with self.assertRaises(BuildError):
                infiltration_equipment(self.document, beats, "ch06")

    def test_other_chapters_keep_their_existing_loadout_contract(self):
        for number in (3, 7):
            chapter = json.loads((ROOT / f"Content/Data/campaign/chapter_{number:02d}.json").read_text())
            before = copy.deepcopy(chapter["beats"])
            infiltration_equipment({}, chapter["beats"], f"ch{number:02d}")
            self.assertEqual(chapter["beats"], before)


if __name__ == "__main__":
    unittest.main()
