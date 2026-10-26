"""CPU tests for the weapon socket export plan (docs/art-direction/WEAPON_SOCKET_EXPORT_PLAN.md).

Run: python3 -m unittest scripts/art/test_weapon_socket_export.py

- **The convention** is the drone's. It differs from the frozen library's LOD0 export only in the axes and the bake.
  Both are read from the builders' source, so the library is never imported or changed.
- **The screen** is tested on synthetic scenes in the library's convention and in the socket convention, and on the
  committed drone LOD0.
- **The gates** (scripts/unreal/weapon_socket_gates.py) are tested on root's two real drone imports:
  - the original fails on scale, forward and up, and its right passes;
  - the corrected file passes;
  - both agree with the model on every axis.
- **same_import** catches a moved vertex, another material slot and another collision count.
- **amend_record** changes only LOD0's hash, the asset's socket_axes and the socket_fbx block, and refuses a stale
  LOD0.
- **The staging preconditions** hold for every socketed kit LOD0 in this tree, except W14 if it is still stale here.
  Root's 3b0a662d reconciled W14 in root's tree.

The tests that read FBX files need Blender's io_scene_fbx parser, and are skipped without it.
"""
import ast
import copy
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "unreal"))
import fbx_socket_export as X  # noqa: E402
import fbx_unreal_sockets as F  # noqa: E402
import screen_fbx_sockets as S  # noqa: E402
import test_fbx_unreal_sockets as T  # noqa: E402
import weapon_socket_gates as G  # noqa: E402

ROOT = HERE.parents[1]
RUNTIME = ROOT / "Content/SourceArt/Weapons/Runtime"
DRONE = ROOT / "Content/SourceArt/Characters/Enemies/InventoryDrone"


def literal_kwargs(call):
    """A call's keyword arguments; filepath, the one argument that is not a literal, is left out."""
    return {k.arg: ast.literal_eval(k.value) for k in call.keywords if k.arg and k.arg != "filepath"}


def call_named(tree, dotted):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func) == dotted:
            yield node


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Convention(unittest.TestCase):
    def test_the_socket_convention_is_the_drones(self):
        tree = ast.parse((HERE / "create_inventory_drone.py").read_text(encoding="utf-8"))
        assign = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id == "LOD0_FBX" for t in n.targets))
        self.assertEqual(literal_kwargs(assign.value), X.SOCKET_FBX)

    def test_only_the_axes_and_the_bake_differ_from_the_frozen_library(self):
        tree = ast.parse((HERE / "create_runtime_weapon_lib.py").read_text(encoding="utf-8"))
        calls = list(call_named(tree, "bpy.ops.export_scene.fbx"))
        self.assertEqual(len(calls), 1)
        library = literal_kwargs(calls[0])
        library.pop("use_selection")
        ours = {**X.SOCKET_FBX, **X.LIBRARY_LOD0_REST}
        self.assertEqual({k: (library.get(k), ours.get(k)) for k in set(library) | set(ours) if library.get(k) != ours.get(k)},
                         {"axis_forward": ("-Y", "Y"), "bake_space_transform": (None, True)})
        self.assertEqual(library, {**X.LIBRARY_CONVENTION, **X.LIBRARY_LOD0_REST})   # the control export is the library's


def scene(axes, mesh_r=(0, 0, 0), mesh_s=(1, 1, 1), socket_t=(0.3, 0, 0)):
    return {"axes": axes, "unit": 1.0, "nodes": {
        "M": {"type": "Mesh", "parent": None, "T": (0, 0, 0), "R": mesh_r, "S": mesh_s, "vertices": None},
        "SOCKET_S": {"type": "Null", "parent": "M", "T": socket_t, "R": (0, 45, 0), "S": (1, 1, 1), "vertices": None}}}


class Screen(unittest.TestCase):
    def test_the_library_convention_fails_on_scale_and_turn(self):
        (row,) = S.screen_scene(scene(F.LIBRARY_AXES, mesh_r=(0, 0, 180), mesh_s=(100, 100, 100)), "lib.fbx")
        self.assertFalse(row["passes"])
        self.assertAlmostEqual(row["turned_deg"], 180.0, places=6)
        self.assertAlmostEqual(max(row["scale"]), 100.0, places=6)

    def test_the_socket_convention_passes(self):
        (row,) = S.screen_scene(scene(F.UNREAL_IMPORT_AXES, socket_t=(30, 0, 0)), "ok.fbx")
        self.assertTrue(row["passes"])
        self.assertLess(row["turned_deg"], 1e-9)

    def test_a_scaled_parent_alone_fails(self):
        (row,) = S.screen_scene(scene(F.UNREAL_IMPORT_AXES, mesh_s=(100, 100, 100)), "scaled.fbx")
        self.assertFalse(row["passes"])
        self.assertLess(row["turned_deg"], 1e-9)

    @unittest.skipUnless(T.parser_available(), "needs Blender's io_scene_fbx parser")
    def test_the_committed_drone_lod0_passes(self):
        rows = S.screen(DRONE / "SM_Drone_Inventory.fbx")
        self.assertEqual(sorted(r["socket"] for r in rows), ["Eye", "NetMuzzle"])
        self.assertTrue(all(r["passes"] for r in rows))


def drone_readback(tag):
    """Root's s80 import of the drone LOD0, with each rotator's right and up added from FRotationMatrix."""
    out = {}
    for name, row in T.RECEIPT["runs"]["s80"]["readback"]["imports"][tag]["sockets"].items():
        _x, y, z = F.rotator_axes(*row["rotation_pyr"])
        out[name] = {**row, "right": y.tolist(), "up": z.tolist()}
    return out


