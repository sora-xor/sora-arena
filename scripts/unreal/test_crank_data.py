"""Cooperative rates, net rescue and collision-clear helper positions."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from build_campaign_data import BuildError, fail
from campaign_crank import cooperation
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
            coop = {"npc": npc, "rate_milliturns_s": rate, "progress_permille": credit,
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

    def test_lift_resolution_is_separate(self):
        self.assertIsNone(chapter(8)["beats"][10]["task"]["crank_coop"])


if __name__ == "__main__":
    unittest.main()
