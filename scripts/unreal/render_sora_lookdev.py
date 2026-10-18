"""Fixed-camera Unreal look-development captures of authored props (editor views).

Run in the pinned editor with a renderer, after the prop's importer:

    scripts/toolchain/run-editor-script.sh --rhi scripts/unreal/render_sora_lookdev.py \
        SORA_LOOKDEV_COMPLETE -- props=SM_SoraRadenBunko rigs=golden,overcast,lantern out=Bunko

It builds the uncooked level /Game/ArtReview/LookDev/L_SoraLookDev: a timber
floor, the listed props from /Game/Generated/Environment/Props at the origin,
and one lighting rig at a time — a physically based SkyAtmosphere sun 7 degrees
above the horizon (golden), a 50-degree sun behind thin overcast (overcast), or
two 2,200 K paper-lantern point lights at night (lantern) — each under a fixed
manual exposure so A/B pairs are comparable. Cameras sit at 1.0 m and 2.5 m
(three-quarter and front, 35 mm). Captures go to
Saved/SoraLookDev/<out>/<rig>_<view>.png. These are **editor look-development
views on the Mac (software Lumen, no Nanite)**, not gameplay captures.
"""

from __future__ import annotations

from pathlib import Path
import math
import sys
import time

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("SORA look development")
ROOT = Path(unreal.Paths.project_dir()).resolve()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
EDITOR = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


class _Pending:
    """Stands in for a screenshot task: done at once; the file wait follows."""

    def is_task_done(self):
        return True
LEVEL = f"/Game/ArtReview/LookDev/L_SoraLookDev_{int(time.time())}"


def parse_args():
    opts = {"props": "SM_SoraRadenBunko", "rigs": "golden,overcast,lantern", "out": "LookDev",
            "dist": "1.0,2.5", "res": "1920x1080", "ev": ""}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            opts[k] = v
    return opts


def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"SORA look-dev: missing asset {path}")
    return asset


def spawn(cls, loc, rot=(0.0, 0.0, 0.0)):
    return ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))


def build_level(props):
    # A fresh, uniquely named level per run (never cooked: ArtReview is not in
    # the cook list); earlier runs' files are removed by the caller.
    ASSETS.make_directory(LEVEL.rsplit("/", 1)[0])
    if not LEVELS.new_level(LEVEL):
        raise RuntimeError("SORA look-dev: could not create the look-dev level")
    floor = spawn(unreal.StaticMeshActor, (0.0, 0.0, 0.0))
    floor.static_mesh_component.set_static_mesh(load("/Engine/BasicShapes/Plane.Plane"))
    floor.set_actor_scale3d(unreal.Vector(60.0, 60.0, 1.0))
    timber = unreal.load_asset("/Game/Generated/Environment/MI_Nyaagyu_Timber.MI_Nyaagyu_Timber")
    if timber:
        floor.static_mesh_component.set_material(0, timber)
    centre_z = 0.0
    lib = unreal.MaterialEditingLibrary
    compiled = set()
    for name in props:
        mesh = load(name if name.startswith("/Game/") else f"/Game/Generated/Environment/Props/{name}.{name}")
        actor = spawn(unreal.StaticMeshActor, (0.0, 0.0, 0.0))
        actor.static_mesh_component.set_static_mesh(mesh)
        bounds = mesh.get_bounds()
        centre_z = max(centre_z, bounds.origin.z)
        # Compile each base material for this platform before any capture, so
        # no frame shows the default material, and a broken Custom node fails.
        for index in range(len(mesh.get_editor_property("static_materials"))):
            material = mesh.get_material(index)
            base = material.get_base_material() if material else None
            if base and base.get_path_name() not in compiled:
                stats = lib.get_statistics(base)
                if stats.get_editor_property("num_pixel_shader_instructions") <= 0:
                    raise RuntimeError(f"SORA look-dev: {base.get_path_name()} did not compile")
                compiled.add(base.get_path_name())
    unreal.SystemLibrary.execute_console_command(None, "r.TextureStreaming 0")
    return centre_z


