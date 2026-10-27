"""Host tests for the b09 Unreal scripts, without Unreal.

Run: python3 -m unittest scripts/unreal/test_b09_workshop_review.py

**render_b09_workshop_review.py.** Its shot list runs here against a stand-in `unreal` module. The stand-in provides
Vector, Rotator, and MakeRotFromXZ as UE 5.8 computes them: FRotationMatrix::MakeFromXZ, then FMatrix::Rotator. The
shots are checked for:
- every mesh placed is a candidate asset, and every socket read is the spec's;
- the needle turns as the gauge contract says, toward (0, sin a, cos a);
- the paste brush stands on the hero's side of the turned lantern, and the sheet being pasted has left the stack;
- the brushes' handles point back toward the hero; the split strip lies along its socket; weapon 7 lies with its
  fuse toward the hero;
- the exposure is metered from the lamps at the work points;
- it labels itself a socket-pose review and never calls quit_editor (the exit hang, EDITOR_EXIT_HANG.md).

**import_b09_workshop_candidates.py:**
- every slot of every candidate has a material;
- each socket is read back on its axes and at its scale, as well as at its point.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import math
import re
import sys
import types
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ART = HERE.parents[1]
CAPTURE = HERE / "render_b09_workshop_review.py"
IMPORT = HERE / "import_b09_workshop_candidates.py"
SPEC = ART / "docs/art-direction/data/b09_workshop_craft_spec.json"
sys.path.insert(0, str(ART / "scripts/art"))
import b09_workshop_craft as B  # noqa: E402


class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Rotator:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll, self.pitch, self.yaw = float(roll), float(pitch), float(yaw)


def rotation_rows(r):
    """FRotationMatrix's rows: the images of the local X, Y and Z axes."""
    p, y, w = (math.radians(v) for v in (r.pitch, r.yaw, r.roll))
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(w), math.cos(w)
    return np.array([[cp * cy, cp * sy, sp],
                     [sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp],
                     [-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp]])


def make_rot_from_xz(x, z):
    """UKismetMathLibrary::MakeRotFromXZ: FRotationMatrix::MakeFromXZ, then FMatrix::Rotator."""
    nx = np.array([x.x, x.y, x.z]) / np.linalg.norm([x.x, x.y, x.z])
    nz = np.array([z.x, z.y, z.z]) / np.linalg.norm([z.x, z.y, z.z])
    ny = np.cross(nz, nx)
    ny /= np.linalg.norm(ny)
    nz = np.cross(nx, ny)
    pitch = math.degrees(math.atan2(nx[2], math.hypot(nx[0], nx[1])))
    yaw = math.degrees(math.atan2(nx[1], nx[0]))
    sy = rotation_rows(Rotator(0.0, pitch, yaw))[1]
    return Rotator(roll=math.degrees(math.atan2(nz @ sy, ny @ sy)), pitch=pitch, yaw=yaw)


