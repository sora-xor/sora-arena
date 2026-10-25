"""First-person review originals of the skeletal yumi, its arrow and the bow paw, in Unreal.

Run in the pinned editor with a renderer, after import_runtime_weapon_yumi_rig.py
(and import_nyaakoto_fp_paws.py, unless paws=0):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_yumi_fp_review.py \
      YUMI_FP_REVIEW_COMPLETE -- holds=rest,root,kai res=1920x1080 out=YumiFP

It builds a fresh uncooked level, /Game/ArtReview/YumiFP/L_YumiFP_<time>.
- **The camera:** at the origin, looking down +X, the eye of the first-person
  frame (viewmodels.json "frame": X forward, Y right, Z up, centimetres),
  at the contract's 70 degree first-person FOV, 16:9.
- **The bow:** SK_Weapon_18, hung from its Grip_L socket at the hold's
  anchor_cm, turned by its rotation_deg (FRotator pitch, yaw, roll) and
  scaled 0.75 (mesh_scale), as the native presentation places a weapon. Its
  take A_Weapon_18_Draw is held at the hold's draw fraction (time in seconds
  = draw fraction).
- **The arrow:** SM_Weapon_18_Ya, nocked at the posed Grip_R and laid
  through the posed Muzzle (the arrow pass).
- **The paw:** SM_NyaakotoFP_PawL_Yumi, attached to the posed Grip_L.
- **The holds:**
  - rest: the bow rest pose, braced;
  - root: root's bow.drawn hold (60, -3, -9.5), at full draw;
  - kai: the proposed kai hold (60, -6, -14), at full draw;
  - paw: a closer three-quarter view of the paw on the grip.
- **The setting:** a plain review set (a floor slab and a far wall, open to
  the sky) under a physically based SkyAtmosphere sun 50 degrees up behind
  thin haze, over the left shoulder, with its real-time sky light. Exposure is
  fixed and manual, metered from the sun: EV100 = log2(E / 2.5), the
  incident-meter equation (calibration constant 250, ISO 100), under the
  look-development convention auto_exposure_bias = 1 - EV100
  (render_sora_lookdev.py).
- **The material gate:** the bow and the arrow must draw their W18 instances,
  and the paw only its own materials, as the components resolve them.
- **The pose gate:** the take is evaluated on the game thread
  (OverrideAnimationData ticks and refreshes the bones), and the posed Grip_R
  and Muzzle, in component space, must match the Blender review's
  (W18_rig_review_arrow.json) within test_yumi_draw's compressed head bound,
  plus Grip_R's own offset from String_Nock and the review's rounding;
  otherwise the run fails before any capture.

Captures go to Saved/YumiFP/<out>/<hold>.png, with a manifest.json of every
file's SHA-256 and the socket positions read from the posed mesh.

Editor review originals: not the native first-person renderer (no
first-person FOV/scale split, no gameplay aim), and not an admission.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Yumi first-person review")
ROOT = Path(unreal.Paths.project_dir()).resolve()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
RIG = "/Game/Generated/Qualification/W18YumiRig"
RIG_REVIEW = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/Review"
PAWS = "/Game/Generated/Qualification/NyaakotoFPPaws"
LEVEL = f"/Game/ArtReview/YumiFP/L_YumiFP_{int(time.time())}"
VIEWMODELS = json.loads((ROOT / "Content/Data/viewmodels.json").read_text(encoding="utf-8"))
MESH_SCALE = VIEWMODELS["mesh_scale"]
FOV = VIEWMODELS["camera"]["first_person_fov_deg"]
# The sun: 20,000 lux at 50 degrees up, behind thin haze (the look-development
# overcast rig's sun, render_sora_lookdev.py), turned to come over the left
# shoulder (yaw 20: travelling toward +X, slightly right).
SUN = {"pitch": -50.0, "yaw": 20.0, "lux": 20000.0, "kelvin": 6500.0, "mie": 6.0, "fog": 0.03}
# The posed sockets' bound, centimetres. test_yumi_draw.UNREAL_COMPRESSED_TOL[0]:
# Blender's playback bound (1e-5 m), ACL's head bound at its inferred default
# threshold (2 x 0.01 cm) and the reference snap (sqrt(3) x 1e-4 cm).
HEAD_TOL_CM = 100.0 * 1e-5 + 2.0 * 0.01 + math.sqrt(3.0) * 1e-4
# The review JSON's positions are rounded to 1e-7 m: at most sqrt(3) x 0.5e-5 cm.
REVIEW_ROUNDING_CM = math.sqrt(3.0) * 0.5e-5
HOLDS = {
    "rest": {"anchor": VIEWMODELS["poses"]["bow"]["rest"]["anchor_cm"],
             "rot": VIEWMODELS["poses"]["bow"]["rest"]["rotation_deg"], "draw": 0.0},
    "root": {"anchor": [60.0, -3.0, -9.5], "rot": [0.25, 0.1, 0.0], "draw": 1.0},
    "kai": {"anchor": [60.0, -6.0, -14.0], "rot": [0.25, 0.1, 0.0], "draw": 1.0},
    "paw": {"anchor": [60.0, -3.0, -9.5], "rot": [0.25, 0.1, 0.0], "draw": 1.0,
            "camera": {"loc": [36.0, -10.0, -2.0], "look_at": [60.0, -3.0, -9.5], "fov": 32.0}},
}


def parse_args():
    opts = {"holds": "rest,root,kai,paw", "res": "1920x1080", "out": "YumiFP", "paws": "1", "ev": ""}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            opts[k] = v
    return opts


def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        raise RuntimeError(f"yumi FP review: missing asset {path}")
    return asset


def spawn(cls, loc=(0.0, 0.0, 0.0), rot=None):
    r = rot if rot is not None else unreal.Rotator(0.0, 0.0, 0.0)
    return ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), r)


def frotator(pitch_yaw_roll):
    pitch, yaw, roll = pitch_yaw_roll
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def world():
    """The editor world, as the console commands' context."""
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_level():
    ASSETS.make_directory(LEVEL.rsplit("/", 1)[0])
    if not LEVELS.new_level(LEVEL):
        raise RuntimeError("yumi FP review: could not create the level")
    # Closed slabs, not one-sided planes, so no face can turn away from the
    # camera: the floor's top at -160 cm (the eye 1.6 m up), the far wall's
    # face at x = 1,190 cm, filling the frame behind the bow.
    cube = load("/Engine/BasicShapes/Cube.Cube")
    for loc, scale in (((500.0, 0.0, -165.0), (24.0, 24.0, 0.1)),                 # floor
                       ((1200.0, 0.0, 340.0), (0.2, 30.0, 10.0))):                # far wall
        a = spawn(unreal.StaticMeshActor, loc)
        a.static_mesh_component.set_static_mesh(cube)
        a.set_actor_scale3d(unreal.Vector(*scale))
    atmosphere = spawn(unreal.SkyAtmosphere)
    atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent).set_editor_property(
        "mie_scattering_scale", SUN["mie"])
    sun = spawn(unreal.DirectionalLight, (0.0, 0.0, 500.0), unreal.Rotator(roll=0.0, pitch=SUN["pitch"], yaw=SUN["yaw"]))
    lc = sun.light_component
    lc.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(SUN["lux"])
    lc.set_use_temperature(True)
    lc.set_temperature(SUN["kelvin"])
    lc.set_editor_property("atmosphere_sun_light", True)
    lc.set_editor_property("light_source_angle", 0.53)
    sky = spawn(unreal.SkyLight, (0.0, 0.0, 300.0))
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property("real_time_capture", True)
    sky.light_component.set_intensity(1.0)
    fog = spawn(unreal.ExponentialHeightFog)
    fog.component.set_fog_density(SUN["fog"])
    unreal.SystemLibrary.execute_console_command(world(), "r.TextureStreaming 0")


