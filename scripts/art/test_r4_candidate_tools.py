"""Host tests: the r4 repaired-paw candidate's tools (s136-s143).

Run: /usr/bin/python3 -m unittest scripts/art/test_r4_candidate_tools.py   (numpy, scipy and PIL)

- **prepare_nyaakoto_r4_paws:**
  - each cut face's parent face;
  - a root located in the cut piece that holds it.
- **check_nyaakoto_r4_fbx:**
  - which candidate-vs-control differences the paws may make;
  - element trees compared with their UIDs by the object they name (Blender seeds them per process);
  - the sRGB byte of a linear coat;
  - an affine fit.
- **fbx_unreal_sockets.model_globals:** global matrices by UID, where a mesh and its parent share a name (Unreal's
  export of s142).
- **check_nyaakoto_r4_comparison.pair:** changed pixels counted inside and outside the paw mask.
- **The Blender and Unreal scripts' source** (they need Blender or Unreal, so they are read):
  - **the assembly:**
    - float64 atan2 angles;
    - both paws' vertices collected before any is added;
    - a numeric sort key;
    - the kept corners' custom-normal codes restored, then a BMesh rebuild;
    - the build's SK export settings;
  - **the import:** a new asset; LOD0 settings from s133's candidate; the preserved packages hashed;
  - **the capture:** nine LOD0 views; three variants in order; s132's cameras within 0.001 deg.
"""
from __future__ import annotations

import ast
import math
import sys
import unittest
from collections import namedtuple
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_nyaakoto_r4_comparison as CC  # noqa: E402
import check_nyaakoto_r4_fbx as K  # noqa: E402
import fbx_unreal_sockets as FUS  # noqa: E402
import nyaakoto_tp_paw_surface as S  # noqa: E402
import prepare_nyaakoto_r4_paws as P  # noqa: E402

UNREAL = HERE.parent / "unreal"
E = namedtuple("E", ("id", "props", "props_type", "elems"))


def prop(name, *values):
    return E(b"P", [name.encode(), name.encode(), b"", b"A"] + list(values), b"SSSS" + b"D" * len(values), [])


def model(uid, name, kind, t=(0.0, 0.0, 0.0)):
    return E(b"Model", [uid, name + b"\x00\x01Model", kind], b"LSS", [E(b"Properties70", [], b"", [prop("Lcl Translation", *t)])])


def fbx(uids, array_value=1.0, geometry_on=2):
    """A small FBX element tree: a document, two models and a mesh geometry (on the model at that place), with the
    given UIDs."""
    doc = E(b"Document", [uids[0], b"Scene", b"Scene"], b"LSS", [E(b"RootNode", [0], b"L", [])])
    geo = E(b"Geometry", [uids[3], b"Mesh\x00\x01Geometry", b"Mesh"], b"LSS",
            [E(b"Vertices", [[0.0, 1.0, array_value]], b"d", [])])
    objects = E(b"Objects", [], b"", [model(uids[1], b"M", b"Null"), model(uids[2], b"M", b"Mesh"), geo])
    links = E(b"Connections", [], b"", [E(b"C", [b"OO", uids[2], uids[1]], b"SLL", []),
                                        E(b"C", [b"OO", uids[1], 0], b"SLL", []),
                                        E(b"C", [b"OO", uids[3], uids[geometry_on]], b"SLL", [])])
    return E(b"", [], b"", [E(b"FBXHeaderExtension", [], b"", []), E(b"Documents", [], b"", [doc]), objects, links])


class Preparation(unittest.TestCase):
    def test_cut_faces_know_their_parents_and_roots_find_their_piece(self):
        verts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
        tris = np.array([[0, 1, 2], [0, 2, 3]])
        f = verts[:, 0] - 0.3                                    # crosses both faces
        v2, t2, inside, parents, ts, f2 = S.cut_by_field(verts, tris, f, snap=0.0)
        parent = P.face_parents(tris, f2)
        self.assertEqual(len(parent), len(t2))
        for c, p in zip(t2, parent):
            for x in c:
                if x < len(verts):
                    self.assertIn(x, tris[p])
                else:
                    self.assertTrue(set(parents[x - len(verts)]) <= set(tris[p]))
        roots = np.array([[0.2, 0.05, 0.0], [0.9, 0.5, 0.0], [0.1, 0.8, 0.0]])
        face = np.array([0, 0, 1])
        cf, cb, mn = P.locate(roots, face, verts, tris, v2, t2, parent)
        self.assertTrue((mn >= -1e-12).all())
        np.testing.assert_allclose((v2[t2[cf]] * cb[:, :, None]).sum(1), roots, atol=1e-12)
        np.testing.assert_array_equal(parent[cf], face)


