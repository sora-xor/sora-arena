"""Host-only tests of the VFX review stills' shot table and blade-sweep harness; a stub `unreal`, no editor.

diagnostics/render_vfx_previews.py runs inside the editor, so these load it
with a minimal stand-in for the `unreal` module (real vector and rotator maths,
mocks for the rest) and check what does not need a renderer: every system has
a shot, no two stills share a file name, the forge's three gauge states are all
rendered, and the blade trail is swept with +X along the blade, across its
path, in the plane that faces the camera.
"""

import importlib.util
import math
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent


class Vector:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scale):
        return Vector(self.x * scale, self.y * scale, self.z * scale)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other):
        return Vector(self.y * other.z - self.z * other.y, self.z * other.x - self.x * other.z,
                      self.x * other.y - self.y * other.x)

    def length(self):
        return math.sqrt(self.dot(self))


class Rotator:
    def __init__(self, roll=0.0, pitch=0.0, yaw=0.0):
        self.roll, self.pitch, self.yaw = float(roll), float(pitch), float(yaw)


def forward(rotator):
    """Unreal's forward (+X) vector of a rotator: pitch up from the XY plane, yaw about +Z."""
    pitch, yaw = math.radians(rotator.pitch), math.radians(rotator.yaw)
    return Vector(math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))


def load_preview_script(output):
    unreal = types.ModuleType("unreal")
    unreal.Vector, unreal.Rotator = Vector, Rotator
    unreal.MathLibrary = types.SimpleNamespace(get_forward_vector=forward, make_rot_from_x=mock.MagicMock())
    unreal.Paths = types.SimpleNamespace(project_dir=lambda: str(output))
    unreal.__getattr__ = lambda name: mock.MagicMock(name=f"unreal.{name}")
    pin = types.ModuleType("sora_engine_pin")
    pin.require_running_engine = lambda what: None
    spec = importlib.util.spec_from_file_location("render_vfx_previews_under_test",
                                                  HERE / "diagnostics/render_vfx_previews.py")
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {"unreal": unreal, "sora_engine_pin": pin}), \
            mock.patch.dict("os.environ", {"SORA_VFX_PREVIEW_DIR": str(output)}):
        spec.loader.exec_module(module)
    return module


class FakeActor:
    def set_actor_location(self, location, sweep, teleport):
        self.location = location

    def set_actor_rotation(self, rotation, teleport):
        self.rotation = rotation


class PreviewShots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="sora-vfx-preview-")
        cls.previews = load_preview_script(Path(cls.temporary.name))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_every_built_system_has_a_shot(self):
        builder = (HERE / "create_sora_vfx.py").read_text(encoding="utf-8")
        built = set(re.findall(r'System\("(NS_SoraVFX_\w+)"', builder))
        self.assertEqual(len(built), 27)
        self.assertEqual({shot.name for shot in self.previews.SHOTS}, built)

    def test_no_two_stills_share_a_file_name(self):
        names = [self.previews.still_name(shot, age) for shot in self.previews.QUEUE for age in shot.ages]
        self.assertEqual(len(names), len(set(names)))
        # the sheet script groups by <name>_<day|dusk>_<age>s.exr; a tag must keep that shape
        pattern = re.compile(r"(?P<name>.+)_(?P<light>day|dusk)_(?P<age>[0-9.]+)s$")
        self.assertTrue(all(pattern.match(name) for name in names), names)

    def test_a_repeated_still_stops_the_script(self):
        forge = next(shot for shot in self.previews.SHOTS if shot.name == "NS_SoraVFX_Forge_Fire")
        with mock.patch.object(self.previews, "SHOTS", self.previews.SHOTS + [forge._replace(user={"Bellows": 0.0})]):
            with self.assertRaisesRegex(RuntimeError, "overwrite each other"):
                self.previews.shot_queue()

    def test_the_forge_is_rendered_in_its_three_gauge_states(self):
        forge = [shot.user["Temperature"] for shot in self.previews.SHOTS if shot.name == "NS_SoraVFX_Forge_Fire"]
        self.assertEqual(sorted(forge), [0.0, .5, 1.0])

    def test_a_full_circle_cleave_is_rendered(self):
        arcs = [shot.user.get("ArcDegrees", 120.0) for shot in self.previews.SHOTS if shot.name == "NS_SoraVFX_Telegraph_Cleave"]
        self.assertIn(360.0, arcs)

    def test_the_projectile_trail_is_flown(self):
        trails = [shot for shot in self.previews.SHOTS if shot.name == "NS_SoraVFX_Trail_Projectile"]
        self.assertTrue(trails)
        self.assertTrue(all(shot.motion == "flight" for shot in trails))

    def test_rain_dispatches_each_simulation_step_with_a_render(self):
        rain = [shot for shot in self.previews.SHOTS if shot.name == "NS_SoraVFX_Rain"]
        self.assertEqual([shot.motion for shot in rain], ["render_steps"])
        runner = object.__new__(self.previews.Runner)
        runner.wait = 0
        runner.phase = "render_steps"
        runner.render_steps_left = 2
        runner.actor = mock.Mock()
        calls = mock.Mock()
        calls.attach_mock(runner.actor.niagara_component, "effect")
        with mock.patch.object(self.previews, "capture", calls.capture):
            runner._tick()
            self.assertEqual(runner.phase, "render_steps")
            runner._tick()
        self.assertEqual(calls.mock_calls, [
            mock.call.effect.advance_simulation(1, 1 / 60), mock.call.capture.capture_scene(),
            mock.call.effect.advance_simulation(1, 1 / 60), mock.call.capture.capture_scene(),
            mock.call.effect.set_paused(True),
        ])
        self.assertEqual(runner.phase, "capture")
        self.assertEqual(runner.wait, 2)

    def test_the_blade_sweeps_its_edge_across_its_path_facing_the_camera(self):
        pivot = self.previews.CUT_PIVOT
        actor, poses = FakeActor(), []
        for step in range(9):
            self.previews.place_blade(actor, pivot, step / 8)
            poses.append((actor.location, forward(actor.rotation)))
        for location, axis in poses:
            radial = location - pivot
            self.assertAlmostEqual(radial.length(), 90.0, places=6)
            self.assertAlmostEqual(axis.cross(radial).length(), 0.0, places=6)     # +X along the blade
            self.assertGreater(axis.dot(radial), 0.0)
        for (start, axis), (end, next_axis) in zip(poses, poses[1:]):
            path, edge = end - start, axis + next_axis        # a chord of the arc and the blade across its middle
            self.assertAlmostEqual(edge.dot(path) / (edge.length() * path.length()), 0.0, places=6)
        first, last = poses[0][1], poses[-1][1]
        self.assertAlmostEqual(math.degrees(math.acos(first.dot(last))), 100.0, places=6)
        normal = poses[0][1].cross(poses[4][1])
        normal = normal * (1.0 / normal.length())
        for shot in (shot for shot in self.previews.SHOTS if shot.motion == "sweep"):
            camera, look_at = shot.camera
            view = look_at - camera
            facing = abs(normal.dot(view)) / view.length()
            self.assertGreater(facing, math.cos(math.radians(10.0)), "the cut must face the camera, not lie edge-on")


if __name__ == "__main__":
    unittest.main()
