"""Host tests: b09_workshop_craft, the lantern workshop's craft assets and their integration proposal.

Run: /usr/bin/python3 -m unittest scripts/art/test_b09_workshop_craft.py   (numpy)

- **Root's inputs as pinned:** the stations, steps, timing, floors and reach (check_b09_root_inputs.py checks them
  against root's tree).
- **The lantern:**
  - the hoops follow the profile;
  - the paper lies outside the hoops, and the four gores cover the round with their overlaps;
  - the rims sit at the openings, and the hang point is above them.
- **A hoop's strip** keeps its length through every flex stage, straight at 0 and closed at 1.
- **The gauge:**
  - its fixed green band is the release window (+30 to +90 deg of a -90 to +90 deg sweep), and the strip is fully bent
    at 800 ms;
  - the needle points where gauge_angle says;
  - merged meshes keep each part's material slot, so the band, ticks and face stay distinct.
- **First-person view** (the world's 94 deg, 16:9 and 21:9): every station's required elements are in frame,
  unoccluded and readable at the work stand, and at no less than 90% of the working side's positions.
- **The lanterns** sit at chest height (130) at the paste bench and oil rack; the station point stays at 110.
- **Every station:**
  - no proposed proxy blocks a station ray, and each proxy stays under the ray's start;
  - the work stand is eligible with a clear ray and a capsule gap of at least 10 cm;
  - nothing but the work stands between the eye and the work;
  - the parts stay over their proxies and clear of the room's walls.
- **Weapon 7's rest:** a proper rotation; the culm lies above the bench, inside it and clear of its cradles; a wrapped
  shell seats with about 1 mm all round.
- **The hanging output:** 40 slots inside the room and clear of the hero's head, the ceiling and each other.
- **Meshes:** valid indices, no degenerate faces, attributes in [0, 1].
- **The committed spec** is what spec() writes.
"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b09_workshop_craft as B  # noqa: E402

SPEC = HERE.parents[1] / "docs/art-direction/data/b09_workshop_craft_spec.json"


def arc_length(points):
    p = np.asarray(points)
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def centreline(k, flex):
    """The strip's centreline: the mean of each cross-section's four corners."""
    m = B.hoop(k, flex)
    n = (len(m.verts) - 2) // 4 if flex < 1.0 else None
    v = m.verts[: (n * 4 if n else (len(m.verts) // 4) * 4)]
    return v.reshape(-1, 4, 3).mean(1)


class RootInputs(unittest.TestCase):
    def test_the_recipe_and_stations_as_pinned(self):
        self.assertEqual([s for s, _ in B.STATIONS], ["st_b09_rib_form", "st_b09_paste_bench", "st_b09_oil_rack", "st_b09_shell_bench"])
        self.assertEqual([xy for _, xy in B.STATIONS], [(2100, -620), (2100, -950), (2100, -1300), (2790, -2050)])
        self.assertEqual(B.STEP_STATIONS, (0, 1, 1, 2, 3, 3))
        self.assertEqual([n for _, n in B.STEPS], [6, 4, 1, 1, 3, 1])
        self.assertEqual((B.BEND_MS, B.BEND_TOL_MS, B.PASTE_MS, B.REACH_CM), (800, 160, 1500, 260.0))
        self.assertEqual((B.CAPSULE_R, B.CAPSULE_HALF, B.RAY_FROM_Z, B.RAY_TO_Z), (34.0, 88.0, 88.0, 110.0))

    def test_floor_at_follows_root(self):
        for (x, y), want in {(2100, -620): 45, (2100, -2050): 0, (1745, -950): 22.5, (1900, -1535): 22.5,
                             (2790, -2050): 0, (1700, -900): 0}.items():
            self.assertEqual(B.floor_at(x, y), want, (x, y))


class Lantern(unittest.TestCase):
    def test_hoops_follow_the_profile_between_the_rims(self):
        z, r = B.hoop_z(), B.hoop_r()
        self.assertEqual(len(z), 6)
        self.assertTrue((np.diff(z) > 0).all())
        np.testing.assert_allclose(r, B.profile_r(z) + B.HOOP_T / 2)
        self.assertTrue((r < B.LANTERN_R + B.HOOP_T).all() and (r > B.LANTERN_RIM_R).all())
        np.testing.assert_allclose(r, r[::-1])                            # symmetric about the waist
        self.assertAlmostEqual(float(B.profile_r(B.LANTERN_H / 2)), B.LANTERN_RIM_R)

    def test_the_paper_covers_the_round_outside_the_hoops(self):
        cover = np.zeros(360)
        for k in range(1, 5):
            g = B.gore(k)
            rad = np.hypot(g.verts[:, 0], g.verts[:, 1])
            self.assertTrue((rad >= B.profile_r(g.verts[:, 2]) + B.HOOP_T + B.PAPER_GAP - 1e-9).all())
            a0 = 180.0 + 90.0 * (k - 1) - B.GORE_OVERLAP_DEG
            for a in np.arange(a0, a0 + 90.0 + 2 * B.GORE_OVERLAP_DEG, 0.5):
                cover[int(a) % 360] += 1
            for key in ("height_frac", "azimuth_frac"):
                self.assertTrue((g.attrs[key] >= -1e-12).all() and (g.attrs[key] <= 1 + 1e-12).all())
        self.assertTrue((cover >= 2).all())                               # every degree covered
        self.assertGreater(int((cover >= 4).sum()), 4 * 2 * int(B.GORE_OVERLAP_DEG) - 4)   # doubled at the seams

    def test_rims_and_hang_point(self):
        lo, hi = B.rim("Top").bounds()
        np.testing.assert_allclose([lo[2], hi[2]], [-B.RIM_H / 2, B.RIM_H / 2])
        finished = B.merge("x", B.lantern("finished"))
        self.assertAlmostEqual(float(finished.verts[:, 2].max()), B.hang_point()[2] + 1.2 + 0.1, delta=0.2)
        self.assertNotIn("SM_B09_Form", {m.name for m in B.lantern("finished")})
        self.assertIn("SM_B09_Form", {m.name for m in B.lantern("rimmed")})


class Strip(unittest.TestCase):
    def test_a_strip_keeps_its_length_from_straight_to_closed(self):
        for k in (1, 3, 6):
            want = B.hoop_r()[k - 1] * math.radians(360.0 + B.HOOP_LAP_DEG)
            for f in B.FLEX_STAGES[:-1]:
                c = centreline(k, f)
                self.assertAlmostEqual(arc_length(c), want, delta=want * 0.01, msg=(k, f))
            straight = centreline(k, 0.0)
            self.assertLess(float(np.ptp(straight[:, 0])), 1e-6)          # all along Y, tangent at -X
            self.assertAlmostEqual(float(straight[:, 0].mean()), -B.hoop_r()[k - 1], places=6)

    def test_the_gauge_and_flex_follow_the_bend_window(self):
        band = [B.gauge_angle(B.BEND_MS - B.BEND_TOL_MS), B.gauge_angle(B.BEND_MS + B.BEND_TOL_MS)]
        self.assertEqual(band, [30.0, 90.0])
        self.assertEqual(B.gauge_angle(0), -90.0)
        for ms in (0, 400, 800, 960):
            n = B.needle_at(ms)
            d = n.verts - np.array(B.GAUGE["pivot"])
            tip = d[np.argmax(np.linalg.norm(d, axis=1))]
            self.assertAlmostEqual(math.degrees(math.atan2(tip[1], tip[2])), B.gauge_angle(ms), delta=1.0)
            self.assertLess(tip[0], 0.0)                                  # in front of the face, toward the hero
        g = B.gauge_mesh(75.0)
        self.assertEqual(sorted(set(g.slots())), ["M_B09_GaugeBand", "M_B09_GaugeFace", "M_B09_GaugeMarks", "M_B09_TimberBench"])
        band_tris = g.tris[g.slots() == "M_B09_GaugeBand"]
        c = g.verts[band_tris].mean(1) - np.array(B.GAUGE["pivot"])
        ang = np.degrees(np.arctan2(c[:, 1], c[:, 2]))
        self.assertTrue((ang >= band[0] - 1e-6).all() and (ang <= band[1] + 1e-6).all())
        self.assertEqual(B.flex_stage(B.BEND_MS), len(B.FLEX_STAGES) - 1)
        self.assertEqual(B.flex_stage(0), 0)
        self.assertEqual([B.flex_stage(ms) for ms in (0, 200, 400, 600, 800)], [0, 1, 2, 3, 4])


class Stations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clear = [B.clearance(i, step=20.0) for i in range(4)]

    def test_no_proxy_blocks_a_station_ray(self):
        for i, c in enumerate(self.clear):
            self.assertEqual(c["rays_blocked_by_proposed_proxies"], 0, B.STATIONS[i][0])
            self.assertTrue(all(top < B.RAY_FROM_Z for top in c["proxy_tops_cm"]))
            self.assertGreater(c["eligible_positions"], 100)

    def test_the_hero_works_each_station_from_its_stand(self):
        for i, c in enumerate(self.clear):
            sid = B.STATIONS[i][0]
            self.assertTrue(c["work_stand_eligible"] and c["work_stand_ray_clear"], sid)
            self.assertGreaterEqual(c["capsule_gap_cm"], 10.0, sid)
            self.assertEqual(c["sight_occluded_by"], [], sid)
            self.assertTrue(-55.0 <= c["eye_pitch_deg"] <= -10.0, sid)        # the chest-height lanterns are 16 deg down

    def test_parts_stay_over_their_proxies_and_clear_of_the_walls(self):
        walls = [(c - s / 2, c + s / 2) for k, (c, s) in enumerate(B.SOLIDS) if k not in B.FLOOR_SLABS]
        for i, (sid, (x, y)) in enumerate(B.STATIONS):
            parts, sockets, proxies, work = B.station_parts(i)
            lo_p, hi_p = proxies[0]
            o = np.array([x, y, B.floor_at(x, y)])
            for m in parts:
                lo, hi = m.bounds()
                self.assertTrue((lo[:2] >= lo_p[:2] - 1e-6).all() and (hi[:2] <= hi_p[:2] + 1e-6).all(), (sid, m.name))
                for wl, wh in walls:
                    inter = np.minimum(hi + o, wh) - np.maximum(lo + o, wl)
                    self.assertFalse((inter > 0).all(), (sid, m.name, wl, wh))

    def test_first_person_view_of_every_station(self):
        for i, (sid, _) in enumerate(B.STATIONS):
            fp = B.first_person(i, step=30.0)
            self.assertGreater(fp["approach_positions"], 30, sid)
            for aspect in B.ASPECTS:
                for name, row in fp["stand"][aspect].items():
                    if "(reported)" not in name:
                        self.assertTrue(row["ok"], (sid, aspect, name, row))
                for name, share in fp["approach"][aspect].items():
                    if "(reported)" not in name:
                        self.assertGreaterEqual(share, 0.9, (sid, aspect, name))

    def test_lanterns_at_chest_height_and_the_station_point_at_the_trace(self):
        self.assertEqual(B.LANTERN_Z, {0: 110.0, 1: 130.0, 2: 130.0})
        for i in range(4):
            _, sockets, _, _ = B.station_parts(i)
            np.testing.assert_allclose(sockets["StationPoint"][0], [0.0, 0.0, B.RAY_TO_Z])
        _, sockets, _, _ = B.station_parts(2)
        np.testing.assert_allclose(sockets["LanternHang"][0] - B.hang_point(), [0.0, 0.0, B.LANTERN_Z[2]])


class ShellBench(unittest.TestCase):
    def test_weapon_rest_is_a_proper_rotation_on_the_bench(self):
        origin, rot = B.weapon_rest()
        np.testing.assert_allclose(rot.T @ rot, np.eye(3), atol=1e-12)
        self.assertAlmostEqual(float(np.linalg.det(rot)), 1.0)
        a, b = (origin + rot @ [x, 0, 0] for x in B.WEAPON7["x_range_cm"])
        self.assertTrue(abs(a[1]) <= 60 and abs(b[1]) <= 60)              # the tube lies within the bench's width
        self.assertGreaterEqual(origin[2] - B.WEAPON7["culm_cm"] / 2, 72.0 - 1e-9)
        handle = origin + rot @ [0.0, 0.0, B.WEAPON7["z_range_cm"][0]]
        self.assertGreater(handle[0], origin[0])                          # the handle plug lies toward the back
        self.assertLessEqual(handle[0], 35.0)
        parts, sockets, proxies, work = B.station_parts(3)
        cradle = next(m for m in parts if m.name == "SM_B09_WeaponCradle")
        side = cradle.verts[np.abs(cradle.verts[:, 0] - origin[0]) < B.WEAPON7["culm_cm"] / 2]
        self.assertTrue((side[:, 2] <= 72.0 + 2.0 + 1e-9).all())          # only the cradle's base runs under the culm
        fuse = sockets["FuseInspect"][0]
        self.assertLess(fuse[0], origin[0])                               # the fuse faces the hero

    def test_shells_fit_the_bore(self):
        fit = B.bore_fit()
        self.assertTrue(0.5 <= fit["radial_clear_mm"] <= 2.0)
        self.assertLess(B.SHELL["core_cm"], B.SHELL["wrapped_cm"])
        for stage in ("core", "wrapped"):
            lo, hi = B.shell(stage).bounds()
            self.assertLessEqual(float(max(hi[0] - lo[0], hi[1] - lo[1])), B.WEAPON7["bore_cm"])


class HangingOutput(unittest.TestCase):
    def test_forty_slots_clear_of_heads_ceiling_and_each_other(self):
        c = B.hanging_clearance()
        self.assertEqual(c["slots"], B.OUTPUT_LANTERNS)
        self.assertGreaterEqual(c["min_head_clear_cm"], 60.0)
        self.assertTrue(c["inside_room"])
        self.assertGreater(c["hook_top_below_ceiling_cm"], 10.0)
        self.assertGreaterEqual(c["neighbour_gap_cm"], 15.0)
        self.assertTrue(1 <= B.PLAYER_SLOT <= 40)


class Meshes(unittest.TestCase):
    def test_every_mesh_is_valid(self):
        meshes = []
        for i in range(4):
            meshes += B.station_parts(i)[0] + [m for m, _, _ in B.state_meshes(i)]
        meshes += list(B.hanging_parts())
        for m in meshes:
            self.assertTrue(m.tris.min() >= 0 and m.tris.max() < len(m.verts), m.name)
            a = 0.5 * np.linalg.norm(np.cross(m.verts[m.tris[:, 1]] - m.verts[m.tris[:, 0]],
                                              m.verts[m.tris[:, 2]] - m.verts[m.tris[:, 0]]), axis=1)
            self.assertGreater(float(a.min()), 0.0, m.name)
            self.assertTrue(np.isfinite(m.verts).all(), m.name)


class Candidates(unittest.TestCase):
    def test_the_assets_are_unique_and_cover_every_state_mesh(self):
        rows = B.candidates()
        names = [n for n, *_ in rows]
        self.assertEqual(len(names), len(set(names)))
        for i in range(4):
            self.assertTrue({m.name for m, _, _ in B.state_meshes(i)} <= set(names))
        self.assertIn("SM_B09_PasteFrame", names)
        frame = dict((n, m) for n, m, *_ in rows)["SM_B09_PasteFrame"]
        lo, hi = frame.bounds()
        self.assertLess(abs((lo[2] + hi[2]) / 2), B.LANTERN_H)               # in the lantern frame, about its centre

    def test_the_uv_layouts(self):
        m = B.box("t", (0.0, 0.0, 0.0), (100.0, 200.0, 50.0), "M_B09_TimberBench")
        uv = B.box_uv(m)
        self.assertEqual(uv.shape, (len(m.tris), 3, 2))
        self.assertAlmostEqual(float(uv.max()), 2.0)                         # one unit per metre
        for name, mesh, socks, frame, lantern_frame in B.candidates():
            r = B.reveal_uv(mesh, lantern_frame)
            self.assertEqual(r.shape, (len(mesh.verts), 2))
            self.assertTrue(((r >= 0.0) & (r <= 1.0)).all(), name)

    def test_the_fbx_check_judges_closed_parts_by_their_facing(self):
        import check_b09_candidates_fbx as C
        m = B.box("t", (0.0, 0.0, 0.0), (1.0, 2.0, 3.0), "M_B09_TimberBench")
        bl = m.verts * [1.0, -1.0, 1.0]                                     # as Blender holds it
        (closed, vol), = C.closed_parts(bl, m.tris[:, [0, 2, 1]])
        self.assertTrue(closed)
        self.assertAlmostEqual(vol, 6.0)                                     # outward
        (closed, vol), = C.closed_parts(bl, m.tris)
        self.assertTrue(closed)
        self.assertAlmostEqual(vol, -6.0)                                    # the winding left unreversed faces in
        parts = C.closed_parts(B.gore(1).verts, B.gore(1).tris)
        self.assertFalse(any(c for c, _ in parts))                           # paper is open


class Spec(unittest.TestCase):
    def test_the_committed_spec_is_the_modules(self):
        self.assertEqual(json.loads(SPEC.read_text()), json.loads(json.dumps(B.spec(), ensure_ascii=False)))

    def test_the_review_room_is_roots_solids(self):
        room = json.loads(SPEC.read_text())["room"]                       # the committed spec is the module's (above)
        self.assertEqual(len(room["solids_cm"]), len(B.SOLIDS))
        for row, (c, s) in zip(room["solids_cm"], B.SOLIDS):
            np.testing.assert_allclose(row, np.concatenate([c, s]), atol=1e-3)
        self.assertEqual(room["ceilings"], [9, 26])                     # the workshop's ceiling and the storehouse roof
        for k in room["floor_slabs"]:
            c, s = B.SOLIDS[k]
            self.assertEqual(B.floor_at(c[0], c[1]), c[2] + s[2] / 2)   # each slab's top is the floor there


if __name__ == "__main__":
    unittest.main()
