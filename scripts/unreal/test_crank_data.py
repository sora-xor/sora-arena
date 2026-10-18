"""Cooperative rates, net rescue and collision-clear helper positions."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, fail
from campaign_crank import cooperation, player_work
from validate_campaign import CampaignError, check_crank_player
from campaign_fieldcraft import _clear, _inside

ROOT = Path(__file__).resolve().parents[2]


def chapter(number):
    return json.loads((ROOT / f"Content/Data/campaign/chapter_{number:02}.json").read_text())


class CrankDataTests(unittest.TestCase):
    def test_authored_contracts_and_clear_walks(self):
        for number, index, npc, rate, credit, suspend, retreat, locks in (
                (4, 5, "otane", 200, 1000, True, 0, []),
                (5, 5, "bellows_boy", 500, 400, False, 0, []),
                (7, 6, "kohagi", 150, 1000, True, 500, [250, 500, 750])):
            data = chapter(number)
            beat, space = data["beats"][index], data["space"]["beats"][index]
            coop = {"npcs": [npc], "per_npc_milliturns_s": rate, "progress_permille": credit,
                    "suspends_decay": suspend, "retreat_cm": retreat, "ratchets_permille": locks}
            self.assertEqual(beat["task"]["crank_coop"], coop)
            self.assertEqual(cooperation(beat, fail), coop)
            person, = space["fieldcraft"]["people"]
            self.assertEqual((person["id"], person["target"]), (npc, -1))
            zone = data["space"]["zones"][space["zone"]]
            a, b = person["at"], person["cover"]
            for i in range(101):
                point = [a[0]+(b[0]-a[0])*i/100, a[1]+(b[1]-a[1])*i/100]
                self.assertTrue(_inside(zone["rect"], point, 80))
                self.assertTrue(_clear(point, zone["cover"], 80))

    def test_boy_is_netted_until_freed_without_haul_timer(self):
        nets = chapter(5)["space"]["beats"][5]["fieldcraft"]["nets"]
        self.assertEqual(nets["quarry"], [{"id": "bellows_boy", "kind": "person", "index": 0, "hp": 0}])
        self.assertEqual((nets["net_waves"], nets["nets_per_wave"]), ([0], [1]))
        self.assertEqual((nets["haul_ms"], nets["cut_ms"], nets["windup_ms"]), (0, 1000, 800))
        self.assertTrue(nets["tether"])

    def test_invalid_contracts_fail_closed(self):
        original = chapter(7)["beats"][6]
        for key, value in (("coop_npc_rate_turns_s", True), ("coop_npc_rate_turns_s", 0),
                           ("coop_npc_suspends_decay", 1), ("coop_npc_leaves_if_enemy_within_cm", -1),
                           ("ratchet_locks", [.5, .25]), ("ratchet_locks", [.25, .25]),
                           ("ratchet_locks", [1]), ("ratchet_locks", None)):
            beat = deepcopy(original)
            beat["ext"]["override"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                cooperation(beat, fail)

    def test_lift_rate_is_explicitly_per_named_person(self):
        data = chapter(8)
        beat, space = data["beats"][10], data["space"]["beats"][10]
        coop = beat["task"]["crank_coop"]
        names = ["tetsugoro", "league_engineer_1", "league_engineer_2"]
        self.assertEqual(coop, {"npcs": names, "per_npc_milliturns_s": 150, "progress_permille": 1000,
                                "suspends_decay": False, "retreat_cm": 0, "ratchets_permille": []})
        self.assertEqual(cooperation(beat, fail), coop)
        self.assertEqual(beat["params"]["crank"]["coop_npc"], {"npcs": names, "turns_per_s_per_npc": .15})
        self.assertEqual([person["id"] for person in space["fieldcraft"]["people"]], names)
        self.assertEqual(beat["task"]["decay_permille"] * beat["task"]["count"], 480)
        self.assertEqual(3 * coop["per_npc_milliturns_s"] - 480, -30)
        self.assertEqual(beat["params"]["crank"]["moving_platform"]["travel_cm"], 11500)
        self.assertIn("decay x3", beat["params"]["crank"]["rope_hazard"]["rule"])
        zone = data["space"]["zones"][space["zone"]]
        for person in space["fieldcraft"]["people"]:
            self.assertTrue(_inside(zone["rect"], person["at"], 80))
            self.assertTrue(_clear(person["at"], zone["cover"], 80))
        for raw in ({"npcs": names, "turns_per_s": .15}, {"npcs": [], "turns_per_s_per_npc": .15},
                    {"npcs": [names[0], names[0]], "turns_per_s_per_npc": .15},
                    {"npcs": names, "turns_per_s_per_npc": 0}, {"npcs": names, "turns_per_s_per_npc": True}):
            bad = deepcopy(beat)
            bad["params"]["crank"]["coop_npc"] = raw
            with self.subTest(raw=raw), self.assertRaises(BuildError):
                cooperation(bad, fail)


    def test_player_contracts_are_exact_and_helpers_are_separate(self):
        expected = {"ch04.b06": (6, 0, False, 0, False), "ch05.b06": (2, 2, False, 0, True),
                    "ch07.b07": (8, 0, True, 600, False), "ch08.b11": (5, 0, False, 0, False)}
        found = set()
        for number in range(1, 9):
            for beat in chapter(number)["beats"]:
                contract = player_work(beat, fail)
                self.assertEqual(beat["task"]["crank_player"], contract)
                check_crank_player(beat)
                if contract:
                    found.add(beat["id"])
                    self.assertEqual(tuple(contract.values()), expected[beat["id"]])
                    helper_before = cooperation(beat, fail)
                    beat["params"]["crank"]["stamina_per_turn"] = 1
                    self.assertEqual(cooperation(beat, fail), helper_before)
        self.assertEqual(found, set(expected))
        self.assertTrue(all(beat["task"]["crank_player"] is None for beat in chapter(2)["beats"]))

    def test_invalid_player_costs_and_assists_are_rejected(self):
        original = chapter(7)["beats"][6]
        for value in (True, 0, -1, 101, 8.5, None):
            beat = deepcopy(original)
            beat["params"]["crank"]["stamina_per_turn"] = value
            with self.subTest(cost=value), self.assertRaises(BuildError):
                player_work(beat, fail)
        for key, value in (("two_handed", False), ("loadout_while_cranking", "katana"),
                           ("overspeed", "progress"), ("accessibility_hold_to_crank_turns_s", True),
                           ("accessibility_hold_to_crank_turns_s", 0), ("accessibility_hold_to_crank_turns_s", .2),
                           ("accessibility_hold_to_crank_turns_s", 1), ("accessibility_hold_to_crank_turns_s", .5)):
            beat = deepcopy(original)
            beat["ext"]["override"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(BuildError):
                player_work(beat, fail)
        del original["ext"]["override"]
        with self.assertRaises(BuildError):
            player_work(original, fail)
        bellows = chapter(5)["beats"][5]
        bellows["ext"]["flame_gauge"]["above"] = "no stamina cost"
        with self.assertRaises(BuildError):
            player_work(bellows, fail)


    def test_bellows_tread_and_all_gauge_states_are_required(self):
        original = chapter(5)["beats"][5]
        for key in ("below", "in", "above"):
            beat = deepcopy(original)
            beat["ext"]["flame_gauge"][key] = "progress color"
            with self.subTest(key=key), self.assertRaises(BuildError):
                player_work(beat, fail)
        for value in (None, "press interact", "alternate_right_left_tread"):
            beat = deepcopy(original)
            beat["ext"]["input"] = value
            with self.subTest(value=value), self.assertRaises(BuildError):
                player_work(beat, fail)
        original["task"]["crank_player"]["alternate_treads"] = False
        with self.assertRaises(CampaignError):
            check_crank_player(original)

    def test_normalized_player_contract_cannot_lose_authored_fields(self):
        original = chapter(7)["beats"][6]
        for key, value in (("stamina_per_turn", 0), ("stamina_per_turn", 6),
                           ("overspeed_cost_multiplier", 2), ("two_handed", False), ("hold_milliturns_s", 0)):
            beat = deepcopy(original)
            beat["task"]["crank_player"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(CampaignError):
                check_crank_player(beat)
        for beat in (original, chapter(2)["beats"][0]):
            del beat["task"]["crank_player"]
            with self.assertRaises(CampaignError):
                check_crank_player(beat)
        for invalid in ([], True, None):
            beat = chapter(5)["beats"][5]
            beat["ext"]["flame_gauge"] = invalid
            with self.subTest(gauge=invalid), self.assertRaises(BuildError):
                player_work(beat, fail)


if __name__ == "__main__":
    unittest.main()
