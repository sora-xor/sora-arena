"""Render review stills of the SORA Niagara effects in a throwaway editor world.

Run with a real RHI (no -nullrhi) after scripts/unreal/create_sora_vfx.py:

    UnrealEditor-Cmd SoraArena.uproject -ExecutePythonScript=scripts/unreal/diagnostics/render_vfx_previews.py \\
        -unattended -nosplash -stdout

Output EXRs (linear scene colour, before post-processing) go to
Saved/VFXPreview/<system>[_<tag>]_<light>_<age>.exr (override with the
SORA_VFX_PREVIEW_DIR environment variable; SORA_VFX_PREVIEW_ONLY=Name,Name
limits the systems). A shot that repeats a system and light with other user
parameters carries a tag, and the script refuses to start when two stills
would share a file name. Each effect is placed on a stone floor in front of a
plaster wall under the Estate's overcast daylight (a 25 lux sun, the overcast
HDRI sky light) or a dusk key (1.8 lux), advanced to fixed ages with
NiagaraComponent.advance_simulation and captured by a SceneCapture2D with
fixed settings, so repeated runs frame the same instants. Nothing is saved
into the project: the level is a new unsaved blank map. Tone-map and tile the
EXRs with scripts/unreal/diagnostics/vfx_preview_sheet.py (host Python).

These are art-review stills, not packaged-game evidence: no Lumen scene of a
real level, no bloom, motion blur or eye adaptation (the sheet script applies a
fixed exposure and a filmic curve). A capture made before the editor world has
ticked comes back empty, hence the warm-up.

Some shots move instead of stepping in place. The blade trail ("sweep")
swings the component through a 100-degree cut in the plane that faces the
camera, with +X along the blade as a sword socket would hold it. The
projectile trail ("flight") flies the component along its +X at 45 m/s.
Rain ("render_steps") advances one 1/60 s simulation step, then draws the main
editor viewport before continuing. UE's SceneCapture views exclude the GPU
post-opaque update used by depth collisions; a scene capture alone cannot
dispatch this effect correctly. Solo mode with component ticking disabled
prevents the editor world from adding simulation steps between manual steps.
The captured rain age is a prescribed simulation age, not a wall-clock age.

After the stills it checks that Niagara lights light the scene: on the dusk
stage it measures the floor under NS_SoraVFX_Lantern (150 lm by default)
against the bare stage and against an ordinary 150 lm point light in the same
place, and logs SORA_VFX_LIGHT_CHECK: PASS when the lantern brightens the floor
by 0.5 to 2 times what the point light adds (FAIL, as an error, otherwise). The
three captures are saved as LightCheck_<case>.exr beside the stills.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import NamedTuple

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("VFX preview")
ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ.get("SORA_VFX_PREVIEW_DIR", str(ROOT / "Saved/VFXPreview")))
OUT.mkdir(parents=True, exist_ok=True)
ONLY = {name for name in os.environ.get("SORA_VFX_PREVIEW_ONLY", "").split(",") if name}
WIDTH, HEIGHT = 960, 540
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
V, C = unreal.Vector, unreal.LinearColor


def R(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator's positional order is (roll, pitch, yaw); name them."""
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def log(message):
    unreal.log(f"SORA_VFX_PREVIEW: {message}")


class Shot(NamedTuple):
    name: str
    placement: tuple          # (location, rotation); for a sweep, the location is the cut's pivot
    camera: tuple             # (location, look-at)
    mode: str                 # "day" or "dusk"
    user: dict
    ages: list
    motion: str | None = None  # None (stepped in place), "sweep", "flight" or "render_steps"
    tag: str = ""             # tells apart stills of one system and light with other user parameters


def still_name(shot, age):
    return f"{shot.name[len('NS_SoraVFX_'):]}{'_' + shot.tag if shot.tag else ''}_{shot.mode}_{age:.2f}s"


