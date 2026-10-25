"""Regression tests for the v2 pilot timbers (sora_timber_v2, dojo_timber_pilot).

Run: python3 -m unittest scripts/art/test_sora_timber_v2.py

Numpy only; about 30 seconds. It builds the six real pilot members, dense and
fallback, and proves:

* **The six members** are closed, consistently wound, unfolded, crossing-free
  and needle-free, with their checks, dents, raised grain and adze relief.
* **The materials' ring model** is reproduced:
  - shared textures byte-identical to the committed PNGs;
  - the v2 wander monotonic, where v1's reverses hundreds of times;
  - ridges at exactly the phase rebuilt from the stored UVs.
* **Every reproduced defect is caught:** an open hole, a flipped triangle, a
  fold, misaligned UVs, and an adze that ignores the arris.
* **The frozen v1 kit's inputs** are unchanged, and the pilot can only write
  inside its own namespace.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dojo_timber_pilot as PILOT  # noqa: E402
import sora_timber_lib as T  # noqa: E402
import sora_timber_v2 as V  # noqa: E402

ARRAYS = V.shared_arrays()


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RingModel(unittest.TestCase):
    def test_shared_arrays_are_the_committed_textures(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, key in (("T_TimberRingNoise.png", "RingNoise"), ("T_TimberRingRandom.png", "RingRandom"),
                              ("T_TimberFibre.png", "Fibre")):
                self.assertEqual(sha(T.write_png(Path(tmp) / name, ARRAYS[key])), sha(PILOT.KIT / "Shared" / name), name)

    def test_v2_wander_is_monotonic_where_v1_reverses(self):
        m = PILOT.pilot_members()[0][0]
        half = m.width / 2
        u = np.arange(-half + 0.003, half - 0.003, 0.00002)
        x, y = T._face_xy(3, u, half, half)
        px, py = m.log.pith_at(np.full(u.size, 1.3))
        r = np.hypot(x - px, y - py)
        seed01 = (m.log.seed % 997) / 997.0

        def reversals(phase):
            d = np.diff(phase)
            return int(np.sum(np.sign(d[:-1]) != np.sign(d[1:])))
        v2 = V._phase_of_r(r, seed01, m.log.ring_width, ARRAYS)
        nu = r / (6.0 * m.log.ring_width) + seed01 * 37.0
        var = V.sample_linear(ARRAYS["RingNoise"].astype(float) / 65535.0, nu, np.full(u.size, (seed01 * 7.31) % 1.0))
        v1 = r / m.log.ring_width + (var - 0.5) * 3.0
        self.assertLessEqual(reversals(v2), 1)       # only at the face centre, nearest the pith
        self.assertGreater(reversals(v1), 100)       # v1's chaotic striping

    def test_ridge_is_the_masters_latewood_ridge(self):
        f = np.array([0.0, 0.3, 0.51, 0.66, 0.81, 0.83, 0.91, 0.999])
        expect = T.smoothstep(0.51, 0.81, f) * (1 - T.smoothstep(0.82, 1.0, f))
        np.testing.assert_allclose(V.ridge(f), expect)
        self.assertEqual(V.ridge(np.array([0.2]))[0], 0.0)


class Pilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.members = PILOT.pilot_members()
        cls.built = {}
        for m, fam, kind, rec in cls.members:
            cls.built[kind] = (m, V.build(m, ARRAYS))
            mf = V.fallback(m)
            cls.built[kind + ":fallback"] = (mf, V.build(mf, ARRAYS))

    def test_all_twelve_meshes_pass_their_checks(self):
        for key, (m, B) in self.built.items():
            with self.subTest(mesh=key):
                r = V.check_mesh(B, m)
                self.assertTrue(r["ok"], r["failures"])
                self.assertEqual(r["metrics"]["edges_not_shared_by_two"], 0)
                self.assertEqual(r["metrics"]["folded_triangles"], 0)
                self.assertLess(r["metrics"]["max_angle_outside_checks_deg"], 179.0)

    def test_features_carry_their_specified_relief(self):
        wall = V.check_mesh(self.built["wall"][1], self.built["wall"][0])["metrics"]
        self.assertTrue(all(c["count_min"] == 17 for c in wall["checks"]))
        self.assertGreaterEqual(min(wall["dent_depth_reached"]), 0.6)
        self.assertGreater(wall["grain_recess_p95_m"], 25e-6)
        self.assertLessEqual(wall["grain_recess_p95_m"], 45e-6)
        self.assertEqual(wall["grain_phase_from_stored_uvs_max_error"], 0.0)
        koshi = V.check_mesh(self.built["Koshi"][1], self.built["Koshi"][0])["metrics"]
        self.assertGreater(koshi["grain_recess_p95_m"], 1e-4)               # the hand-worn top
        nuki = V.check_mesh(self.built["Nuki"][1], self.built["Nuki"][0])["metrics"]
        self.assertGreater(nuki["adze_depth_p50_m"], 0.0015)                # visible scallops
        vis = V.relief_visibility(self.built["wall"][1], self.built["wall"][0])
        self.assertGreater(vis["grain"]["shading_p95_at_30deg_pct"], 5.0)   # visible in raking light
        self.assertGreater(V.relief_visibility(self.built["Nuki"][1], self.built["Nuki"][0])["adze"]["shading_p95_at_30deg_pct"], 10.0)

    def test_budget(self):
        dense = sum(self.built[k][1]["tris"].shape[0] for k in ("wall", "open", "Nageshi", "Cornice", "Koshi", "Nuki"))
        self.assertLess(dense, 2_600_000)
        self.assertLess(self.built["open"][1]["tris"].shape[0], 1_300_000)

    # -- Every reproduced defect is caught --------------------------------

    def mutated(self, kind):
        m, B = self.built[kind]
        return m, {**B, "tris": B["tris"].copy(), "verts": B["verts"].copy(), "uv2": B["uv2"].copy()}

    def test_open_hole_fails(self):
        m, B = self.mutated("Cornice:fallback")
        B["tris"] = B["tris"][1:]
        self.assertTrue(any("not closed" in f for f in V.check_mesh(B, m)["failures"]))

    def test_flipped_triangle_fails(self):
        m, B = self.mutated("Cornice:fallback")
        B["tris"][10] = B["tris"][10][[0, 2, 1]]
        self.assertTrue(any("winding" in f for f in V.check_mesh(B, m)["failures"]))

    def test_fold_and_crossing_fail(self):
        # A vertex pushed straight in only makes a pit, which is legitimate
        # relief. Moving one past its neighbours is what folds or crosses.
        m, B = self.mutated("Cornice:fallback")
        S = B["samples"]
        k = int(np.nonzero((S.seg == 6) & (S.z > 0.5))[0][5])
        B["verts"][k, 2] += 3 * m.row_sp                # past the next rows along the member: triangles flip
        r = V.check_mesh(B, m)
        self.assertTrue(any("fold" in f for f in r["failures"]), r["failures"])
        m, B = self.mutated("Cornice:fallback")
        row = S.row_start[20]
        idx = row + np.nonzero(S.seg[row:row + S.row_count[20]] == 6)[0]
        B["verts"][idx[3], 0] = B["verts"][idx[5], 0] + 0.001   # past two neighbours along the row
        r = V.check_mesh(B, m)
        self.assertTrue(any("cross their neighbours" in f for f in r["failures"]), r["failures"])

    def test_misaligned_grain_uvs_fail(self):
        m, B = self.mutated("wall")
        B["uv2"][B["grain_sel"]] += 0.0002            # the stored log frame no longer the ridges'
        self.assertTrue(any("not aligned" in f for f in V.check_mesh(B, m)["failures"]))

    def test_adze_ignoring_the_arris_folds(self):
        m = self.built["Nuki"][0]
        keep = V._from_arris
        try:
            V._from_arris = lambda m, f, u, width: np.ones(np.asarray(u).shape)
            r = V.check_mesh(V.build(m, ARRAYS), m)
        finally:
            V._from_arris = keep
        self.assertGreater(r["metrics"]["folded_triangles"], 0)


class Baseline(unittest.TestCase):
    def test_frozen_v1_kit_inputs_are_unchanged(self):
        for manifest in (PILOT.KIT / "manifest.json", PILOT.KIT / "Rails/manifest.json"):
            data = json.loads(manifest.read_text())
            self.assertEqual(sha(PILOT.ROOT / data["generator"]), data["generator_sha256"], data["generator"])
            for rel, digest in data["inputs"].items():
                self.assertEqual(sha(PILOT.ROOT / rel), digest, rel)

    def test_pilot_writes_only_in_its_namespace(self):
        self.assertEqual(PILOT.guard(PILOT.OUT / "Dense" / "x.fbx"), PILOT.OUT / "Dense" / "x.fbx")
        for bad in (PILOT.KIT / "FBX" / "x.fbx", PILOT.ROOT / "Local/ArtCache/NyaagyuDojoTimbers/Unique/x.fbx",
                    PILOT.ROOT / "Content/x.fbx"):
            with self.subTest(path=str(bad)), self.assertRaises(ValueError):
                PILOT.guard(bad)


if __name__ == "__main__":
    unittest.main()
