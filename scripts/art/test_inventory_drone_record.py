"""CPU checks of the Inventory drone kit's build record against its envelope contract
(docs/art-direction/INVENTORY_DRONE_ENVELOPE.md).

Run: python3 -m unittest scripts/art/test_inventory_drone_record.py

- The body stays within its 36.5 cm design bound, inside the 38 cm movement sphere.
- The sphere fits the ledger hall: its top 12 cm under the 600 ceiling at the 550 flight plane, its bottom 62 cm over
  the 450 shelf tops. The hall's numbers are root's SoraLedgerRules.h (65f4aaea).
- Three convex hit hulls enclose the body, span about 27 cm against the sphere's 76, and fill under a quarter of it.
- The Eye socket faces forward on the front rim; NetMuzzle points down and forward below the body.
- LOD triangle counts fall, and the eye and ledger line are the emissive glows.
"""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone/build_record.json"
HALL = {"ceiling_cm": 600, "flight_cm": 550, "shelf_top_cm": 450}      # SoraLedgerRules.h, root 65f4aaea


class DroneRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = json.loads(RECORD.read_text(encoding="utf-8"))
        cls.asset = cls.r["assets"]["SM_Drone_Inventory"]

    def test_envelope(self):
        env = self.r["envelope"]
        self.assertLessEqual(env["max_from_centre_m"], 0.365)
        self.assertLess(env["max_from_centre_m"], env["collision_radius_m"])
        self.assertEqual([row["lod"] for row in env["lods"]], [0, 1, 2])
        self.assertTrue(all(row["max_from_centre_m"] <= 0.365 for row in env["lods"]))

    def test_sphere_fits_the_ledger_hall(self):
        c = self.r["collision_proposal"]
        self.assertEqual(c["shape"], "sphere: capsule radius = half-height")
        radius = c["radius_cm"]
        self.assertEqual({k: c["ledger_hall"][k] for k in HALL}, HALL)
        self.assertAlmostEqual(HALL["flight_cm"] + radius, c["ledger_hall"]["top_cm"])
        self.assertGreaterEqual(HALL["ceiling_cm"] - (HALL["flight_cm"] + radius), 10.0)
        self.assertGreaterEqual(HALL["flight_cm"] - radius - HALL["shelf_top_cm"], 50.0)
        self.assertEqual(c["actor_scale"], 1.0)

    def test_hit_hulls(self):
        h = self.r["hit_hulls"]
        self.assertEqual(sorted(h["hulls"]), [f"UCX_SM_Drone_Inventory_{i:02d}" for i in range(3)])
        self.assertTrue(all(v["deepest_outside_m"] <= 0.0 for v in h["hulls"].values()))
        lo, hi = h["vertical_span_m"]
        self.assertLess(hi - lo, 0.30)                                    # against the sphere's 0.76
        self.assertLess(h["share_of_movement_sphere"], 0.25)
        self.assertAlmostEqual(h["movement_sphere_volume_m3"], 4.0 / 3.0 * math.pi * 0.38 ** 3, places=4)

    def test_sockets(self):
        s = self.asset["sockets"]
        self.assertEqual(set(s), {"Eye", "NetMuzzle"})
        eye, muzzle = s["Eye"], s["NetMuzzle"]
        self.assertGreater(eye[0], 0.35)                                  # on the front rim
        self.assertAlmostEqual(eye[1], 0.0, places=6)
        self.assertLess(math.dist(eye, (0, 0, 0)), 0.365)
        self.assertLess(muzzle[2], -0.14)                                  # below the body
        self.assertGreater(muzzle[0], 0.0)                                 # and forward of its centre

    def test_lods_and_glows(self):
        tris = [lod["triangles"] for lod in self.asset["lods"]]
        self.assertTrue(all(a > b for a, b in zip(tris, tris[1:])), tris)
        glows = {g["material"] for g in self.r["emissive"]["glows"]}
        self.assertEqual(glows, {"M_Drone_EyeLens", "M_Drone_Ledger"})
        self.assertEqual(self.r["emissive"]["mask"], "Mask R")


if __name__ == "__main__":
    unittest.main()
