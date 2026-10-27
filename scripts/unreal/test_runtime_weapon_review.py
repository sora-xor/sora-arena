"""Source and adversarial readback tests for the weapon ArtReview importer."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_weapon_review as R
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "art"))
import verify_weapon_review_geometry as V

ROOT = Path(__file__).resolve().parents[2]


class WeaponReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan, cls.records = R.source_plan(ROOT)

    def test_exact_inventory_omits_held_assets_and_separate_bow_rebuild(self):
        self.assertEqual(len(self.records), 16)
        self.assertEqual(len(self.plan["assets"]), 20)
        self.assertEqual(sum(len(a["lods"]) for a in self.plan["assets"].values()), 60)
        self.assertEqual(sum(len(a["sockets"]) for r in self.records.values() for a in r["assets"].values()), 64)
        for number in (3, 11, 13, 16, 18):
            self.assertNotIn(f"SM_Weapon_{number:02}", self.plan["assets"])

    def test_an_envelope_cannot_redefine_the_gate(self):
        read = Path.read_bytes
        bad = copy.deepcopy(self.plan)
        bad["assets"]["SM_Weapon_02"]["lods"][0]["min_cm"][0] -= 100
        def tampered(path):
            return json.dumps(bad).encode() if path == ROOT / R.ENVELOPE else read(path)
        with patch.object(Path, "read_bytes", tampered), self.assertRaisesRegex(RuntimeError, "unreviewed geometry envelope"):
            R.source_plan(ROOT)

    def test_changed_fbx_and_texture_are_rejected(self):
        read = Path.read_bytes
        record = self.records["W00_Katana"]
        for entry in (record["assets"]["SM_Weapon_00"]["lods"][0], record["textures"]["Normal"]):
            target = ROOT / entry["file"]
            def tampered(path):
                return b"changed bytes" if path == target else read(path)
            with self.subTest(file=target.name), patch.object(Path, "read_bytes", tampered):
                with self.assertRaisesRegex(RuntimeError, "changed source"):
                    R.source_plan(ROOT)

    def test_hamon_does_not_glow_and_weapon_colors_keep_their_authored_values(self):
        expected = {"W01_ArcCarbine": ([1, .86, .7], 4), "W05_CoilMatchlock": ([1, .32, .05], 6),
                    "W12_MonofilamentNaginata": ([1, .55, .22], 22),
                    "W14_PlasmaMatchlock": ([.12, .85, 1], 8), "W17_HealingLance": ([1, .62, .3], 5)}
        for kit, record in self.records.items():
            material = R.material_plan(record)
            self.assertEqual((material["emissive_color"], material["emissive_strength"]), expected.get(kit, ([0, 0, 0], 0)))
            self.assertEqual(material["masked"], kit == "W07_GrenadeLauncher")
            self.assertEqual(material["two_sided"], material["masked"])
            self.assertFalse(material["normal_flip_green"])

    def test_ambiguous_or_nonfinite_emission_is_refused(self):
        for kind in ("multiple", "color", "strength", "channel"):
            record = copy.deepcopy(self.records["W01_ArcCarbine"])
            if kind == "multiple":
                record["emissive"]["glows"] *= 2
            elif kind == "color":
                record["emissive"]["glows"][0]["linear_rgb"][0] = float("nan")
            elif kind == "strength":
                record["emissive"]["glows"][0]["strength"] = float("inf")
            else:
                record["emissive"]["mask"] = "Mask B"
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                R.material_plan(record)

    def geometry(self, name="SM_Weapon_02"):
        expected = self.plan["assets"][name]
        lods = []
        for row in expected["lods"]:
            lo, hi = row["min_cm"], row["max_cm"]
            points = [list(lo), list(hi), [hi[0], lo[1], hi[2]]]
            section = {"positions": points, "indices": [0, 1, 2]*row["triangles"],
                       "normals": [[0, 0, 1]]*3, "tangents": [[1, 0, 0]]*3,
                       "uvs": [list(row["uv_min"]), list(row["uv_max"]), list(row["uv_min"])]}
            lods.append({"sections": [section], "triangles": row["triangles"], "uv_channels": row["uv_channels"]})
        return expected, lods, list(expected["screen_sizes"])

    def test_clean_bounds_counts_frames_uvs_and_screens_pass(self):
        expected, lods, screens = self.geometry()
        self.assertEqual(len(R.geometry_readback(expected, lods, screens)), 3)

    def test_recorded_atlas_defects_require_exact_bounds_and_corner_count(self):
        expected, lods, screens = self.geometry()
        expected = copy.deepcopy(expected)
        expected["lods"][0]["uv_max"][1] = 1.01
        expected["lods"][0]["atlas_uv_outside_corners"] = 1
        section = lods[0]["sections"][0]
        for field in ("positions", "normals", "tangents"):
            section[field].append(list(section[field][0]))
        section["uvs"].append([section["uvs"][1][0], 1.01])
        section["indices"][0] = 3
        self.assertEqual(R.geometry_readback(expected, lods, screens)[0]["atlas_uv_outside_corners"], 1)
        section["indices"][1] = 3
        with self.assertRaisesRegex(RuntimeError, "changed atlas overshoot"):
            R.geometry_readback(expected, lods, screens)

    def test_scale_pivot_axis_count_and_uv_damage_fail(self):
        for defect in ("scale", "pivot", "axes", "count", "uv_count", "uv_outside", "indices", "section"):
            expected, lods, screens = self.geometry()
            section = lods[1]["sections"][0]
            if defect in {"scale", "pivot", "axes"}:
                for point in section["positions"]:
                    if defect == "scale":
                        point[:] = [v*100 for v in point]
                    elif defect == "pivot":
                        point[0] += .1
                    else:
                        point[0] = -point[0]
            elif defect == "count":
                section["indices"] = section["indices"][:-3]
            elif defect == "uv_count":
                lods[1]["uv_channels"] = 1
            elif defect == "uv_outside":
                section["uvs"][0][0] = 1.1
            elif defect == "indices":
                section["indices"][0] = 3
            else:
                lods[1]["sections"] *= 2
            with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                R.geometry_readback(expected, lods, screens)

    def test_nonfinite_and_malformed_render_vectors_fail(self):
        for field in ("positions", "normals", "tangents", "uvs"):
            for bad in (float("nan"), float("inf"), float("-inf"), True, "0"):
                expected, lods, screens = self.geometry()
                lods[0]["sections"][0][field][0][0] = bad
                with self.subTest(field=field, bad=bad), self.assertRaises(RuntimeError):
                    R.geometry_readback(expected, lods, screens)
        expected, lods, screens = self.geometry()
        lods[0]["sections"][0]["normals"] = []
        with self.assertRaises(RuntimeError):
            R.geometry_readback(expected, lods, screens)

    def test_missing_lod_and_bad_screen_thresholds_fail(self):
        expected, lods, screens = self.geometry()
        with self.assertRaises(RuntimeError):
            R.geometry_readback(expected, lods[:2], screens)
        for value in (float("nan"), .5):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                R.geometry_readback(expected, lods, [value, *screens[1:]])

    def test_real_selected_socket_readbacks_are_regated_against_installed_records(self):
        receipt = json.loads((ROOT / "docs/art-direction/data/runtime_weapon_ue_socket_probe.json").read_text())["readback"]
        for name, expected in self.plan["assets"].items():
            asset = self.records[expected["kit"]]["assets"][name]
            sockets = receipt["imports"][name]["corrected"]["sockets"]
            R.socket_readback(name, asset, sockets)
        asset = self.records["W15_MicroMortar"]["assets"]["SM_Weapon_15"]
        sockets = copy.deepcopy(receipt["imports"]["SM_Weapon_15"]["corrected"]["sockets"])
        sockets["Grip_R"]["up"] = [0, 0, 1]  # W15's intentional turned frame must survive.
        with self.assertRaises(RuntimeError):
            R.socket_readback("SM_Weapon_15", asset, sockets)

    def test_corner_comparison_keeps_uv_seams_and_accepts_reordered_split_vertices(self):
        source = {"positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                  "indices": [0, 1, 2, 3, 4, 5], "normals": [[0, 0, 1]]*6,
                  "tangents": [[1, 0, 0]]*6, "uvs": [[0, 0], [.4, 0], [0, .4], [.6, .6], [1, 1], [.6, 1]]}
        actual = copy.deepcopy(source)
        actual["indices"] = [4, 5, 3, 1, 2, 0]
        measured, failures = V.compare(source, actual)
        self.assertEqual(failures, [])
        self.assertEqual(measured["corners"], 6)
        for field, index, value in (("uvs", 3, [.4, 0]), ("normals", 4, [0, 0, -1]),
                                    ("tangents", 2, [0, 0, 0])):
            damaged = copy.deepcopy(actual)
            damaged[field][index] = value
            with self.subTest(field=field):
                self.assertTrue(V.compare(source, damaged)[1])
        for defect in ("position", "winding"):
            damaged = copy.deepcopy(actual)
            if defect == "position":
                damaged["positions"][3][0] -= .01
            else:
                damaged["indices"][:3] = [4, 3, 5]
            with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                V.compare(source, damaged)

    def test_fine_adjacent_triangles_are_not_paired_across_uv_seams(self):
        points = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        source = {"positions": points + [[x+.0005, y, z] for x, y, z in points],
                  "indices": [0, 1, 2, 3, 4, 5], "normals": [[0, 0, 1]]*6,
                  "tangents": [[1, 0, 0]]*6,
                  "uvs": [[0, 0], [.4, 0], [0, .4], [.6, .6], [1, .6], [.6, 1]]}
        actual = copy.deepcopy(source)
        actual["indices"] = [3, 4, 5, 0, 1, 2]
        measured, failures = V.compare(source, actual)
        self.assertEqual(failures, [])
        self.assertEqual(measured["position_cm"], 0)


if __name__ == "__main__":
    unittest.main()