UP = R(pitch=90.0)          # local +X up out of the floor
CUT_PIVOT = V(0, -60, 130)  # the blade trail's cut turns about the wielder's hands, 90 cm behind the blade's middle
SHOTS = [
    Shot("NS_SoraVFX_Muzzle_Matchlock", (V(0, -160, 150), R(0, 90, 0)), (V(-560, 60, 170), V(0, 60, 150)), "day", {}, [.02, .05, .12, .6, 2.0, 4.5]),
    Shot("NS_SoraVFX_Muzzle_Energy", (V(0, -60, 150), R(0, 90, 0)), (V(-260, 0, 160), V(0, 0, 150)), "dusk", {}, [.02, .05, .3]),
    Shot("NS_SoraVFX_Beam_Energy", (V(0, -500, 140), R(0, 90, 0)), (V(-700, 0, 180), V(0, 0, 140)), "dusk",
         {"BeamEnd": V(0, 500, 140), "Duration": 1.0}, [.03, .4]),
    Shot("NS_SoraVFX_Trail_Projectile", (V(0, -380, 150), R(0, 90, 0)), (V(-700, 0, 170), V(0, 0, 150)), "dusk",
         {}, [.15], "flight", tag="Bolt"),
    Shot("NS_SoraVFX_Trail_Projectile", (V(0, -380, 150), R(0, 90, 0)), (V(-700, 0, 170), V(0, 0, 150)), "day",
         {"Tint": C(.8, .8, .78), "Intensity": 1.5, "Width": 1.0}, [.15], "flight", tag="Arrow"),
    Shot("NS_SoraVFX_BladeTrail", (CUT_PIVOT, R(0, 0, 0)), (V(-380, 0, 150), V(0, 0, 140)), "day", {}, [.12], "sweep"),
    Shot("NS_SoraVFX_BladeTrail", (CUT_PIVOT, R(0, 0, 0)), (V(-380, 0, 150), V(0, 0, 140)), "dusk", {}, [.12], "sweep"),
    Shot("NS_SoraVFX_Impact_Wood", (V(0, 0, 1), UP), (V(-160, 0, 70), V(0, 0, 25)), "day", {}, [.04, .25, 1.0]),
    Shot("NS_SoraVFX_Impact_Stone", (V(0, 0, 1), UP), (V(-160, 0, 70), V(0, 0, 25)), "day", {"SparkAmount": 1.0}, [.04, .25, 1.0]),
    Shot("NS_SoraVFX_Impact_Dirt", (V(0, 0, 1), UP), (V(-220, 0, 80), V(0, 0, 30)), "day", {}, [.05, .3, 1.2]),
    Shot("NS_SoraVFX_Impact_Metal", (V(0, 0, 1), UP), (V(-160, 0, 70), V(0, 0, 25)), "dusk", {}, [.02, .12, .5]),
    Shot("NS_SoraVFX_Impact_Fur", (V(0, 0, 110), R(0, 180, 0)), (V(-170, 0, 115), V(0, 0, 100)), "day", {}, [.1, .6, 1.4]),
    Shot("NS_SoraVFX_ParrySparks", (V(0, 0, 130), R(0, 180, 0)), (V(-200, 0, 135), V(0, 0, 125)), "dusk", {}, [.02, .08, .3]),
    Shot("NS_SoraVFX_Explosion", (V(0, 0, 1), UP), (V(-1500, 0, 320), V(0, 0, 220)), "day", {}, [.03, .2, .7, 2.5, 5.0]),
    Shot("NS_SoraVFX_Hanabi_FireZone", (V(0, 0, 1), R(0, 0, 0)), (V(-1100, 0, 320), V(0, 0, 60)), "dusk", {"Radius": 300.0}, [2.5]),
    Shot("NS_SoraVFX_Hanabi_FireZone", (V(0, 0, 1), R(0, 0, 0)), (V(-1100, 0, 320), V(0, 0, 60)), "day", {"Radius": 300.0}, [2.5]),
    Shot("NS_SoraVFX_Kusushi_Heal", (V(0, 0, 1), R(0, 0, 0)), (V(-600, 0, 260), V(0, 0, 60)), "dusk", {}, [.3, .8]),
    Shot("NS_SoraVFX_Kusushi_Ward", (V(0, 0, 1), R(0, 0, 0)), (V(-650, 0, 280), V(0, 0, 90)), "day", {}, [3.0]),
    Shot("NS_SoraVFX_Shinobi_Decoy", (V(0, 0, 1), R(0, 0, 0)), (V(-700, 0, 200), V(0, 0, 110)), "day", {}, [.15, .8, 2.5]),
    Shot("NS_SoraVFX_Karakuri_BuildDust", (V(0, 0, 1), R(0, 0, 0)), (V(-500, 0, 180), V(0, 0, 40)), "day", {}, [2.5]),
    Shot("NS_SoraVFX_Telegraph_Beam", (V(-300, 0, 1), R(0, 0, 0)), (V(-900, 300, 700), V(400, 0, 0)), "day", {"Length": 1500.0}, [.3, 1.0]),
    Shot("NS_SoraVFX_Telegraph_Cleave", (V(0, 0, 1), R(0, 0, 0)), (V(-800, 250, 650), V(150, 0, 0)), "day", {}, [.3, .85]),
    Shot("NS_SoraVFX_Telegraph_Cleave", (V(0, 0, 1), R(0, 0, 0)), (V(-800, 250, 650), V(0, 0, 0)), "day",
         {"ArcDegrees": 360.0}, [.3, .85], tag="Area"),
    Shot("NS_SoraVFX_Water_SluiceRise", (V(0, 0, 1), R(0, 0, 0)), (V(-500, -500, 260), V(100, 0, 20)), "day", {}, [4.0]),
    Shot("NS_SoraVFX_Water_Splash", (V(0, 0, 1), UP), (V(-300, 0, 90), V(0, 0, 40)), "day", {}, [.08, .35, 1.0]),
    # The forge's three gauge states: red heat, yamabuki, white heat.
    Shot("NS_SoraVFX_Forge_Fire", (V(0, 0, 1), R(0, 0, 0)), (V(-300, 0, 120), V(0, 0, 60)), "dusk",
         {"Temperature": 0.0, "Bellows": .3}, [2.0], tag="Red"),
    Shot("NS_SoraVFX_Forge_Fire", (V(0, 0, 1), R(0, 0, 0)), (V(-300, 0, 120), V(0, 0, 60)), "dusk",
         {"Temperature": .5, "Bellows": .6}, [2.0], tag="Yamabuki"),
    Shot("NS_SoraVFX_Forge_Fire", (V(0, 0, 1), R(0, 0, 0)), (V(-300, 0, 120), V(0, 0, 60)), "dusk",
         {"Temperature": 1.0, "Bellows": 1.0}, [2.0], tag="White"),
    Shot("NS_SoraVFX_Steam", (V(0, 0, 1), R(0, 0, 0)), (V(-300, 0, 120), V(0, 0, 90)), "day", {}, [3.0]),
    Shot("NS_SoraVFX_Steam_Burst", (V(0, 0, 1), R(0, 0, 0)), (V(-350, 0, 130), V(0, 0, 100)), "day", {}, [.25, 1.0]),
    Shot("NS_SoraVFX_Rain", (V(0, 0, 1), R(0, 0, 0)), (V(-300, 0, 160), V(300, 0, 120)), "day", {}, [2.5], "render_steps"),
    Shot("NS_SoraVFX_Mist", (V(0, 0, 1), R(0, 0, 0)), (V(-1400, 0, 200), V(0, 0, 100)), "day", {}, [16.0]),
    Shot("NS_SoraVFX_Lantern", (V(0, 0, 150), R(0, 0, 0)), (V(-300, 0, 150), V(0, 0, 120)), "dusk", {}, [1.3]),
]
SWEEP_FRAMES = 8            # the cut takes the last 8 frames (0.13 s) before the capture
FLIGHT_SPEED = 4500.0       # cm/s: a yumi arrow leaves the bow at 45-60 m/s