class Gates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        record = json.loads((DRONE / "build_record.json").read_text(encoding="utf-8"))
        cls.positions, cls.axes = record["assets"]["SM_Drone_Inventory"]["sockets"], record["socket_axes"]

    def test_the_original_fails_on_scale_forward_and_up_but_not_right(self):
        failures = G.socket_failures(drone_readback("original"), self.positions, self.axes, main_mesh=False)
        for name in ("Eye", "NetMuzzle"):
            self.assertTrue(any(f.startswith(f"{name} is scaled") for f in failures), failures)
            self.assertTrue(any(f.startswith(f"{name} forward") for f in failures), failures)
            self.assertTrue(any(f.startswith(f"{name} up") for f in failures), failures)
            self.assertFalse(any(f.startswith(f"{name} right") for f in failures), failures)
            self.assertFalse(any(f.startswith(f"{name} moved") for f in failures), failures)

    def test_the_corrected_file_passes(self):
        self.assertEqual(G.socket_failures(drone_readback("corrected"), self.positions, self.axes, main_mesh=False), [])

    def test_a_main_mesh_needs_the_admission_sockets(self):
        failures = G.socket_failures(drone_readback("corrected"), self.positions, self.axes, main_mesh=True)
        self.assertEqual(sorted(failures), sorted(f"{n} is missing (admission)" for n in G.ADMISSION))

    def test_both_real_imports_agree_with_the_model_on_every_axis(self):
        for tag, model_scene in (("original", T.FC0858A9), ("corrected", T.CORRECTED)):
            predicted = {n: {"position_cm": s["position_cm"].tolist(), "scale": s["scale"].tolist(),
                             "forward": s["x"].tolist(), "right": s["y"].tolist(), "up": s["z"].tolist()}
                         for n, s in F.interchange(model_scene)["sockets"].items()}
            worst = G.model_agreement(drone_readback(tag), predicted)
            self.assertTrue(G.agrees(worst), (tag, worst))

    def test_same_import_sees_moved_vertices_slots_and_collision(self):
        mesh = {"lod0": {"sections": [{"positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "indices": [0, 1, 2],
                                       "normals": [[0, 0, 1]] * 3, "uvs": [[0, 0], [1, 0], [0, 1]],
                                       "tangents": [[1, 0, 0]] * 3}]},
                "materials": [["M", "M", "M"]], "collision": {"convex": 0, "other_simple": 0}}
        self.assertEqual(G.same_import(mesh, copy.deepcopy(mesh))[1], [])
        moved = copy.deepcopy(mesh)
        moved["lod0"]["sections"][0]["positions"][1] = [1, 0, 0.01]
        self.assertTrue(any("positions_cm" in f for f in G.same_import(mesh, moved)[1]))
        slots = copy.deepcopy(mesh)
        slots["materials"] = [["N", "N", "N"]]
        self.assertTrue(any("material slots" in f for f in G.same_import(mesh, slots)[1]))
        hull = copy.deepcopy(mesh)
        hull["collision"]["convex"] = 1
        self.assertTrue(any("collision" in f for f in G.same_import(mesh, hull)[1]))


class Record(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((RUNTIME / "W02_Kusarigama/build_record.json").read_text(encoding="utf-8"))

    def test_amend_changes_only_the_socketed_lod0s_and_adds_the_blocks(self):
        rewritten, axes = {}, {}
        for asset in ("SM_Weapon_02", "SM_Weapon_02_Chain"):
            lod0 = self.record["assets"][asset]["lods"][0]
            rewritten[asset] = (lod0["file"], "f" * 64, lod0["sha256"])
            axes[asset] = {s: {"x": [1, 0, 0], "z": [0, 0, 1]} for s in self.record["assets"][asset]["sockets"]}
        amended = X.amend_record(self.record, rewritten, axes, "tool.py")
        self.assertEqual([f["file"] for f in amended["socket_fbx"]["files"]], [v[0] for v in rewritten.values()])
        reverted = copy.deepcopy(amended)
        del reverted["socket_fbx"]
        for asset, (file, _new, old) in rewritten.items():
            self.assertEqual(reverted["assets"][asset]["lods"][0]["sha256"], "f" * 64)
            reverted["assets"][asset]["lods"][0]["sha256"] = old
            self.assertEqual(reverted["assets"][asset].pop("socket_axes"), axes[asset])
        self.assertEqual(reverted, self.record)
        self.assertNotIn("socket_fbx", self.record)                      # the input is not changed

    def test_amend_refuses_a_stale_lod0(self):
        lod0 = self.record["assets"]["SM_Weapon_02"]["lods"][0]
        with self.assertRaises(ValueError):
            X.amend_record(self.record, {"SM_Weapon_02": (lod0["file"], "f" * 64, "0" * 64)}, {"SM_Weapon_02": {}}, "t")


class Preconditions(unittest.TestCase):
    def test_every_socketed_lod0_and_blend_matches_its_record_but_a_stale_w14(self):
        mismatched, socketed = set(), 0
        for rec_path in sorted(RUNTIME.glob("W*/build_record.json")):
            record = json.loads(rec_path.read_text(encoding="utf-8"))
            for asset, entry in record["assets"].items():
                if not entry.get("sockets"):
                    continue
                socketed += 1
                lod0 = ROOT / entry["lods"][0]["file"]
                if sha(lod0) != entry["lods"][0]["sha256"] or sha(ROOT / record["blend"]["file"]) != record["blend"]["sha256"]:
                    mismatched.add(rec_path.parent.name)
        self.assertEqual(socketed, 26)
        self.assertLessEqual(mismatched, {"W14_PlasmaMatchlock"})


if __name__ == "__main__":
    unittest.main()