def metered_ev100():
    """The incident-meter exposure for the sun: EV100 = log2(E / 2.5)."""
    return math.log2(SUN["lux"] / 2.5)


def exposure(ev100):
    volume = spawn(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    s = volume.get_editor_property("settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", -ev100 + 1.0)):
        s.set_editor_property(f"override_{key}", True)
        s.set_editor_property(key, value)
    volume.set_editor_property("settings", s)


class Viewmodel:
    def __init__(self, with_paws):
        self.mesh = load(f"{RIG}/SK_Weapon_18")
        self.anim = load(f"{RIG}/A_Weapon_18_Draw")
        review = json.loads((RIG_REVIEW / "W18_rig_review_arrow.json").read_text(encoding="utf-8"))
        self.expected = {float(st["frame"]) / 10.0: st for st in review["states"].values()}
        readback = json.loads((RIG_REVIEW / "W18_rig_unreal_readback.json").read_text(encoding="utf-8"))
        offset = readback["sockets"]["Grip_R"]["relative_location_cm"]          # Grip_R on String_Nock
        self.tol_cm = HEAD_TOL_CM + math.sqrt(sum(v * v for v in offset)) + REVIEW_ROUNDING_CM
        self.bow = spawn(unreal.SkeletalMeshActor)
        comp = self.bow.skeletal_mesh_component
        if hasattr(comp, "set_skeletal_mesh_asset"):
            comp.set_skeletal_mesh_asset(self.mesh)
        else:
            comp.set_skeletal_mesh(self.mesh)
        # The property is not editable from Python here ("cannot be edited on
        # templates", capture attempt 0); its UFUNCTION setter is.
        comp.set_update_animation_in_editor(True)
        # From the component's default mode this changes the mode, so the
        # single-node instance is created from this animation data (capture
        # attempt 1: set_animation and set_position alone left the braced pose).
        comp.override_animation_data(self.anim, False, False, 0.0, 0.0)
        self.comp = comp
        self.arrow = spawn(unreal.StaticMeshActor)
        self.arrow.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        self.arrow.static_mesh_component.set_static_mesh(load(f"{RIG}/SM_Weapon_18_Ya"))
        self.paw = None
        if with_paws:
            self.paw = spawn(unreal.StaticMeshActor)
            pc = self.paw.static_mesh_component
            # A static component cannot attach to the movable bow (capture
            # attempt 1, AttachTo warning): the paw stayed at the origin.
            pc.set_mobility(unreal.ComponentMobility.MOVABLE)
            pc.set_static_mesh(load(f"{PAWS}/SM_NyaakotoFP_PawL_Yumi"))
            self.paw.attach_to_component(comp, "Grip_L", unreal.AttachmentRule.SNAP_TO_TARGET,
                                         unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD,
                                         False)
            if self.paw.get_attach_parent_actor() != self.bow or str(self.paw.get_attach_parent_socket_name()) != "Grip_L":
                raise RuntimeError("yumi FP review: the paw did not attach to Grip_L")
        # What each part draws with, as the components resolve it, before any shot:
        # attempt 2 drew the bow in /Engine/EngineMaterials/WorldGridMaterial, its
        # imported slot (import_runtime_weapon_yumi_rig.py: SetMaterials).
        self.materials = {"bow": [m.get_path_name() for m in comp.get_materials()],
                          "arrow": [m.get_path_name() for m in self.arrow.static_mesh_component.get_materials()]}
        if self.paw is not None:
            self.materials["paw"] = [m.get_path_name() for m in self.paw.static_mesh_component.get_materials()]
        want = {"bow": {f"{RIG}/MI_W18_Weapon.MI_W18_Weapon"}, "arrow": {f"{RIG}/MI_W18_Hane.MI_W18_Hane"}}
        for part, paths in want.items():
            if set(self.materials[part]) != paths:
                raise RuntimeError(f"yumi FP review: the {part} draws {self.materials[part]}, not {sorted(paths)}")
        if self.paw is not None and not all(m.startswith(f"{PAWS}/M_NyaakotoFP_") for m in self.materials["paw"]):
            raise RuntimeError(f"yumi FP review: the paw draws {self.materials['paw']}")

    def pose(self, hold):
        """Hang the bow from Grip_L at the anchor, and hold the take at the draw fraction."""
        h = HOLDS[hold]
        self.bow.set_actor_scale3d(unreal.Vector(MESH_SCALE, MESH_SCALE, MESH_SCALE))
        self.bow.set_actor_rotation(frotator(h["rot"]), False)
        # Grip_L sits at the mesh origin on the identity Grip root, so the actor
        # origin is the anchor (the runtime recentres on the socket the same way).
        self.bow.set_actor_location(unreal.Vector(*h["anchor"]), False, False)
        # The mode is single-node now, so OverrideAnimationData no longer
        # reinitializes: set the instance's time, then let it tick and refresh
        # the bones on the game thread at that time.
        self.comp.set_position(h["draw"], False)
        self.comp.override_animation_data(self.anim, False, False, h["draw"], 0.0)
        if self.paw is not None:
            self.paw.set_actor_scale3d(unreal.Vector(MESH_SCALE, MESH_SCALE, MESH_SCALE))

    def check_pose(self, hold):
        """The posed sockets against the Blender review's, in component space; raises if off."""
        draw = HOLDS[hold]["draw"]
        want = self.expected.get(draw)
        if want is None:
            raise RuntimeError(f"yumi FP review: the review has no state at draw {draw}")
        rows = {}
        for name, key in (("Grip_R", "nock_m"), ("Muzzle", "muzzle_m")):
            t = self.comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
            x, y, z = want[key]
            e = (100.0 * x, -100.0 * y, 100.0 * z)
            err = math.sqrt((t.x - e[0]) ** 2 + (t.y - e[1]) ** 2 + (t.z - e[2]) ** 2)
            rows[name] = {"component_cm": [t.x, t.y, t.z], "expected_cm": list(e), "error_cm": err}
            if err > self.tol_cm:
                raise RuntimeError(f"yumi FP review: {hold} {name} is {err:.5f} cm from the review's "
                                   f"draw {draw} (bound {self.tol_cm:.5f} cm): the take was not posed")
        if self.paw is not None:
            g = self.comp.get_socket_location("Grip_L")
            p = self.paw.get_actor_location()
            rows["paw_to_Grip_L_cm"] = math.sqrt((g.x - p.x) ** 2 + (g.y - p.y) ** 2 + (g.z - p.z) ** 2)
            if rows["paw_to_Grip_L_cm"] > 1e-3:
                raise RuntimeError(f"yumi FP review: the paw is {rows['paw_to_Grip_L_cm']:.4f} cm off Grip_L")
        rows["bound_cm"] = self.tol_cm
        return rows

    def nock_arrow(self):
        nock = self.comp.get_socket_location("Grip_R")
        rest = self.comp.get_socket_location("Muzzle")
        d = rest - nock
        rot = unreal.MathLibrary.make_rot_from_x(d)
        self.arrow.set_actor_location(nock, False, False)
        self.arrow.set_actor_rotation(rot, False)
        self.arrow.set_actor_scale3d(unreal.Vector(MESH_SCALE, MESH_SCALE, MESH_SCALE))
        return {"Grip_R": [nock.x, nock.y, nock.z], "Muzzle": [rest.x, rest.y, rest.z],
                "Grip_L": [g.x, g.y, g.z] if (g := self.comp.get_socket_location("Grip_L")) else None}


