"""Tests of fbx_unreal_sockets: UE 5.8 Interchange's socket rule, calibrated on root's actual import of fc0858a9.

Run: python3 -m unittest scripts/art/test_fbx_unreal_sockets.py

- **Calibration.** fc0858a9's LOD0 nodes, as its bytes hold them, give root's actual UE 5.8 readback: scale 100,
  both +X reversed, positions right. The file test checks the same on the archived bytes, where they are kept.
- **The convention.** Unreal's import axes with the unit baked leave a socket unturned and at scale 1, and a node
  scale still reaches the socket.
- **The kit.** The committed LOD0, through the rule, meets root's socket and geometry gates
  (scripts/unreal/inventory_drone.py, 0eb8c5e) and the record.

The file tests need Blender's io_scene_fbx parser, and are skipped without it.
"""
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_unreal_sockets as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone"
ORIGINAL = ROOT / "Saved/InventoryDrone/Archive/socket_fix_original_fc0858a9/SM_Drone_Inventory.fbx"
# fc0858a9's LOD0 nodes, as read from its bytes on 2026-10-26: Blender's ('Z', '-Y') axes, and the axis turn and
# the x100 unit on the mesh node.
FC0858A9 = {"axes": {"UpAxis": (2, 1), "FrontAxis": (1, 1), "CoordAxis": (0, -1)}, "unit": 1.0, "nodes": {
    "SM_Drone_Inventory": {"type": "Mesh", "parent": None, "T": (0, 0, 0), "R": (0.0, -0.0, 179.999991348578),
                           "S": (100.0, 100.0, 100.0), "vertices": None},
    "SOCKET_Eye": {"type": "Null", "parent": "SM_Drone_Inventory", "T": (0.362199991941452, 0.0, 0.0),
                   "R": (0.0, 0.0, 0.0), "S": (1.0, 1.0, 1.0), "vertices": None},
    "SOCKET_NetMuzzle": {"type": "Null", "parent": "SM_Drone_Inventory",
                         "T": (0.07676954567432404, 0.0, -0.15176954865455627), "R": (0.0, 45.00000125223908, 0.0),
                         "S": (0.9999998807907104, 0.9999999403953552, 0.9999998807907104), "vertices": None}}}
# Root's actual UE 5.8 readback of that file: Saved/Qualification/2026-10-26/drone-0eb8c5e-import-attempt1,
# editor.log line 1920.
ROOT_READBACK = {
    "Eye": {"forward": [-0.9999999999999886, -1.5099579909783707e-07, 0.0],
            "position": [36.2199991941448, 5.469067717207298e-06, 0.0],
            "scale": [100.00000000000003, 100.00000000000003, 99.99999999999999]},
    "NetMuzzle": {"forward": [-0.7071067657322291, -1.0677015113922622e-07, 0.7071067966408575],
                  "position": [7.6769545674323165, 1.1591878886070896e-06, -15.176954865455624],
                  "scale": [99.99998807907107, 99.99999403953555, 99.99998807907104]}}
# Root's socket gate (scripts/unreal/inventory_drone.py socket_readback, 0eb8c5e).
ROOT_FORWARD = {"Eye": (1.0, 0.0, 0.0), "NetMuzzle": (math.sqrt(0.5), 0.0, -math.sqrt(0.5))}


def parser_available():
    try:
        F.parser()
        return True
    except ImportError:
        return False


class Calibration(unittest.TestCase):
    def check_root_readback(self, scene):
        got = F.interchange(scene)["sockets"]
        self.assertEqual(set(got), set(ROOT_READBACK))
        for name, want in ROOT_READBACK.items():
            self.assertLess(math.dist(got[name]["position_cm"], want["position"]), 1e-6, name)
            self.assertLess(math.dist(got[name]["scale"], want["scale"]), 1e-6, name)
            self.assertLess(math.dist(got[name]["x"], want["forward"]), 1e-9, name)

    def test_fc0858a9_nodes_give_root_readback(self):
        self.check_root_readback(FC0858A9)

    @unittest.skipUnless(parser_available() and ORIGINAL.is_file(), "needs Blender's parser and the archived original")
    def test_fc0858a9_bytes_give_root_readback(self):
        self.check_root_readback(F.read_fbx(ORIGINAL))


