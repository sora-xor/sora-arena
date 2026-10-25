"""Regression tests for the v2.1 pilot timbers (sora_timber_v2, dojo_timber_pilot).

Run: python3 -m unittest scripts/art/test_sora_timber_v2.py

Numpy only; about 90 seconds. It builds the six real pilot members, dense and
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
  inside its own namespace (never run 1's).
* **v2.1's fixes for what run 1's renders showed,** each against a reproduction:
  - the check staircase (v1's position-only ladder);
  - ring beading near knots (no row refinement);
  - the wobble seam at atan2's wrap;
  - knot-edge frame blending (UVKnot).

  Y-junctions are explicit, bounded and continuous, and can't hide a staircase.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
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
        # The indoor 25-45 um, times v2.2's per-year relief (YEAR_RELIEF 0.55-1.45).
        self.assertGreater(wall["grain_recess_p95_m"], 25e-6)
        self.assertLessEqual(wall["grain_recess_p95_m"], 45e-6 * V.YEAR_RELIEF[1])
        self.assertTrue(25e-6 * V.YEAR_RELIEF[0] <= wall["grain_recess_p50_m"] <= 45e-6)
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
        self.assertEqual(PILOT.NAMESPACE, "NyaagyuDojoTimbersV22Pilot")
        for bad in (PILOT.KIT / "FBX" / "x.fbx", PILOT.ROOT / "Local/ArtCache/NyaagyuDojoTimbers/Unique/x.fbx",
                    PILOT.ROOT / "Content/x.fbx", PILOT.RUN1 / "Dense" / "x.fbx", PILOT.RUN1 / "manifest.json",
                    PILOT.RUN_V21 / "Renders" / "x.png", PILOT.RUN_V21 / "manifest.json"):
            with self.subTest(path=str(bad)), self.assertRaises(ValueError):
                PILOT.guard(bad)


class JunctionGate(unittest.TestCase):
    """check_joins on explicit edge graphs: a parent at u = 0 for z 0-2 mm and
    its fork 0.5 mm away for z 2-4 mm, five rows of two samples (parent, fork)
    with both checks' own samples in every row. After Codex's counterexample
    on 3a4aba6 (Saved/Qualification/2026-10-25/timber-v21-review-3a4aba6)."""

    def graph(self, edges, fork_u=0.0005):
        from types import SimpleNamespace

        def check(u, z0, z1, parent=-1):
            return V.CheckV2(face=0, u0=u, drift=0.0, z0=z0, z1=z1, width=0.0004, depth=0.0008, meander=[], noise=[],
                             bridges=[], ext0=0.002, ext1=0.002, steep=1.3, steep_left=True, ratio=4.0, lip=[],
                             splinters=[], parent=parent)
        cs = [check(0.0, 0.0, 0.002), check(fork_u, 0.002, 0.004, 0)]
        z = np.arange(5) * 0.001
        entries = [[(i, 0, c.u0, -0.005, 0.005, -0.01, 0.01, True) for i, c in enumerate(cs)] for _ in z]
        S = SimpleNamespace(x=np.zeros(10), z=np.repeat(z, 2), u=np.tile([0.0, fork_u], 5), seg=np.zeros(10, int),
                            row_start=np.arange(5) * 2, row_count=np.full(5, 2), checks_at=entries)
        m = SimpleNamespace(finish=("planed", "hidden", "hidden", "hidden"), hw_floor=0.00016)
        B = {"samples": S, "tris": np.array([[a, b, 10] for a, b in edges])}
        keep = V.checks_v2
        try:
            V.checks_v2 = lambda _m: cs
            return V.check_joins(B, m)
        finally:
            V.checks_v2 = keep

    def own_edges(self):
        return [(2 * k + i, 2 * (k + 1) + i) for k in range(4) for i in range(2)]

    def test_every_groove_joined_needs_no_exemption(self):
        joins, junctions = self.graph(self.own_edges())
        self.assertTrue(all(j["steps"] == 0 and j["joined"] == j["row_pairs"] for j in joins))
        self.assertEqual(junctions[0]["exempt_pairs"], [])
        self.assertTrue(junctions[0]["continuous"])

    def test_only_the_forward_endpoint_is_broken(self):
        e = self.own_edges()
        e.remove((0, 2))
        e.append((0, 3))                     # the parent's first V-bottom reaches the fork's...
        joins, junctions = self.graph(e)     # ...but nothing from row 0 reaches the parent's second
        self.assertFalse(junctions[0]["continuous"], junctions)
        p = junctions[0]["exempt_pairs"][0]
        self.assertEqual((p["forward_to_other_branch"], p["backward_from_other_branch"]), (True, False))

    def test_only_the_backward_endpoint_is_broken(self):
        e = self.own_edges()
        e.remove((0, 2))
        e.append((1, 2))                     # the fork's row-0 V-bottom reaches the parent's second, nothing leaves the first
        joins, junctions = self.graph(e)
        self.assertFalse(junctions[0]["continuous"], junctions)
        p = junctions[0]["exempt_pairs"][0]
        self.assertEqual((p["forward_to_other_branch"], p["backward_from_other_branch"]), (False, True))

    def test_a_crossing_that_supplies_both_endpoints_is_a_junction(self):
        e = self.own_edges()
        e.remove((0, 2))
        e += [(0, 3), (1, 2)]
        joins, junctions = self.graph(e)
        self.assertTrue(junctions[0]["continuous"], junctions)
        self.assertEqual(len(junctions[0]["exempt_pairs"]), 1)
        self.assertEqual(sum(j["steps"] for j in joins), 0)

    def test_far_from_its_fork_a_break_is_a_step(self):
        e = self.own_edges()
        e.remove((0, 2))
        e += [(0, 3), (1, 2)]
        joins, junctions = self.graph(e, fork_u=0.004)   # 4 mm apart: the V's never overlap, no window
        self.assertEqual(junctions[0]["window_rows"], 0)
        self.assertEqual(joins[0]["steps"], 1)


class V21(unittest.TestCase):
    """What run 1's renders showed, each reproduced and shown fixed."""

    @classmethod
    def setUpClass(cls):
        cls.members = {kind: m for m, fam, kind, rec in PILOT.pilot_members()}
        cls.wall = cls.members["wall"]
        cls.B = V.build(cls.wall, ARRAYS)

    def test_the_check_staircase_is_caught_and_gone(self):
        joins, records = V.check_joins(self.B, self.wall)
        self.assertTrue(all(j["steps"] == 0 and j["joined"] == j["row_pairs"] for j in joins), joins)
        keep = V.ladder
        try:
            V.ladder = T.ladder                       # run 1: rows paired by position alone
            B = V.build(self.wall, ARRAYS)
        finally:
            V.ladder = keep
        r = V.check_mesh(B, self.wall)
        self.assertTrue(any("step" in f for f in r["failures"]), r["failures"])
        steps = sum(j["steps"] for j in r["metrics"]["check_joins"])
        self.assertGreater(steps, 300)                # most row pairs, as measured on run 1

    def test_y_junctions_are_explicit_bounded_and_continuous(self):
        cs = V.checks_v2(self.wall)
        for m in (self.wall, self.members["open"], self.members["Nageshi"], self.members["Nuki"]):
            records = V.junctions(m)
            forks = [i for i, c in enumerate(V.checks_v2(m)) if c.parent >= 0 and m.finish[c.face] != "hidden"]
            self.assertEqual([r[0] for r in records], forks)        # one per fork, nothing by proximity
            for j, par, f, z in records:
                c, pc = V.checks_v2(m)[j], V.checks_v2(m)[par]
                self.assertEqual(c.parent, par)
                self.assertTrue(abs(z - pc.z0) < 1e-9 or abs(z - pc.z1) < 1e-9)   # at the parent's end
            r = V.check_mesh(V.build(m, ARRAYS), m)["metrics"]
            for rec in r["junctions"]:
                self.assertTrue(rec["continuous"], rec)
                self.assertLessEqual(rec["window_length_m"], V.JUNCTION_MAX_LENGTH)
                self.assertEqual(rec["exempt_pairs"], [])          # every V-bottom joins, forks included
        self.assertTrue(any(c.parent >= 0 for c in cs))

    def test_a_staircase_cannot_hide_in_a_junction(self):
        keep = V.ladder
        try:
            V.ladder = T.ladder
            B = V.build(self.wall, ARRAYS)
        finally:
            V.ladder = keep
        _joins, records = V.check_joins(B, self.wall)
        exempt = [p for rec in records for p in rec["exempt_pairs"]]
        self.assertTrue(exempt)
        for p in exempt:
            self.assertEqual(p["continuous"], p["forward_to_other_branch"] and p["backward_from_other_branch"])
        self.assertTrue(any(not rec["continuous"] for rec in records))

    def test_ring_beading_near_knots_is_caught_and_gone(self):
        ring = V.ring_error(self.B, self.wall)
        self.assertLessEqual(ring["close"]["p99"], V.RING_ERROR_CLOSE[0])
        self.assertLessEqual(ring["close"]["max"], V.RING_ERROR_CLOSE[1])
        keep = V._refine_rows, V._refine_across
        try:
            V._refine_rows = lambda m, z, **k: z
            V._refine_across = lambda m, f, z, u, *a, **k: u
            B = V.build(self.wall, ARRAYS)
        finally:
            V._refine_rows, V._refine_across = keep
        r = V.check_mesh(B, self.wall)
        self.assertTrue(any("rings sit" in f and "close" in f for f in r["failures"]), r["failures"])

    def test_the_wobble_has_no_seam(self):
        z = np.linspace(0.5, 6.5, 200)
        for m in (self.wall, self.members["open"]):
            eps = 1e-6
            v1 = np.abs(m.log.wobble(np.full(z.size, (math.pi - eps) * 0.08), z)
                        - m.log.wobble(np.full(z.size, (-math.pi + eps) * 0.08), z)).max()
            v21 = np.abs(V.wobble(m, np.full(z.size, math.pi - eps), z) - V.wobble(m, np.full(z.size, -math.pi + eps), z)).max()
            self.assertGreater(v1 / m.log.ring_width, 1.0)       # v1's form jumps rings at the wrap
            self.assertLess(v21 / m.log.ring_width, 1e-3)
        r = V.check_mesh(V.build(self.members["open"], ARRAYS), self.members["open"])
        self.assertTrue(r["ok"], r["failures"])                   # the seam was the open column's face 2

    def test_uvknot_carries_the_knots_and_uvlogq_stays_continuous(self):
        B, m = self.B, self.wall
        _mask, kd, kr, *_ = T._knots(m, np.stack([B["samples"].x, B["samples"].y, B["samples"].z], 1))
        inside = kd < kr
        self.assertTrue(inside.any())
        np.testing.assert_array_equal(B["uv4"][:, 1] < 0, inside)
        fb = V.build(V.fallback(m), ARRAYS)
        self.assertTrue(np.all(fb["uv4"] == np.array([0.0, 1.0])))
        # No frame swap. Across every edge touching a knot, UVLogQ moves only as
        # far as the surface plus the swirl's bend (under 1 cm). Swapping in the
        # knot's own radius, as v2 did, would jump by its gap to the log radius
        # (over 2 cm here).
        t = B["tris"]
        tt = t[inside[t].any(1)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            dq = np.linalg.norm(B["uv2"][tt[:, a]] - B["uv2"][tt[:, b]], axis=1)
            dp = np.linalg.norm(B["verts"][tt[:, a]] - B["verts"][tt[:, b]], axis=1)
            self.assertLess(float(np.max(dq - dp)), 0.01)
        swap = np.abs(B["uv4"][inside, 0] - np.linalg.norm(B["uv2"][inside], axis=1))
        self.assertGreater(float(swap.min()), 0.02)
        # The material reference: the latewood on the stored channels is the ridges' phase, and the
        # knot select uses the knot's own rings.
        g = B["grain_sel"]
        uv0 = np.stack([B["s"], B["z"]], 1)
        ph = V.material_phase(uv0[g], B["uv2"][g], B["uv3"][g], B["uv4"][g], m.log.ring_width, ARRAYS)
        self.assertEqual(float(np.max(np.abs(ph - B["grain_phase"][g]))), 0.0)
        k = inside
        ph_k = V.material_phase(uv0[k], B["uv2"][k], B["uv3"][k], B["uv4"][k], m.log.ring_width, ARRAYS)
        ref = V.ring_phase(np.stack([B["uv4"][k, 0], np.zeros(int(k.sum()))], 1), float(B["uv3"][0, 1]), uv0[k],
                           m.log.ring_width, ARRAYS)
        np.testing.assert_array_equal(ph_k, ref)

    def test_uv_contract_names_every_channel_in_export_order(self):
        names = [c["blender_layer"] for c in V.UV_CONTRACT["channels"]]
        self.assertEqual(names, ["UV0", "UV1", "UVLogQ", "UVLogZ", "UVKnot"])
        self.assertEqual([c["index"] for c in V.UV_CONTRACT["channels"]], list(range(5)))
        src = (PILOT.HERE / "sora_timber_lib.py").read_text()
        self.assertIn('for layer, arr in (("UV0", uv0), ("UV1", uv1), ("UVLogQ", uv2), ("UVLogZ", uv3)):', src)
        v2 = Path(V.__file__).read_text()
        self.assertIn('uv_layers.new(name="UVKnot")', v2[v2.index("def to_blender("):v2.index("def canonical_digest(")])
        self.assertEqual(V.UV_CONTRACT["geometry"], "sora-timber-geometry-v2.2")
        self.assertTrue(V.UV_CONTRACT["unreal_content_path"].endswith("DojoTimberPilotV22"))
        self.assertEqual(V.UV_CONTRACT["ring"]["year_waves"], [list(w) for w in V.YEAR_WAVES])
        self.assertIn("finish", V.UV_CONTRACT)


class WoodCharacter(unittest.TestCase):
    """v2.2: what root's review of the v2.1 originals named, each measured on the real members."""

    @classmethod
    def setUpClass(cls):
        cls.members = {kind: m for m, fam, kind, rec in PILOT.pilot_members()}
        cls.nuki = cls.members["Nuki"]
        cls.Bn = V.build(cls.nuki, ARRAYS)
        cls.nag = cls.members["Nageshi"]
        cls.Bg = V.build(cls.nag, ARRAYS)

    def test_naguri_facets_cover_the_face_and_run_along_the_grain(self):
        # "a repeated grid of rounded hammered dimples, not directional cut facets"
        m, B = self.nuki, self.Bn
        S = B["samples"]
        f = 3
        sel = (S.seg == 2 * f) & (S.detail > 0) & (V._from_arris(m, f, S.u, 0.008) >= 1.0)
        cut = V.adze(m, S.u[sel], S.z[sel], f) - (T._adze_undulation(m, f, S.u[sel], S.z[sel]) - 0.001)
        self.assertLess(float(np.mean(cut > -1e-4)), 0.02)                 # no flat land between facets
        u = np.arange(-0.05, 0.05, 0.0005)
        z = np.arange(1.0, 1.5, 0.0005)
        Ug, Zg = np.meshgrid(u, z)
        H = (V.adze(m, Ug.ravel(), Zg.ravel(), f) - (T._adze_undulation(m, f, Ug.ravel(), Zg.ravel()) - 0.001)).reshape(Ug.shape)
        H = H - H.mean()

        def corr_len(axis):
            n, var = H.shape[axis], float(np.mean(H * H))
            for lag in range(1, n // 2):
                a, b = np.take(H, range(0, n - lag), axis=axis), np.take(H, range(lag, n), axis=axis)
                if float(np.mean(a * b)) / var < 0.5:
                    return lag * 0.0005
            return n * 0.0005
        # Directional cuts: the field holds together along the grain far longer than across it.
        self.assertGreater(corr_len(0), 1.5 * corr_len(1))               # v2.2: 18 mm along, 8 mm across
        self.assertTrue(0.0012 <= V.NAGURI["depth_m"][0] < V.NAGURI["depth_m"][1] <= 0.003)

    def test_dents_are_crushed_grooves_without_a_rim(self):
        # "Column_DentClose still reads as a soft blister"
        wall = self.members["wall"]
        B = V.build(wall, ARRAYS)
        S = B["samples"]
        floors = []
        for df, du, dz, a_u, a_z, dep, _rim in V.dent_sites(wall):
            near = (S.seg == 2 * df) & (np.abs(S.u - du) < 1.6 * a_u) & (np.abs(S.z - dz) < 1.6 * a_z)
            if not near.any():
                continue
            rho = np.sqrt(((S.u[near] - du) / a_u) ** 2 + ((S.z[near] - dz) / a_z) ** 2)
            self.assertLessEqual(float(B["dent_disp"][near].max()), 0.0)   # nothing raised
            inner = rho < 0.5
            if inner.any():
                floors.append(float(np.mean(-B["dent_disp"][near][inner] > 0.75 * dep)))
        self.assertTrue(floors)
        self.assertGreater(min(floors), 0.9)                                 # flat crushed floors

    def test_rings_vary_year_to_year_in_width_and_relief(self):
        # "Nageshi_GrainClose looks like fine uniform corrugation"
        B = self.Bg
        g = B["grain_sel"]
        ph, rec = B["grain_phase"][g], -B["grain_disp"][g]
        frac, ring = np.mod(ph, 1.0), np.floor(ph)
        by = {}
        for r_, h_ in zip(ring[frac < 0.4], rec[frac < 0.4]):
            by.setdefault(r_, []).append(h_)
        means = np.array([np.mean(v) for v in by.values() if len(v) > 20])
        self.assertGreater(float(means.std() / means.mean()), 0.2)           # relief per ring
        S = B["samples"]
        z0 = S.z[S.row_start][len(S.row_start) // 2]
        row = g & (np.abs(B["z"] - z0) < 1e-9)
        o = np.argsort(S.u[row])
        u, p = S.u[row][o], B["grain_phase"][row][o]
        d = np.diff(p)
        self.assertEqual(int(np.sum(np.sign(d[:-1]) != np.sign(d[1:]))), 0)  # monotonic
        crossings = [u[i] + (k - p[i]) / (p[i + 1] - p[i]) * (u[i + 1] - u[i]) for i in range(len(p) - 1)
                     for k in range(int(math.ceil(min(p[i], p[i + 1]))), int(math.floor(max(p[i], p[i + 1]))) + 1)
                     if min(p[i], p[i + 1]) <= k < max(p[i], p[i + 1])]
        w = np.diff(np.sort(crossings))
        self.assertTrue(0.12 <= float(w.std() / w.mean()) <= 0.4, w.std() / w.mean())   # v2.1: 0.04
        self.assertLess(2 * math.pi * sum(a / period for period, a, _c in V.YEAR_WAVES), 0.8)

    def test_the_finish_is_a_satin_film_and_cavities_are_bare(self):
        # "Koshi_WornTopClose has repetitive parallel glossy ridges"
        fin = V.FINISH_V22["column_fukiurushi"]
        self.assertLessEqual(fin["coat"], 0.6)
        self.assertGreaterEqual(fin["coat_rough"], 0.3)
        self.assertTrue(V.FINISH_V22["cavity_uncoats"])
        koshi = self.members["Koshi"]
        B = V.build(koshi, ARRAYS)
        g = B["grain_sel"] & (B["samples"].seg == 4)                        # the hand-worn top
        rec = -B["grain_disp"][g]
        z = B["z"][g]
        bins = np.digitize(z, np.linspace(z.min(), z.max(), 9))
        p95 = np.array([np.percentile(rec[bins == b], 95) for b in np.unique(bins) if np.sum(bins == b) > 50])
        self.assertGreater(float(p95.std() / p95.mean()), 0.05)             # wear varies along the rail


if __name__ == "__main__":
    unittest.main()