def camera_for(hold, width, height):
    h = HOLDS[hold].get("camera")
    loc = (0.0, 0.0, 0.0) if h is None else tuple(h["loc"])
    if h is None:
        rot = unreal.Rotator(0.0, 0.0, 0.0)
    else:
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*h["look_at"]))
    cam = spawn(unreal.CameraActor, loc, rot)
    cc = cam.camera_component
    cc.set_editor_property("field_of_view", FOV if h is None else h["fov"])
    cc.set_editor_property("aspect_ratio", width / height)
    cc.set_editor_property("constrain_aspect_ratio", True)
    return cam


def main():
    opts = parse_args()
    holds = [h for h in opts["holds"].split(",") if h]
    width, height = (int(x) for x in opts["res"].split("x"))
    out = ROOT / "Saved/YumiFP" / opts["out"]
    out.mkdir(parents=True, exist_ok=True)
    build_level()
    ev100 = float(opts["ev"]) if opts["ev"] else metered_ev100()
    exposure(ev100)
    vm = Viewmodel(opts["paws"] != "0")
    status = {"frames": 0, "queue": list(holds), "phase": "pose", "wait": 0, "written": [], "sockets": {}, "poses": {}}

    def finish(message, error=False):
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()

    def tick(delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            finish(f"YUMI_FP_REVIEW_FAILED: {exc!r}", error=True)

    def step():
        status["frames"] += 1
        LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        if status["phase"] == "pose":
            if not status["queue"]:
                manifest = {"level": LEVEL, "fov": FOV, "mesh_scale": MESH_SCALE, "holds": {h: HOLDS[h] for h in holds},
                            "files": {p: sha256(out / p) for p in status["written"]}, "sockets_cm": status["sockets"],
                            "poses_component_cm": status["poses"], "materials": vm.materials, "sun": SUN,
                            "ev100": ev100,
                            "exposure_bias": 1.0 - ev100,
                            "scope": "editor review originals: not the native first-person renderer or an admission"}
                (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
                finish(f"YUMI_FP_REVIEW_COMPLETE: {len(status['written'])} captures in {out}")
                return
            hold = status["queue"][0]
            vm.pose(hold)
            status.update(phase="settle", count=0, hold=hold)
            return
        if status["phase"] == "settle":
            status["count"] += 1
            if status["count"] < 20:
                return
            status["poses"][status["hold"]] = vm.check_pose(status["hold"])
            status["sockets"][status["hold"]] = vm.nock_arrow()
            cam = camera_for(status["hold"], width, height)
            LEVELS.pilot_level_actor(cam)
            LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, cam=cam)
            return
        if status["phase"] == "light":
            status["count"] += 1
            if status["count"] < 150:                                  # Lumen, TSR and exposure settle
                return
            path = out / f"{status['hold']}.png"
            status.update(phase="shot", current=path, started=time.time(), count=0)
            unreal.SystemLibrary.execute_console_command(world(), f'HighResShot {width}x{height} filename="{path}"')
            return
        if status["phase"] == "shot":
            p = status["current"]
            if not p.is_file() or p.stat().st_mtime < status["started"]:
                status["count"] += 1
                if status["count"] > 4000:
                    finish(f"YUMI_FP_REVIEW_FAILED: {p} was not written", error=True)
                return
            status["written"].append(p.name)
            ACTORS.destroy_actor(status["cam"])
            status["queue"].pop(0)
            status["phase"] = "pose"

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


main()
