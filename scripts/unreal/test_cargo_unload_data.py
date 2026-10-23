"""The cargo ride must retain its authored, validated continuous unload hold."""
import copy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, normalize_task, fail
from campaign_space import ride_mount, _kit
from campaign_cargo import cargo_manifest, MAX_QUANTITY
from validate_campaign import CampaignError, check_cargo_unload, check_spook_dismount, check_cargo_manifest

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

    def test_bunta_lead_and_fear_contract(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_04.json").read_text())
        mount = chapter["space"]["beats"][13]["mount"]
        self.assertEqual(self.beat["params"]["cargo"]["carrier"], "pack_horse")
        self.assertEqual(mount["pack"], [{"id": "pack_horse_cargo", "follow": "lead", "speed_cm_s": 0,
                                         "spacing_cm": 300, "hp": 0}])
        self.assertEqual(mount["fear"], {"radius_cm": 900, "recover_ms": 2500})
        self.assertTrue(mount["dismount"])
        self.assertFalse(self.beat["task"]["horse_down_retries"])

    def test_cargo_manifest_and_three_drying_stands(self):
        chapter = json.loads((ROOT / "Content/Data/campaign/chapter_04.json").read_text())
        space = chapter["space"]["beats"][13]
        self.assertEqual(space["mount"]["cargo"], {"item": "barley_sheaf", "total": 30, "per_dropoff": 10})
        self.assertEqual(space["kit"], {"work": "cargo", "item": "bale", "pickups": [],
                                      "dropoffs": ["drying_stand"] * 3, "targets": [], "party": []})
        check_cargo_manifest(self.beat, space["mount"], space["kit"])

    def test_invalid_authored_quantities_cannot_produce_delivery_credit(self):
        for key in ("qty", "per_dropoff"):
            for value in (None, True, False, 0, -1, 1.5, 30.0, "30", [], {}, MAX_QUANTITY + 1):
                beat = copy.deepcopy(self.beat)
                beat["params"]["cargo"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                    normalize_task(beat)
                with self.assertRaises(CampaignError):
                    check_cargo_unload(beat)
            beat = copy.deepcopy(self.beat)
            del beat["params"]["cargo"][key]
            with self.assertRaises(BuildError):
                normalize_task(beat)
        for patch in ({"qty": 31}, {"per_dropoff": 11}, {"dropoffs": ["hamlet_kami"] * 3},
                      {"qty": 90, "dropoffs": [f"hamlet_{n}" for n in range(9)]},
                      {"carrier": "kurimaru"}, {"item": "rice"}):
            beat = copy.deepcopy(self.beat)
            beat["params"]["cargo"].update(patch)
            with self.subTest(patch=patch), self.assertRaises(BuildError):
                normalize_task(beat)

    def test_quantity_validation_uses_wide_arithmetic_and_bounded_groups(self):
        for count, per in ((1, MAX_QUANTITY), (3, 715827882), (8, 1)):
            beat = copy.deepcopy(self.beat)
            beat["params"]["cargo"].update(qty=count * per, per_dropoff=per,
                                          dropoffs=[f"hamlet_{n}" for n in range(count)])
            task = normalize_task(beat)
            self.assertEqual(task["count"], count)
            self.assertEqual(cargo_manifest(beat, fail)["total"], count * per)
        beat = copy.deepcopy(self.beat)
        beat["params"]["cargo"].update(qty=MAX_QUANTITY, per_dropoff=MAX_QUANTITY)
        with self.assertRaises(BuildError):
            normalize_task(beat)

    def test_normalized_cargo_and_kit_cannot_disagree_with_authored_transfer(self):
        mount, kit = ride_mount(self.beat, fail), _kit(self.beat)
        for value in (None, {}, {"item": "barley_sheaf", "total": 31, "per_dropoff": 10},
                      {"item": "barley_sheaf", "total": 30.0, "per_dropoff": 10},
                      {"item": "rice", "total": 30, "per_dropoff": 10}):
            with self.subTest(value=value), self.assertRaises(CampaignError):
                check_cargo_manifest(self.beat, {**mount, "cargo": value}, kit)
        missing = copy.deepcopy(mount); del missing["cargo"]
        with self.assertRaises(CampaignError): check_cargo_manifest(self.beat, missing, kit)
        for pack in ([], mount["pack"] * 2, [{**mount["pack"][0], "follow": "convoy"}]):
            with self.assertRaises(CampaignError): check_cargo_manifest(self.beat, {**mount, "pack": pack}, kit)
        for patch in ({"work": None}, {"item": "crate"}, {"dropoffs": ["drying_stand"] * 2}):
            with self.assertRaises(CampaignError): check_cargo_manifest(self.beat, mount, {**kit, **patch})

    def test_non_cargo_mounts_require_null_manifest(self):
        count = 0
        for path in (ROOT / "Content/Data/campaign").glob("chapter_*.json"):
            chapter = json.loads(path.read_text())
            for beat, space in zip(chapter["beats"], chapter["space"]["beats"]):
                if space["mount"] is None or beat["id"] == "ch04.b14": continue
                count += 1
                check_cargo_manifest(beat, space["mount"], space["kit"])
                self.assertIsNone(space["mount"]["cargo"])
                with self.assertRaises(CampaignError):
                    check_cargo_manifest(beat, {**space["mount"], "cargo": {"item": "barley_sheaf", "total": 30, "per_dropoff": 10}}, space["kit"])
        self.assertEqual(count, 7)

    def test_only_authored_cargo_spook_dismounts(self):
        found, mounts = [], 0
        for path in (ROOT / "Content/Data/campaign").glob("chapter_*.json"):
            chapter = json.loads(path.read_text())
            for beat, space in zip(chapter["beats"], chapter["space"]["beats"]):
                mount = space["mount"]
                if mount is None:
                    continue
                mounts += 1
                check_spook_dismount(beat, mount)
                if mount["spook_dismount"]:
                    found.append(beat["id"])
                else:
                    forged = {**mount, "spook_dismount": True}
                    with self.subTest(beat=beat["id"]), self.assertRaises(CampaignError):
                        check_spook_dismount(beat, forged)
        self.assertEqual(mounts, 8)
        self.assertEqual(found, ["ch04.b14"])
        self.assertEqual(self.beat["params"]["on_spook"], "dismount_continue")
        self.assertTrue(ride_mount(self.beat, fail)["spook_dismount"])

    def test_spook_policy_rejects_bad_values_and_incompatible_rides(self):
        for value in (None, True, False, 1, "checkpoint", "", [], {}):
            beat = copy.deepcopy(self.beat)
            beat["params"]["on_spook"] = value
            with self.subTest(value=value), self.assertRaises(BuildError):
                ride_mount(beat, fail)
        for key, value in (("mode", "travel"), ("dismount_allowed", False),
                           ("on_horse_down", "checkpoint"), ("fear", None),
                           ("fear", {"spook_radius_cm": 900, "recover_s": False}),
                           ("fear", {"spook_radius_cm": 900, "recover_s": float("inf")}),
                           ("cargo", {"carrier": "kurimaru"})):
            beat = copy.deepcopy(self.beat)
            beat["params"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                ride_mount(beat, fail)

    def test_normalized_spook_policy_is_required_and_exact(self):
        mount = ride_mount(self.beat, fail)
        for value in (None, 0, 1, "true", False):
            forged = {**mount, "spook_dismount": value}
            with self.subTest(value=value), self.assertRaises(CampaignError):
                check_spook_dismount(self.beat, forged)
        del mount["spook_dismount"]
        with self.assertRaises(CampaignError):
            check_spook_dismount(self.beat, mount)
        beat = copy.deepcopy(self.beat)
        del beat["params"]["on_spook"]
        self.assertFalse(ride_mount(beat, fail)["spook_dismount"])
        beat["params"]["on_spook"] = "shy"
        self.assertFalse(ride_mount(beat, fail)["spook_dismount"])

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