def place_blade(actor, pivot, t):
    """The blade trail at fraction t of a 100-degree cut about pivot, in the plane facing the camera (world YZ).

    +X is radial, along the blade, as NS_SoraVFX_BladeTrail expects (its ribbon's side vector is the
    component's +X), so the 72 cm sheet spans the edge and is swept across the arc.
    """
    rotation = R(pitch=80.0 - 100.0 * t, yaw=90.0)      # from overhead to just below level, a shomen cut seen side-on
    actor.set_actor_location(pivot + unreal.MathLibrary.get_forward_vector(rotation) * 90.0, False, False)
    actor.set_actor_rotation(rotation, False)


world = None
capture = None
target = None
sun = None
sky = None


def spawn_mesh(mesh, material, location, scale):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, R(0, 0, 0))
    component = actor.static_mesh_component
    component.set_static_mesh(unreal.load_asset(mesh))
    component.set_material(0, unreal.load_asset(material))
    actor.set_actor_scale3d(scale)
    return actor


def build_stage():
    global world, capture, target, sun, sky
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    spawn_mesh("/Engine/BasicShapes/Plane.Plane", "/Game/Generated/Environment/MI_Nyaagyu_Stone.MI_Nyaagyu_Stone",
               V(0, 0, 0), V(60, 60, 1))
    spawn_mesh("/Engine/BasicShapes/Cube.Cube", "/Game/Generated/Environment/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster",
               V(900, 0, 250), V(.4, 30, 5))
    sun = actors.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 500), R(-35, 35, 0))
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_editor_property("intensity", 25.0)
    sun.light_component.set_editor_property("light_color", C(1.0, .96, .9).to_color(True))
    sky = actors.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 300), R(0, 0, 0))
    sky_component = sky.light_component
    sky_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_component.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky_component.set_editor_property("cubemap", unreal.load_asset("/Game/Generated/Environment/Textures/T_NyaagyuOvercast"))
    sky_component.set_editor_property("intensity", .65)
    sky_component.recapture_sky()
    actors.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, 0), R(0, 0, 0))
    target = unreal.RenderingLibrary.create_render_target2d(world, WIDTH, HEIGHT, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    camera = actors.spawn_actor_from_class(unreal.SceneCapture2D, V(-400, 0, 170), R(0, 0, 0))
    capture = camera.capture_component2d
    capture.set_editor_property("texture_target", target)
    capture.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_SCENE_COLOR_HDR)
    capture.set_editor_property("capture_every_frame", False)
    capture.set_editor_property("capture_on_movement", False)
    capture.set_editor_property("fov_angle", 60.0)
    capture.set_editor_property("post_process_blend_weight", 1.0)
    return camera