class Rig:
    def __init__(self):
        self.actors = []

    def clear(self):
        for a in self.actors:
            ACTORS.destroy_actor(a)
        self.actors = []

    def add(self, actor):
        self.actors.append(actor)
        return actor

    def sky(self, sun_pitch, sun_yaw, sun_lux, sun_k, fog_density, ev100, mie=1.0):
        atmosphere = self.add(spawn(unreal.SkyAtmosphere, (0.0, 0.0, 0.0)))
        atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent).set_editor_property(
            "mie_scattering_scale", mie)
        sun = self.add(spawn(unreal.DirectionalLight, (0.0, 0.0, 500.0), (0.0, sun_pitch, sun_yaw)))
        light = sun.light_component
        light.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        light.set_intensity(sun_lux)
        light.set_use_temperature(True)
        light.set_temperature(sun_k)
        light.set_editor_property("atmosphere_sun_light", True)
        light.set_editor_property("light_source_angle", 0.53)
        sky = self.add(spawn(unreal.SkyLight, (0.0, 0.0, 300.0)))
        sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        sky.light_component.set_editor_property("real_time_capture", True)
        sky.light_component.set_intensity(1.0)
        fog = self.add(spawn(unreal.ExponentialHeightFog, (0.0, 0.0, 0.0)))
        fc = fog.component
        fc.set_fog_density(fog_density)
        fc.set_volumetric_fog(True)
        self.exposure(ev100)

    def lantern(self, ev100):
        atmosphere = self.add(spawn(unreal.SkyAtmosphere, (0.0, 0.0, 0.0)))
        moon = self.add(spawn(unreal.DirectionalLight, (0.0, 0.0, 500.0), (0.0, -35.0, 120.0)))
        moon.light_component.set_intensity(0.25)
        moon.light_component.set_use_temperature(True)
        moon.light_component.set_temperature(7800.0)
        moon.light_component.set_editor_property("atmosphere_sun_light", True)
        sky = self.add(spawn(unreal.SkyLight, (0.0, 0.0, 300.0)))
        sky.light_component.set_editor_property("real_time_capture", True)
        for loc, lm in (((-90.0, -70.0, 75.0), 160.0), ((110.0, 50.0, 115.0), 110.0)):
            p = self.add(spawn(unreal.PointLight, loc))
            pc = p.point_light_component
            pc.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
            pc.set_intensity(lm)
            pc.set_use_temperature(True)
            pc.set_temperature(2200.0)
            pc.set_editor_property("source_radius", 9.0)
            pc.set_attenuation_radius(900.0)
        self.exposure(ev100)

    def exposure(self, ev100):
        """``ev100`` None: the game's histogram auto exposure (SoraWorldBuilderLighting.cpp);
        a number: fixed manual exposure for strict A/B pairs."""
        volume = self.add(spawn(unreal.PostProcessVolume, (0.0, 0.0, 0.0)))
        volume.set_editor_property("unbound", True)
        s = volume.get_editor_property("settings")
        if ev100 is None:
            pairs = (("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
                     ("auto_exposure_low_percent", 12.0), ("auto_exposure_high_percent", 88.0),
                     ("auto_exposure_speed_up", 20.0), ("auto_exposure_speed_down", 20.0),
                     ("auto_exposure_bias", -0.45))
        else:
            pairs = (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                     ("auto_exposure_apply_physical_camera_exposure", False),
                     ("auto_exposure_bias", -ev100 + 1.0))
        for key, value in pairs:
            s.set_editor_property(f"override_{key}", True)
            s.set_editor_property(key, value)
        volume.set_editor_property("settings", s)


RIG_EV = {"golden": 8.0, "overcast": 10.5, "lantern": 1.5}


def apply_rig(rig, name, ev_override):
    rig.clear()
    ev = None if ev_override is None else ev_override
    if name == "golden":
        rig.sky(-7.0, 205.0, 75000.0, 5900.0, 0.012, ev)
    elif name == "overcast":
        rig.sky(-50.0, 160.0, 20000.0, 6500.0, 0.03, ev, mie=6.0)
    elif name == "lantern":
        rig.lantern(ev)
    else:
        raise RuntimeError(f"SORA look-dev: unknown rig {name}")


def cameras(centre_z, distances):
    cams = []
    for dist in distances:
        d = dist * 100.0
        for view, yaw in (("ThreeQuarter", -35.0), ("Front", 0.0)):
            a = math.radians(yaw)
            eye = unreal.Vector(math.sin(a) * d, -math.cos(a) * d, centre_z + 0.35 * d + 25.0)
            target = unreal.Vector(0.0, 0.0, centre_z)
            rot = unreal.MathLibrary.find_look_at_rotation(eye, target)
            cam = spawn(unreal.CineCameraActor, (eye.x, eye.y, eye.z), (rot.roll, rot.pitch, rot.yaw))
            comp = cam.get_cine_camera_component()
            comp.set_editor_property("current_focal_length", 35.0)
            fs = comp.get_editor_property("focus_settings")
            fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
            comp.set_editor_property("focus_settings", fs)
            cams.append((f"{view}_{dist:.1f}m", cam))
    return cams


def main():
    opts = parse_args()
    props = [p for p in opts["props"].split(",") if p]
    rigs = [r for r in opts["rigs"].split(",") if r]
    distances = [float(x) for x in opts["dist"].split(",")]
    width, height = (int(x) for x in opts["res"].split("x"))
    ev_override = float(opts["ev"]) if opts["ev"] else None
    out = ROOT / "Saved/SoraLookDev" / opts["out"]
    out.mkdir(parents=True, exist_ok=True)
    centre_z = build_level(props)
    cams = cameras(centre_z, distances)
    rig = Rig()
    queue = [(r, name, cam) for r in rigs for name, cam in cams]
    status = {"task": None, "frames": 0, "written": [], "rig": None, "settle": 0}

    def finish(message, error=False):
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def tick(delta):
        try:
            step(delta)
        except Exception as exc:  # never spin on a failing callback
            finish(f"SORA_LOOKDEV_FAILED: {exc!r}", error=True)

    def step(_delta):
        status["frames"] += 1
        LEVELS.editor_invalidate_viewports()
        if status["frames"] < 20:
            return
        task = status["task"]
        if task is not None and not task.is_task_done():
            return
        if task is not None:
            path = status["current"]
            if not path.is_file() or path.stat().st_mtime < status["started"]:
                status["wait"] += 1
                if status["wait"] > 4000:
                    finish(f"SORA_LOOKDEV_FAILED: {path} was not written", error=True)
                return
            status["written"].append(path.name)
            status["task"] = None
        if not queue:
            finish(f"SORA_LOOKDEV_COMPLETE: {len(status['written'])} captures in {out}: "
                   + ", ".join(status["written"]))
            return
        rig_name, view, cam = queue[0]
        if status["rig"] != rig_name:
            apply_rig(rig, rig_name, ev_override)
            status["rig"] = rig_name
            status["settle"] = 0
        # Let Lumen's surface cache and screen probes converge after a rig change.
        status["settle"] += 1
        if status["settle"] < (240 if not status["written"] else 90):
            return
        if status.get("posed") != view + rig_name:
            # Look through the camera (its 35 mm lens) in game view (no editor
            # icons), then let Lumen, TSR and exposure settle.
            LEVELS.pilot_level_actor(cam)
            LEVELS.editor_set_game_view(True)
            status["posed"] = view + rig_name
            status["pose_frames"] = 0
            return
        status["pose_frames"] += 1
        if status["pose_frames"] < 75:
            return
        queue.pop(0)
        status["current"] = out / f"{rig_name}_{view}.png"
        status["started"], status["wait"] = time.time(), 0
        unreal.SystemLibrary.execute_console_command(
            None, f'HighResShot {width}x{height} filename="{status["current"]}"')
        status["task"] = _Pending()

    handle = unreal.register_slate_post_tick_callback(tick)
    # -ExecutePythonScript closes the editor once the script returns unless it
    # asks to stay; finish() releases it after the last capture.
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


main()