class FbxCheck(unittest.TestCase):
    def test_which_differences_the_paws_may_make(self):
        self.assertTrue(K.allowed("Objects/Geometry[Angular_brow_-1.001|Mesh]/LayerElementUV/UV"))
        self.assertTrue(K.allowed("Objects/Geometry[PawEmpty_R|Shape]/Vertices"))
        self.assertTrue(K.allowed("Objects/Deformer[PawEmpty_L|BlendShapeChannel]/FullWeights"))
        self.assertTrue(K.allowed("Objects/Deformer[hand_R|Cluster]/Weights"))
        self.assertFalse(K.allowed("Objects/Deformer[spine|Cluster]/Weights"))
        self.assertFalse(K.allowed("Objects/Model[root|LimbNode]"))
        self.assertFalse(K.allowed("Objects/Geometry[Angular_brow_-1.001|Mesh]/Vertices#children"))
        self.assertFalse(K.allowed("Takes/Take"))

    def test_uids_compare_by_the_object_they_name(self):
        a, b = fbx((7, 11, 12, 13)), fbx((907, 811, 812, 813))
        self.assertEqual(K.tree_diff(a, b), [])
        c = fbx((907, 811, 812, 813), array_value=2.0)
        self.assertEqual(K.tree_diff(a, c), ["Objects/Geometry[Mesh|Mesh]/Vertices"])
        d = fbx((907, 811, 812, 813), geometry_on=1)             # the geometry on the other model, by UID
        self.assertEqual(K.tree_diff(a, d), ["Connections/C"])

    def test_srgb_bytes_and_the_affine_fit(self):
        np.testing.assert_array_equal(K.srgb_byte(np.array([0.0, 1.0, 0.5, 0.0031308])), [0, 255, 188, 10])
        rng = np.random.default_rng(3)
        src = rng.normal(size=(50, 3))
        ang = 0.4
        R = np.array([[math.cos(ang), -math.sin(ang), 0], [math.sin(ang), math.cos(ang), 0], [0, 0, 1]])
        dst = src @ (R * 1.17647).T + [0.1, -0.2, 0.3]
        A, t, resid = K.fit_affine(src, dst)
        self.assertLess(resid, 1e-12)
        np.testing.assert_allclose(A, R * 1.17647, atol=1e-12)

    def test_model_globals_follow_uids_where_names_repeat(self):
        g = FUS.model_globals(fbx((7, 11, 12, 13)))
        root = fbx((7, 11, 12, 13))
        objects = FUS._child(root, b"Objects")
        objects.elems[0].elems[0].elems[0].props[4:] = [1.0, 2.0, 3.0]   # the Null
        objects.elems[1].elems[0].elems[0].props[4:] = [0.0, 0.0, 5.0]   # the mesh, also named M
        g = FUS.model_globals(root)
        np.testing.assert_allclose(g[12][:3, 3], [1.0, 2.0, 8.0])
        np.testing.assert_allclose(g[11][:3, 3], [1.0, 2.0, 3.0])


class ComparisonCheck(unittest.TestCase):
    def test_changed_pixels_inside_and_outside_the_mask(self):
        a = np.zeros((4, 4, 3), np.int16)
        b = a.copy()
        b[0, 0] = 50                                             # inside the mask
        b[3, 3] = 9                                              # outside, just over the level
        b[2, 2] = 8                                              # outside, at the level: unchanged
        mask = np.zeros((4, 4), bool)
        mask[:2, :2] = True
        row, m = CC.pair(b, a, mask)
        self.assertEqual((row["changed_inside_paws_px"], row["changed_outside_paws_px"]), (1, 1))
        self.assertEqual(int(m.max()), 50)


class EngineSources(unittest.TestCase):
    def test_the_assembly(self):
        src = (HERE / "assemble_nyaakoto_r4_paws.py").read_text()
        ast.parse(src)
        self.assertIn("np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), (a * b).sum(1))", src)
        self.assertIn("a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)", src)
        self.assertLess(src.index("old_verts = {side:"), src.index("bm.verts.new("))
        self.assertIn("return nf + f[cut] if f[cut] > 0 else nf + right_cut - f[cut]", src)
        encode = src.index("me.normals_split_custom_set(want_n.tolist())")
        restore = src.index("    write_codes(me, codes)", encode)
        self.assertLess(restore, src.index("rt.from_mesh(me)", restore))
        self.assertIn("codes[kept_loops_after] = codes_before[kept_loops_before]", src[encode:restore])
        rig = (HERE / "rig_nyaakoto_runtime.py").read_text()
        call = rig[rig.index("bpy.ops.export_scene.fbx("):]
        call = call[:call.index("prioritize_active_color=True)") + 30]
        for piece in ('axis_forward="-Y"', 'axis_up="Z"', "apply_unit_scale=True", "add_leaf_bones=False",
                      "use_armature_deform_only=True", "bake_anim=True", "bake_anim_use_nla_strips=False",
                      "bake_anim_use_all_actions=False", "bake_anim_simplify_factor=0", 'path_mode="STRIP"',
                      "prioritize_active_color=True", 'object_types={"MESH", "ARMATURE"}', "use_selection=True"):
            self.assertIn(piece, call)
            self.assertIn(piece.replace("=", "=", 1), src)

    def test_the_import(self):
        src = (UNREAL / "import_nyaakoto_r4_candidate.py").read_text()
        ast.parse(src)
        self.assertIn('CANDIDATE_DIR = "/Game/Generated/Candidates/R4Paws"', src)
        self.assertIn("if ASSETS.does_asset_exist(CANDIDATE):", src)
        self.assertIn('want_row = s133["candidate"]["lod_build_settings"][0]', src)
        self.assertIn('fail("a preserved package changed")', src)
        self.assertIn("options.skeleton = skeleton", src)

    def test_the_capture(self):
        src = (UNREAL / "render_nyaakoto_r4_comparison.py").read_text()
        tree = ast.parse(src)
        views = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                     and getattr(n.targets[0], "id", None) == "VIEWS")
        self.assertEqual(len(views), 9)
        self.assertTrue(all(v.endswith("_LOD0") for v in views))
        self.assertIn('VARIANTS = (("baseline", R.MESH_PATH), ("authored_normals", S133), ("r4_paws", R4))', src)
        self.assertIn("ROT_TOL_DEG = 1e-3", src)
        self.assertIn('R.fail("the r4 candidate on disk is not the one its import read back")', src)


if __name__ == "__main__":
    unittest.main()