def set_lighting(mode):
    """Estate overcast day (25 lux sun) or dusk (1.8 lux); a fixed manual exposure keeps pre-exposure constant."""
    day = mode == "day"
    sun.light_component.set_editor_property("intensity", 25.0 if day else 1.8)
    sky.light_component.set_editor_property("intensity", .65 if day else .08)
    sky.light_component.recapture_sky()
    settings = capture.get_editor_property("post_process_settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", 0.0),
                       # Scene captures get no Lumen scene here: light the stage with the classic sky light instead.
                       ("dynamic_global_illumination_method", unreal.DynamicGlobalIlluminationMethod.NONE),
                       ("reflection_method", unreal.ReflectionMethod.SCREEN_SPACE),
                       ("bloom_intensity", .25), ("motion_blur_amount", 0.0)):
        settings.set_editor_property("override_" + key, True)
        settings.set_editor_property(key, value)
    capture.set_editor_property("post_process_settings", settings)


def aim(camera, location, look_at):
    direction = look_at - location
    camera.set_actor_location(location, False, False)
    camera.set_actor_rotation(unreal.MathLibrary.make_rot_from_x(direction), False)


def aim_simulation_viewport(location, look_at):
    """Depth-collision GPU simulations need a main view at the capture's camera."""
    if editor.get_level_viewport_camera_info() is None:
        raise RuntimeError("GPU preview requires a level editor viewport")
    editor.set_level_viewport_camera_info(location, unreal.MathLibrary.make_rot_from_x(look_at - location))
    levels.editor_invalidate_viewports()
    log("GPU simulation uses the main editor viewport at the shot camera")