def load_capture():
    """The capture module with a stand-in `unreal`, which is removed again; sora_engine_pin is the real one."""
    sys.path.insert(0, str(HERE))
    import sora_engine_pin
    stub = types.ModuleType("unreal")
    stub.Vector, stub.Rotator = Vector, Rotator
    stub.MathLibrary = types.SimpleNamespace(make_rot_from_xz=make_rot_from_xz)
    stub.Paths = types.SimpleNamespace(project_dir=lambda: str(ART) + "/")
    stub.SystemLibrary = types.SimpleNamespace(get_engine_version=lambda: sora_engine_pin.ENGINE_VERSION)
    stub.get_editor_subsystem = lambda cls: None
    stub.__getattr__ = lambda name: types.SimpleNamespace()
    saved = sys.modules.get("unreal")
    sys.modules["unreal"] = stub
    try:
        spec = importlib.util.spec_from_file_location("b09_review_under_test", CAPTURE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            del sys.modules["unreal"]
        else:
            sys.modules["unreal"] = saved
    return module


class Capture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = load_capture()
        cls.spec = json.loads(SPEC.read_text())
        cls.shots = {s["name"]: s for s in cls.R.shots(cls.spec)}
        cls.text = CAPTURE.read_text(encoding="utf-8")

    def items(self, shot, mesh):
        return [it for it in self.shots[shot]["items"] if it[0] == mesh]

    def test_every_mesh_is_a_candidate_and_every_socket_the_specs(self):
        names = {n for n, *_ in B.candidates()} | {"SM_B09_Weapon07_ReviewStandIn"}
        for s in self.shots.values():
            for mesh, loc, rot, params in s["items"]:
                self.assertIn(mesh, names, s["name"])
                self.assertTrue(np.isfinite(loc).all())
        read = set()

        class Recording(dict):                                              # a missing socket raises KeyError
            def __getitem__(self, key):
                read.add(key)
                return dict.__getitem__(self, key)
        spec = json.loads(SPEC.read_text())
        for st in spec["stations"]:
            st["sockets"] = Recording(st["sockets"])
        self.R.shots(spec)
        self.assertTrue({"GaugePivot", "SplitStripRest", "LanternCentre", "Seam3_4", "BrushRest", "WashiSheet1",
                         "RimTopRest", "RimTopSeat", "RimBottomSeat", "LanternHang", "OilStroke0_4", "WeaponRest",
                         "ShellSeat3", "ShellCore3"} <= read, read)
        self.assertEqual(len(self.shots), 15)
        for name in ("rib_midbend", "rib_midbend_21x9", "paste_halfseam", "oil_half", "shell_two", "rafters_40"):
            self.assertIn(name, self.shots)

    def test_the_needle_points_as_the_gauge_contract_says(self):
        for shot, ms in (("rib_midbend", 640), ("rib_split", 0), ("rib_six", 0)):
            (mesh, loc, rot, _), = self.items(shot, "SM_B09_GaugeNeedle")
            a = math.radians(B.gauge_angle(ms))
            np.testing.assert_allclose(rotation_rows(rot)[2], [0.0, math.sin(a), math.cos(a)], atol=1e-9)
            st = self.spec["stations"][0]
            np.testing.assert_allclose(loc, self.R.world_of(st, st["sockets"]["GaugePivot"]["cm"]))
        self.assertAlmostEqual(B.gauge_angle(640), 30.0)                    # mid-bend: the green band's edge

    def test_the_paste_brush_works_the_seam_facing_the_hero(self):
        st = self.spec["stations"][1]
        centre = self.R.world_of(st, st["sockets"]["LanternCentre"]["cm"])
        (mesh, loc, rot, _), = self.items("paste_halfseam", "SM_B09_PasteBrush")
        self.assertAlmostEqual(math.degrees(math.atan2(loc[1] - centre[1], loc[0] - centre[0])) % 360.0, 180.0, places=6)
        self.assertAlmostEqual(loc[2], centre[2], places=6)                 # Seam3_4, halfway up at 750 ms
        sheets = [m for m, *_ in self.shots["paste_halfseam"]["items"] if m.startswith("SM_B09_WashiSheet")]
        self.assertEqual(sheets, ["SM_B09_WashiSheet1"])                     # 4 - 2 committed - 1 held
        (_, _, _, params), = self.items("paste_halfseam", "SM_B09_Washi3")
        self.assertEqual(params, {"M_B09_Washi": {"PasteReveal": 0.5}})
        self.assertEqual(self.shots["paste_halfseam"]["state"]["turntable_yaw_deg"], -180.0)

    def test_tools_and_strip_lie_as_designed(self):
        for shot, mesh in (("paste_halfseam", "SM_B09_PasteBrush"), ("oil_half", "SM_B09_OilBrush")):
            (_, _, rot, _), = self.items(shot, mesh)
            rows = rotation_rows(rot)
            np.testing.assert_allclose(rows[1], [-math.cos(math.radians(30)), 0.0, 0.5], atol=1e-3)   # the handle
            np.testing.assert_allclose(rows[0], [0.0, 1.0, 0.0], atol=1e-9)                           # the flat's width
        (_, _, rot, _), = self.items("rib_split", "SM_B09_SplitStrip")
        np.testing.assert_allclose(rotation_rows(rot)[0], [0.0, 1.0, 0.0], atol=1e-9)
        (_, loc, rot, _), = self.items("shell_two", "SM_B09_Weapon07_ReviewStandIn")
        origin, r = B.weapon_rest()
        rows = rotation_rows(rot)
        np.testing.assert_allclose(rows[0], r[:, 0], atol=1e-9)                                     # the bore
        np.testing.assert_allclose(rows[2], r[:, 2], atol=1e-9)                                     # the fuse side
        self.assertLess(rows[2][0], 0.0)                                                            # toward the hero

    def test_the_exposure_is_metered_from_the_lamps(self):
        ev, lux = self.R.metered_ev100(self.spec)
        self.assertEqual(len(lux), 4)
        self.assertAlmostEqual(ev, math.log2(float(np.median(lux)) / 2.5))
        self.assertTrue(2.0 < ev < 6.0, ev)

    def test_two_light_sets_and_roots_surfaces(self):
        self.assertEqual(set(self.R.LIGHT_SETS), {"neutral", "night"})
        self.assertEqual(self.R.LIGHT_SETS["neutral"]["lamp_kelvin"], 6500.0)
        night = self.R.LIGHT_SETS["night"]
        shift = 1e6 / 2200 - 1e6 / 3400                                       # the intended lamp under a tungsten balance
        self.assertAlmostEqual(1e6 / (1e6 / 6500 + shift), night["lamp_kelvin"], delta=60.0)
        self.assertLess(night["ev_offset"], 0.0)
        surfaces = set(self.spec["room"]["surfaces"])
        self.assertTrue(surfaces <= set(self.R.REVIEW), surfaces)
        self.assertTrue({"Floor", "Ceiling"} <= set(self.R.REVIEW))

    def test_its_engine_calls_are_ones_working_scripts_use(self):
        code = re.sub(r"#.*", "", self.text)
        for call in ("create_dynamic_material_instance", "set_collision_enabled", "get_material_index", "set_light_color"):
            self.assertNotIn(call, code)                                     # no working script calls these
        state = ast.get_source_segment(self.text, next(n for n in ast.walk(ast.parse(self.text))
                                                       if isinstance(n, ast.FunctionDef) and n.name == "review_state"))
        for call in ("set_material_instance_parent", "set_material_instance_scalar_parameter_value", "MaterialInstanceConstantFactoryNew"):
            self.assertIn(call, state)

    def test_a_readback_with_problems_needs_a_review_that_explains_each(self):
        main = ast.get_source_segment(self.text, next(n for n in ast.walk(ast.parse(self.text))
                                                      if isinstance(n, ast.FunctionDef) and n.name == "main"))
        self.assertIn('fail("the import\'s readback has problems and no host review explains them")', main)
        for needle in ('review["readback_sha256"] != hashlib.sha256(rb_bytes).hexdigest()', 'review["unexplained"]',
                       'sorted(review["explained"]) != sorted(rb["problems"])'):
            self.assertIn(needle, main)
        self.assertLess(main.index('if rb["problems"]:'), main.index("build(spec, ev100, opts[\"light\"])"))
        self.assertIn('"a diagnostic capture of a failed import candidate: its readback problems stand.', main)
        self.assertIn('"readback_problems": rb["problems"]', main)                  # kept verbatim (Coordination 237)

    def test_it_draws_the_readbacks_candidates(self):
        main = next(n for n in ast.walk(ast.parse(self.text)) if isinstance(n, ast.FunctionDef) and n.name == "main")
        src = ast.get_source_segment(self.text, main)
        self.assertIn('MESHES, MATS = f"{rb[\'base\']}/Meshes", f"{rb[\'base\']}/Materials"', src)
        self.assertLess(src.index("MESHES, MATS ="), src.index("build(spec, ev100, opts[\"light\"])"))

    def test_it_is_a_socket_pose_review_and_never_quits_from_slate(self):
        self.assertIn("socket-pose review", self.text)
        self.assertIn("not runtime first-person hand contact", self.text.replace("\n", " ").replace("  ", " ").replace('" "', ""))
        code = re.sub(r"#.*", "", self.text)
        self.assertNotIn("quit_editor(", code)
        self.assertIn("unreal.EditorPythonScripting.set_keep_python_script_alive(False)", code)
        self.assertIn('write("manifest.partial.json")', code)


class Import(unittest.TestCase):
    text = IMPORT.read_text(encoding="utf-8")

    def test_every_candidate_slot_has_a_material(self):
        bound = set(re.findall(r'"(M_B09_[A-Za-z]+)": \("(?:cargo_wood|straw|ash|urushi|iron|bamboo|neutral)"', self.text)) | {"M_B09_Washi"}
        used = set()
        for name, mesh, *_ in B.candidates():
            used |= set(mesh.slots().tolist())
        self.assertEqual(used - bound, set())
        self.assertIn('mats["M_B09_Washi"] = instance("MI_B09_Washi", washi)', self.text)

    def function(self, name):
        tree = ast.parse(self.text)
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(self.text, node)

    def test_every_material_source_is_in_the_tree_and_tracked(self):
        import subprocess
        tree = ast.parse(self.text)
        consts = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                try:
                    consts[n.targets[0].id] = ast.literal_eval(n.value)
                except ValueError:
                    pass
        env = {k: v for k, v in consts.items() if isinstance(v, str)}
        textures = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TEXTURES":
                for k, v in zip(n.value.keys, n.value.values):
                    path = "".join(env[x.value.id] if isinstance(x, ast.FormattedValue) else x.value for x in v.elts[0].values) \
                        if isinstance(v.elts[0], ast.JoinedStr) else v.elts[0].value
                    textures[k.value] = path
        self.assertGreaterEqual(len(textures), 25)
        for name, path in textures.items():
            self.assertTrue((ART / path).is_file(), (name, path))
            r = subprocess.run(["git", "-C", str(ART), "ls-files", "--error-unmatch", path], capture_output=True)
            self.assertEqual(r.returncode, 0, f"{path} is not tracked")
        for slot, (maps, *_rest) in consts["OPAQUE"].items():
            if maps != "neutral":
                for k in ("Albedo", "NormalDX", "ORM"):
                    self.assertIn(f"T_B09_{consts['MAPSETS'][maps]}_{k}", textures, slot)
            self.assertGreater(_rest[-1], 0.0)                                 # each slot's tile, in cm
        self.assertNotIn("M_Nyaakoto_PBR\"", self.text)                       # the furred character's master is gone
        self.assertNotIn("wood_planks_dirt_", self.text)

    def test_sockets_are_read_back_by_name_on_their_axes(self):
        read = self.function("read_socket")
        self.assertIn("mesh.find_socket(name)", read)                      # StaticMesh.Sockets is protected (s146)
        for key in ("relative_location", "relative_rotation", "relative_scale"):
            self.assertIn(key, read)
        self.assertNotIn('get_editor_property("sockets")', re.sub(r"#.*", "", self.text))
        mesh = self.function("import_mesh")
        for needle in ("read_socket(mesh, sname)", 'a["socket_axes"][sname]', "SOCKET_TOL_AXIS", "SOCKET_TOL_CM"):
            self.assertIn(needle, mesh)
        self.assertIn('set_editor_property("auto_generate_collision", False)', mesh)
        self.assertIn("read_socket(weapon, n) for n in sorted(w_record)", self.function("import_weapon"))

    def test_each_run_imports_into_a_new_base_and_fails_part_by_part(self):
        main = self.function("main")
        self.assertIn('base = arg("--base")', main)
        self.assertIn('fail(f"{BASE} exists: the candidates are new assets")', main)
        for part in ("import_mesh(name, a, build, mats, rows, problems)", "import_weapon(tex, prop, rows, problems)",
                     "washi = washi_master(tex)"):
            i = main.index(part)
            self.assertIn("try:", main[max(0, i - 120):i])                 # a failure is a problem, not the run's end
        self.assertLess(main.index("json.dump(readback, fh"), main.index('fail(f"{len(problems)} problems'))
        self.assertIn('"base": BASE', main)


if __name__ == "__main__":
    unittest.main()
