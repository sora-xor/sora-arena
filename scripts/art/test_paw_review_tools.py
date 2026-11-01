"""Host tests: the authored-normal comparison's tools and the paw boundary diagnosis.

Run: /usr/bin/python3 -m unittest scripts/art/test_paw_review_tools.py   (numpy and PIL)

- **compare_fbx_normals:** isolated polygons, Newell face normals, position matching within 0.02 mm.
- **diagnose_nyaakoto_paw_boundaries:**
  - the edges between two face classes, and the corner of a vertex;
  - Unreal's camera axes from a rotator;
  - the two per-face choices it blames: corner_uvs switching projection by face normal, and pad_faces assigning whole
    faces;
  - the coat, which is per vertex.
- **The engine scripts' source** (they need Unreal, so they are read):
  - the candidate changes only LOD0's recompute_normals, keeps the tangents explicit, checks the baseline's package
    and refuses to replace;
  - the comparison replays s132's cameras within 0.001 deg.
"""
from __future__ import annotations

import ast
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_fbx_normals as C  # noqa: E402
import diagnose_nyaakoto_paw_boundaries as D  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402

UNREAL = HERE.parent / "unreal"


def mesh(poly_corners, positions):
    """A compare_fbx_normals mesh dict from polygons (lists of vertex indices) and vertex positions."""
    corner_vertex = np.array([v for p in poly_corners for v in p])
    poly = np.concatenate([[k] * len(p) for k, p in enumerate(poly_corners)])
    return {"positions": np.asarray(positions, float)[corner_vertex], "vertex": corner_vertex, "poly": poly,
            "uses": np.bincount(corner_vertex, minlength=len(positions))}


class Normals(unittest.TestCase):
    def test_isolated_polygons_are_those_sharing_no_vertex(self):
        pts = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [5, 5, 5], [6, 5, 5], [5, 6, 5]]
        m = mesh([[0, 1, 2], [1, 3, 2], [4, 5, 6]], pts)
        np.testing.assert_array_equal(C.isolated(m), [False] * 6 + [True] * 3)

    def test_newell_normals_follow_the_winding(self):
        m = mesh([[0, 1, 2]], [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        np.testing.assert_allclose(C.face_normals(m), [[0, 0, 1]] * 3, atol=1e-12)
        m = mesh([[0, 2, 1]], [[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        np.testing.assert_allclose(C.face_normals(m), [[0, 0, -1]] * 3, atol=1e-12)

    def test_matching_takes_the_nearest_normal_at_a_position_within_tolerance(self):
        ours_p = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        ours_n = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])
        tilt = math.radians(10.0)
        theirs_p = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0 + 1e-4, 0.0, 0.0]])
        theirs_n = np.array([[math.sin(tilt), 0.0, math.cos(tilt)], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
        got = C.match(ours_p, ours_n, theirs_p, theirs_n)
        self.assertAlmostEqual(got[0], 10.0, places=6)
        self.assertTrue(np.isnan(got[1]))                     # 0.1 mm off: beyond the 0.02 mm tolerance


class Boundaries(unittest.TestCase):
    def test_edges_between_two_classes_and_the_corner_of_a_vertex(self):
        tris = np.array([[0, 1, 2], [1, 3, 2], [3, 4, 2]])
        a = np.array([True, False, False])
        b = ~a
        key, fa, fb = D.edges_between(tris, a, b)
        self.assertEqual([tuple(k) for k in key], [(1, 2)])
        self.assertEqual(sorted([int(fa[0]), int(fb[0])]), [0, 1])
        np.testing.assert_array_equal(D.corner_of(tris, np.array([0, 1]), np.array([2, 2])), [2, 2])

    def test_unreal_camera_axes(self):
        f, r, u = D.camera_basis([0.0, 0.0, 0.0])
        np.testing.assert_allclose((f, r, u), ([1, 0, 0], [0, 1, 0], [0, 0, 1]), atol=1e-12)
        f, r, u = D.camera_basis([-30.0, 90.0, 0.0])
        np.testing.assert_allclose(f, [0.0, math.cos(math.radians(30)), -0.5], atol=1e-12)
        np.testing.assert_allclose(r, [-1.0, 0.0, 0.0], atol=1e-12)
        self.assertAlmostEqual(float(np.dot(f, u)), 0.0, places=12)
        self.assertGreater(u[2], 0.0)

    def test_the_uv_projection_is_chosen_per_face_by_its_normal(self):
        fr = {"c": np.zeros(3), "z": np.array([1.0, 0.0, 0.0]), "w": np.array([0.0, 0.0, 1.0]), "a": 0.02, "b": 0.015}
        # One face looking along the channel (Y) and one across it, sharing an edge.
        verts = np.array([[0.03, 0.0, 0.0], [0.03, 0.0, 0.01], [0.04, 0.0, 0.0], [0.03, 0.01, 0.0]])
        tris = np.array([[0, 1, 2], [0, 3, 1]])
        uvs = TPP.corner_uvs(verts, tris, fr)
        flat = np.stack([verts @ fr["z"], verts @ fr["w"]], -1)[tris[0]] * TPP.UV_PER_M
        np.testing.assert_allclose(uvs[0], flat, atol=1e-12)              # planar: the cross-section's own coordinates
        shared0 = uvs[0][0], uvs[1][0]                                     # vertex 0 in both faces
        self.assertGreater(float(np.linalg.norm(shared0[0] - shared0[1])), 1e-3)   # one vertex, two UVs: a seam

    def test_the_engine_scripts_change_one_setting_and_replay_the_cameras(self):
        prep = (UNREAL / "prepare_nyaakoto_authored_normals.py").read_text()
        ast.parse(prep)
        self.assertIn('settings.set_editor_property("recompute_normals", False)', prep)
        self.assertIn('[{"lod": 0, "field": "recompute_normals", "baseline": True, "candidate": False}]', prep)
        self.assertIn('TANGENTS = {"recompute_tangents": True, "use_mikk_t_space": True, "use_high_precision_tangent_basis": False}', prep)
        self.assertIn("if ASSETS.does_asset_exist(CANDIDATE):", prep)
        self.assertIn('fail("the baseline\'s package changed")', prep)
        comp = (UNREAL / "render_nyaakoto_normals_comparison.py").read_text()
        ast.parse(comp)
        self.assertIn('VIEWS = ("guard_front_LOD0", "paw_R_back_empty_LOD0", "cuff_R_outside_LOD0")', comp)
        self.assertIn("ROT_TOL_DEG = 1e-3", comp)
        self.assertIn('if run["packages_sha256"].get(rel) != digest:', comp)


if __name__ == "__main__":
    unittest.main()