def floor_median():
    """Median luminance of the floor below the light-check spot (the lantern hangs 150 cm above it)."""
    x0, y0, x1, y1 = int(WIDTH * .44), int(HEIGHT * .70), int(WIDTH * .56), int(HEIGHT * .80)
    pixels = unreal.RenderingLibrary.read_render_target_raw_pixel_area(world, target, x0, y0, x1, y1, False)
    values = sorted(.2126 * p.r + .7152 * p.g + .0722 * p.b for p in pixels)
    if not values:
        raise RuntimeError("the light check read no pixels from the render target")
    return values[len(values) // 2]


def light_check(camera):
    """Yields editor ticks to wait; logs SORA_VFX_LIGHT_CHECK with the three floor medians."""
    set_lighting("dusk")
    aim(camera, V(-300, 0, 170), V(0, 0, 60))
    floor = {}
    for case in ("none", "lantern", "point"):
        actor = None
        if case == "lantern":
            actor = actors.spawn_actor_from_object(unreal.load_asset("/Game/Generated/VFX/NS_SoraVFX_Lantern"), V(0, 0, 150), R())
            actor.niagara_component.activate(True)
            actor.niagara_component.advance_simulation(60, 1 / 60)
        elif case == "point":
            actor = actors.spawn_actor_from_class(unreal.PointLight, V(0, 0, 150), R())
            point = actor.light_component
            point.set_mobility(unreal.ComponentMobility.MOVABLE)
            point.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
            point.set_editor_property("intensity", 150.0)
            point.set_editor_property("attenuation_radius", 420.0)
        yield 30
        capture.capture_scene()
        yield 2
        unreal.RenderingLibrary.export_render_target(world, target, str(OUT), f"LightCheck_{case}.exr")
        floor[case] = floor_median()
        if actor is not None:
            actor.destroy_actor()
        yield 2
    gain_point = floor["point"] - floor["none"]
    gain_lantern = floor["lantern"] - floor["none"]
    ratio = gain_lantern / gain_point if gain_point > 0.0 else 0.0
    passed = gain_point > .5 * floor["none"] and .5 <= ratio <= 2.0
    report = (f"SORA_VFX_LIGHT_CHECK: {'PASS' if passed else 'FAIL'} floor median: bare {floor['none']:.4f}, "
              f"lantern {floor['lantern']:.4f}, 150 lm point light {floor['point']:.4f}; "
              f"lantern gain / point gain {ratio:.2f} (passes at 0.5-2.0)")
    if passed:
        unreal.log(report)
    else:
        unreal.log_error(report)


def apply_user(component, values):
    for key, value in values.items():
        name = "User." + key if not key.startswith("User.") else key
        if isinstance(value, float):
            component.set_variable_float(name, value)
        elif isinstance(value, unreal.Vector):
            component.set_variable_vec3(name, value)
        elif isinstance(value, unreal.LinearColor):
            component.set_variable_linear_color(name, value)


class Runner:
    """Advances through the shots one editor tick at a time (captures need ticks for shaders and readback)."""

    def __init__(self, camera, queue):
        self.camera = camera
        self.queue = queue
        self.index = -1
        self.wait = 0
        self.actor = None
        self.shot = None
        self.ages = []
        self.phase = "warmup"
        self.started = time.time()
        self.warm_actors = []
        self.written = []
        self.light = None
        self.delta = 0.0
        self.render_steps_left = 0
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def finish(self):
        unreal.unregister_slate_post_tick_callback(self.handle)
        log(f"wrote {len(self.written)} stills to {OUT}")
        unreal.log(f"SORA_VFX_PREVIEW_DONE: {len(self.written)}")
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def tick(self, delta):
        self.delta = delta
        try:
            self._tick()
        except Exception as error:          # noqa: BLE001 - report and stop instead of hanging the editor
            unreal.log_error(f"SORA_VFX_PREVIEW_ERROR: {error}")
            self.finish()

    def _tick(self):
        if self.wait > 0:
            self.wait -= 1
            return
        if self.phase == "warmup":
            # Spawn every system once and render it so its shaders compile, then let the compile queue drain.
            for name in sorted({shot.name for shot in self.queue}):
                system = unreal.load_asset(f"/Game/Generated/VFX/{name}")
                actor = actors.spawn_actor_from_object(system, V(0, 0, 100), R(0, 0, 0))
                actor.niagara_component.advance_simulation(20, 1 / 60)
                self.warm_actors.append(actor)
            set_lighting("day")
            capture.capture_scene()
            self.phase = "drain"
            self.wait = 90
            return
        if self.phase == "drain":
            capture.capture_scene()
            if time.time() - self.started < float(os.environ.get("SORA_VFX_PREVIEW_WARMUP_SECONDS", "150")):
                self.wait = 30
                return
            for actor in self.warm_actors:
                actor.destroy_actor()
            self.phase = "next"
            return
        if self.phase == "next":
            if self.actor is not None:
                self.actor.destroy_actor()
                self.actor = None
            self.index += 1
            if self.index >= len(self.queue):
                self.light = light_check(self.camera)
                self.phase = "light"
                return
            self.shot = shot = self.queue[self.index]
            set_lighting(shot.mode)
            aim(self.camera, *shot.camera)
            system = unreal.load_asset(f"/Game/Generated/VFX/{shot.name}")
            self.actor = actors.spawn_actor_from_object(system, *shot.placement)
            component = self.actor.niagara_component
            if shot.motion == "render_steps":
                aim_simulation_viewport(*shot.camera)
                component.set_force_solo(True)
            apply_user(component, shot.user)
            self.ages = list(shot.ages)
            # A system's first activation can wait on pipeline precaching; run it once and throw that away.
            component.activate(True)
            if shot.motion == "render_steps":
                component.set_component_tick_enabled(False)
            component.advance_simulation(30, 1 / 60)
            self.phase = "age"
            self.wait = 30
            return
        if self.phase == "age":
            # Reset and let the component register a fresh instance before stepping it.
            component = self.actor.niagara_component
            component.set_paused(False)
            apply_user(component, self.shot.user)
            if self.shot.motion == "sweep":
                place_blade(self.actor, self.shot.placement[0], 0.0)    # start the trail at the top of the cut
            elif self.shot.motion == "flight":
                self.actor.set_actor_location(self.shot.placement[0], False, False)
            component.activate(True)
            if self.shot.motion == "render_steps":
                component.set_component_tick_enabled(False)
            component.set_paused(True)
            self.phase = "advance"
            self.wait = 3
            return
        if self.phase == "advance":
            shot = self.shot
            component = self.actor.niagara_component
            age = self.ages.pop(0)
            self.pending = still_name(shot, age)
            component.set_paused(False)
            if shot.motion == "render_steps":
                component.set_component_tick_enabled(False)
                self.render_steps_left = max(1, int(round(age * 60)))
                self.phase = "render_steps"
                return
            steps = max(1, int(round(age * 60)))
            if shot.motion == "flight":
                start, rotation = shot.placement
                heading = unreal.MathLibrary.get_forward_vector(rotation)
                for step in range(steps):
                    self.actor.set_actor_location(start + heading * (FLIGHT_SPEED * (step + 1) / 60.0), False, False)
                    component.advance_simulation(1, 1 / 60)
            elif shot.motion == "sweep":
                # the whole cut in the last frames before the capture (all of them when the age is shorter)
                frames = min(SWEEP_FRAMES, steps)
                for step in range(steps):
                    if step >= steps - frames:
                        place_blade(self.actor, shot.placement[0], (step - (steps - frames) + 1) / frames)
                    component.advance_simulation(1, 1 / 60)
            else:
                component.advance_simulation(steps, 1 / 60)
            component.set_paused(True)
            self.phase = "capture"
            self.wait = 2
            return
        if self.phase == "render_steps":
            # SceneView::AllowGPUParticleUpdate excludes scene captures. Let a
            # main viewport draw consume this tick, including scene depth.
            self.actor.niagara_component.advance_simulation(1, 1 / 60)
            levels.editor_invalidate_viewports()
            self.render_steps_left -= 1
            self.wait = 1
            if self.render_steps_left <= 0:
                self.phase = "render_flush"
                self.wait = 2
            return
        if self.phase == "render_flush":
            self.actor.niagara_component.set_paused(True)
            self.phase = "capture"
            self.wait = 2
            return
        if self.phase == "capture":
            capture.capture_scene()
            self.phase = "export"
            self.wait = 2
            return
        if self.phase == "export":
            unreal.RenderingLibrary.export_render_target(world, target, str(OUT), self.pending + ".exr")
            self.written.append(self.pending)
            log(f"captured {self.pending}")
            self.phase = "age" if self.ages else "next"
            self.wait = 1
            return
        if self.phase == "light":
            try:
                self.wait = next(self.light)
            except StopIteration:
                self.finish()
            return


def shot_queue():
    """The shots to render; two stills that would share a file name are an error."""
    queue = [shot for shot in SHOTS if not ONLY or shot.name in ONLY]
    names = [still_name(shot, age) for shot in queue for age in shot.ages]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise RuntimeError(f"stills would overwrite each other (give the shots a tag): {repeated}")
    return queue


QUEUE = shot_queue()        # before the script is kept alive, so a bad table stops it at once
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
runner = Runner(build_stage(), QUEUE)