class Convention(unittest.TestCase):
    def scene(self, axes, mesh_s=(1.0, 1.0, 1.0), socket_t=(36.22, 0.0, 0.0), socket_r=(0.0, 45.0, 0.0)):
        return {"axes": axes, "unit": 1.0, "nodes": {
            "M": {"type": "Mesh", "parent": None, "T": (0, 0, 0), "R": (0, 0, 0), "S": mesh_s,
                  "vertices": np.array([[36.22, 1.0, 0.0]])},
            "SOCKET_S": {"type": "Null", "parent": "M", "T": socket_t, "R": socket_r, "S": (1, 1, 1),
                         "vertices": None}}}

    def test_import_axes_leave_a_socket_on_its_own_axes(self):
        r = F.interchange(self.scene(F.UNREAL_IMPORT_AXES))
        s = r["sockets"]["S"]
        np.testing.assert_allclose(r["conversion"], np.eye(3))
        np.testing.assert_allclose(s["scale"], (1, 1, 1))
        np.testing.assert_allclose(s["x"], ROOT_FORWARD["NetMuzzle"], atol=1e-12)
        np.testing.assert_allclose(s["position_cm"], (36.22, 0, 0), atol=1e-12)
        np.testing.assert_allclose(r["vertices"]["M"], [[36.22, -1.0, 0.0]], atol=1e-12)

    def test_other_axes_move_a_socket_with_the_scene_but_not_its_axes(self):
        r = F.interchange(self.scene({"UpAxis": (2, 1), "FrontAxis": (1, 1), "CoordAxis": (0, -1)}))
        np.testing.assert_allclose(r["vertices"]["M"], [[-36.22, 1.0, 0.0]], atol=1e-12)    # the scene, turned
        np.testing.assert_allclose(r["sockets"]["S"]["position_cm"], (-36.22, 0, 0), atol=1e-12)
        # The scene's turn would carry the socket's forward to (-0.7071, 0, -0.7071). C R C^-1 gives Ry(-45) instead.
        np.testing.assert_allclose(r["sockets"]["S"]["x"], (math.sqrt(0.5), 0, math.sqrt(0.5)), atol=1e-12)

    def test_a_parent_scale_reaches_the_socket(self):
        s = F.interchange(self.scene(F.UNREAL_IMPORT_AXES, mesh_s=(100.0,) * 3, socket_t=(0.3622, 0, 0)))["sockets"]["S"]
        np.testing.assert_allclose(s["scale"], (100, 100, 100))
        np.testing.assert_allclose(s["position_cm"], (36.22, 0, 0), atol=1e-12)

    def test_metre_files_are_refused(self):
        with self.assertRaises(ValueError):
            F.interchange({**self.scene(F.UNREAL_IMPORT_AXES), "unit": 100.0})


@unittest.skipUnless(parser_available(), "needs Blender's io_scene_fbx parser")
class Kit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((KIT / "build_record.json").read_text(encoding="utf-8"))
        cls.asset = cls.record["assets"]["SM_Drone_Inventory"]
        cls.scene = F.read_fbx(ROOT / cls.asset["lods"][0]["file"])
        cls.result = F.interchange(cls.scene)

    def test_lod0_declares_unreal_axes_in_centimetres(self):
        self.assertEqual(self.scene["axes"], F.UNREAL_IMPORT_AXES)
        self.assertEqual(self.scene["unit"], 1.0)
        for name, node in self.scene["nodes"].items():
            np.testing.assert_allclose(node["S"], (1, 1, 1), atol=1e-6, err_msg=name)

    def test_sockets_meet_root_gate(self):
        sockets = self.result["sockets"]
        self.assertEqual(set(sockets), {"Eye", "NetMuzzle"})
        for name, s in sockets.items():
            source = self.asset["sockets"][name]
            want = (100 * source[0], -100 * source[1], 100 * source[2])
            self.assertLess(math.dist(s["position_cm"], want), 0.02, name)
            self.assertLess(math.dist(s["scale"], (1, 1, 1)), 1e-4, name)
            self.assertLess(math.dist(s["x"], ROOT_FORWARD[name]), 0.009, name)
            self.assertLess(math.dist(s["x"], ROOT_FORWARD[name]), 1e-5, name)       # and far inside it

    def test_lods_meet_root_geometry_gate(self):
        for lod, entry in enumerate(self.asset["lods"]):
            result = F.interchange(F.read_fbx(ROOT / entry["file"]))
            pts = next(v for n, v in result["vertices"].items() if not n.startswith("UCX_"))
            expected = self.record["envelope"]["lods"][lod]
            low = [100 * expected["bounds_min_m"][0], -100 * expected["bounds_max_m"][1], 100 * expected["bounds_min_m"][2]]
            high = [100 * expected["bounds_max_m"][0], -100 * expected["bounds_min_m"][1], 100 * expected["bounds_max_m"][2]]
            self.assertLessEqual(float(np.linalg.norm(pts, axis=1).max()), 36.5, lod)
            np.testing.assert_allclose(pts.min(0), low, atol=0.02, err_msg=str(lod))
            np.testing.assert_allclose(pts.max(0), high, atol=0.02, err_msg=str(lod))


if __name__ == "__main__":
    unittest.main()
