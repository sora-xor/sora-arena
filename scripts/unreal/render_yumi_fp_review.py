"""First-person review originals of the skeletal yumi, its arrow and the bow paw, in Unreal.

Run in the pinned editor with a renderer, after import_runtime_weapon_yumi_rig.py
(and import_nyaakoto_fp_paws.py, unless paws=0):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_yumi_fp_review.py \
      YUMI_FP_REVIEW_COMPLETE -- holds=rest,root,right_cheek,paw res=1920x1080 out=YumiFP [ids=0] [runup=auto|<n>]

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
- **The holds** (docs/art-direction/data/yumi_fp_hold_study.json; root's
  viewmodels.json is unchanged):
  - rest: the bow rest pose, braced;
  - root: root's bow.drawn hold (60, -3, -9.5), at full draw: the control;
  - right_cheek: Codex's construction (yumi_fp_holds.right_cheek), solved
    here from the full-draw Grip_R and Muzzle this mesh actually poses, so
    rebuilt sockets get their own hold. It keeps the control's nock X and Z,
    mirrors its Y, and turns the bow so the arrow line passes through
    (2000, 0, 0). The manifest records the solve and its difference from
    Codex's candidate.
  - right_cheek_clear: the study's clear-reticle candidate, right_cheek's
    construction with its nock target 6.0 cm right of the eye
    (yumi_fp_holds.cheek_hold; YUMI_FP_RETICLE_STUDY.md), solved the same way.
    It is not in the default holds.
  - paw: a closer three-quarter view of the paw on the grip.
  (The earlier proposed "kai", Y -6, moves farther left: it is not a
  right-cheek fix, and is dropped.)
- **The setting:** a plain review set (a dark polished floor slab and a
  plaster far wall in constant albedo, the timber look-dev stage's, open to
  the sky) under a physically based SkyAtmosphere sun 50 degrees up behind
  thin haze, over the left shoulder, with its real-time sky light. Exposure is
  fixed and manual, metered from the sun: EV100 = log2(E / 2.5), the
  incident-meter equation (calibration constant 250, ISO 100), under the
  look-development convention auto_exposure_bias = 1 - EV100
  (render_sora_lookdev.py).
- **The material gate:** fp_material_bindings.check, the same rows and
  serialized expectations as verify_yumi_rig_materials.py. Each part's slots
  must be exactly the expected names, each bound to its material, and each
  component index must draw its asset's slot at that index.
- **The pose gate:** the take is evaluated on the game thread
  (OverrideAnimationData ticks and refreshes the bones), and the posed Grip_R
  and Muzzle, in component space, must match the Blender review's
  (W18_rig_review_arrow.json) within test_yumi_draw's compressed head bound,
  plus Grip_R's own offset from String_Nock and the review's rounding;
  otherwise the run fails before any capture.
- **The solve gate** (right_cheek): the posed nock must sit on its target and
  the posed arrow line pass through the aim point, within SOLVE_TOL_CM.
- **Socket assessment**, recorded per eye-view hold and never a gate:
  - each socket's screen point against root's left-side boxes (which the
    candidate's grip is not expected to satisfy; they are not relaxed);
  - the clear line's distance from the reticle;
  - the posed arrow's miss at 20 m;
  - how much of the arrow lies nearer than the 10 cm near plane;
  - each part's nearest extent.
- **The ID pass** (unless ids=0), after each eye-view shot:
  - each part is drawn in an unlit colour (bow red, arrow green, paw blue),
    the fur cards and W18 islands keeping their alpha masks;
  - the set, sky and lights are hidden, the exposure is 1, with no bloom;
  - this is <hold>_ids.png, so analyse_yumi_fp_review.py can count each
    part's real pixels and reticle occlusion;
  - then each part returns to its own slots, and the material gate runs
    again before the next hold.

Captures go to Saved/YumiFP/<out>/<hold>.png (and <hold>_ids.png), with a
manifest.json of every file's SHA-256, the socket positions read from the
posed mesh, the solves and the assessments.

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
import fp_material_bindings as B  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "art"))
import yumi_fp_holds as H  # noqa: E402
ROOT = Path(unreal.Paths.project_dir()).resolve()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
RIG = "/Game/Generated/Qualification/W18YumiRig"
RIG_REVIEW = ROOT / "Content/SourceArt/Weapons/Runtime/W18_Yumi/Rig/Review"
PAWS = "/Game/Generated/Qualification/NyaakotoFPPaws"
LEVEL = f"/Game/ArtReview/YumiFP/L_YumiFP_{int(time.time())}"
VIEWMODELS = json.loads((ROOT / "Content/Data/viewmodels.json").read_text(encoding="utf-8"))
# Root's control hold and Codex's right_cheek candidate, with their sources' hashes
# (root's viewmodels.json stays unchanged; yumi_fp_holds solves right_cheek here).
STUDY_PATH = "docs/art-direction/data/yumi_fp_hold_study.json"
STUDY_BYTES = (ROOT / STUDY_PATH).read_bytes()          # hashed as read: the manifest pins exactly these
STUDY = json.loads(STUDY_BYTES.decode("utf-8"))
CONTROL = STUDY["root_control"]
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
    # Root's bow.drawn hold, the control (root viewmodels.json, pinned in the study).
    "root": {"anchor": list(CONTROL["anchor_cm"]), "rot": list(CONTROL["rotation_deg"]), "draw": 1.0},
    # Solved from the posed full-draw sockets at capture time (yumi_fp_holds.right_cheek).
    "right_cheek": {"solve": "right_cheek", "draw": 1.0},
    # The study's clear-reticle candidate: right_cheek's construction with its own nock target and cant
    # (yumi_fp_holds.cheek_hold), also solved from the posed sockets.
    "right_cheek_clear": {"solve": "cheek", "draw": 1.0},
    "paw": {"anchor": list(CONTROL["anchor_cm"]), "rot": list(CONTROL["rotation_deg"]), "draw": 1.0,
            "camera": {"loc": [36.0, -10.0, -2.0], "look_at": list(CONTROL["anchor_cm"]), "fov": 32.0}},
}
# The ID-colour pass after each eye-view shot: unlit, so it counts each part's real pixels.
ID_COLOURS = {"bow": (1.0, 0.0, 0.0), "arrow": (0.0, 1.0, 0.0), "paw": (0.0, 0.0, 1.0)}
# The solved hold must put the nock on its target and the arrow through the aim point within
# this (cm): float32 transforms over the 20 m line, with margin.
SOLVE_TOL_CM = 1e-2


def parse_args():
    opts = {"holds": "rest,root,right_cheek,paw", "res": "1920x1080", "out": "YumiFP", "paws": "1", "ev": "",
            "ids": "1", "runup": "auto"}
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


def imported_assets():
    """Every file of the imported namespaces the capture draws, the W18 rig's and the paws', by SHA-256.

    This is what the parts actually were. Their material paths alone cannot show it: root's review of capture v6
    found the run-up comparison accepting v5 and v6, whose paw bytes differ, because their setups and paths
    matched."""
    out = {}
    for ns in (RIG, PAWS):
        folder = ROOT / "Content" / ns[len("/Game/"):]
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                out[p.relative_to(ROOT).as_posix()] = sha256(p)
    return out


def plain_material(name, colour, rough):
    """A constant-albedo review material in the level's folder, rebuilt each run."""
    folder = LEVEL.rsplit("/", 1)[0]
    path = f"{folder}/{name}"
    lib = unreal.MaterialEditingLibrary
    if ASSETS.does_asset_exist(path):
        m = unreal.load_asset(path)
        for e in list(lib.get_material_expressions(m)):
            lib.delete_material_expression(m, e)
    else:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material,
                                                                    unreal.MaterialFactoryNew())
    c = lib.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(*colour, 1.0))
    lib.connect_material_property(c, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = lib.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
    r.set_editor_property("r", rough)
    lib.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


def id_material(name, colour, mask=None, clip=0.5, two_sided=False, dither=False):
    """An unlit review material of one emissive colour; masked by ``mask``'s alpha, as the part it stands in for."""
    folder = LEVEL.rsplit("/", 1)[0]
    path = f"{folder}/{name}"
    lib = unreal.MaterialEditingLibrary
    if ASSETS.does_asset_exist(path):
        m = unreal.load_asset(path)
        for e in list(lib.get_material_expressions(m)):
            lib.delete_material_expression(m, e)
    else:
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Material,
                                                                    unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", two_sided)
    m.set_editor_property("used_with_skeletal_mesh", True)
    c = lib.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property("constant", unreal.LinearColor(*colour, 1.0))
    lib.connect_material_property(c, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if mask is not None:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        m.set_editor_property("opacity_mask_clip_value", clip)
        m.set_editor_property("dither_opacity_mask", dither)
        t = lib.create_material_expression(m, unreal.MaterialExpressionTextureSample, -600, 200)
        t.set_editor_property("texture", load(mask))
        lib.connect_material_property(t, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.recompile_material(m)
    ASSETS.save_loaded_asset(m)
    return m


# The timber look-dev stage's floor and plaster (sora_timber_lookdev.stage), so
# the backdrop is plain and not BasicShapeMaterial's grid (root's review of
# Saved/YumiFP/v2: "background/surfaces also show grain").
SET_MATERIALS = {"floor": ("M_YumiFP_Floor", (0.09, 0.055, 0.035), 0.22),
                 "wall": ("M_YumiFP_Plaster", (0.50, 0.44, 0.35), 0.85)}


def build_level():
    ASSETS.make_directory(LEVEL.rsplit("/", 1)[0])
    if not LEVELS.new_level(LEVEL):
        raise RuntimeError("yumi FP review: could not create the level")
    # Closed slabs, not one-sided planes, so no face can turn away from the
    # camera: the floor's top at -160 cm (the eye 1.6 m up), the far wall's
    # face at x = 1,190 cm, filling the frame behind the bow.
    cube = load("/Engine/BasicShapes/Cube.Cube")
    mats = {k: plain_material(*v) for k, v in SET_MATERIALS.items()}
    env = []
    for part, loc, scale in (("floor", (500.0, 0.0, -165.0), (24.0, 24.0, 0.1)),
                             ("wall", (1200.0, 0.0, 340.0), (0.2, 30.0, 10.0))):
        a = spawn(unreal.StaticMeshActor, loc)
        env.append(a)
        a.static_mesh_component.set_static_mesh(cube)
        a.static_mesh_component.set_material(0, mats[part])
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
    return env + [atmosphere, sun, sky, fog]


def metered_ev100():
    """The incident-meter exposure for the sun: EV100 = log2(E / 2.5)."""
    return math.log2(SUN["lux"] / 2.5)


# Run-up frames HighResShot renders per TSR history sample, before it saves.
RUNUP_PER_HISTORY_SAMPLE = 2


def highres_runup(option="auto"):
    """Set how many frames HighResShot renders at the shot's own size before saving (r.HighResScreenshotDelay).

    HighResShot draws into its own viewport at the requested size, and only for r.HighResScreenshotDelay frames,
    "to allow temporal effects to converge" (UnrealClient.cpp:1685-1714; default 4). The viewport's settle frames
    don't carry over: TSR's history restarts at the new size. TSR keeps at most r.TSR.History.SampleCount samples
    per pixel (default 16, at most 32; TemporalSuperResolution.cpp:44-50).

    **The candidate it was set for, tested in capture v4 and not supported in that pair.** Dithered coverage needs
    that history to resolve, and the fur cards' DitherOpacityMask and the ID pass's dithered fur mask both use it.
    Four frames could have left it raw, which would have explained capture v3's white speckle: its fur's
    high-frequency residual is 4.1 to 4.6 times the urushi stave's in the eye-view holds
    (scripts/art/fur_capture_noise.py).
    - Capture v4 shot the same five holds twice, nothing changed but this run-up: runup=4 (v3's condition) and
      runup=auto (32 frames; Saved/YumiFP/v4_runup_4 and v4_runup_auto).
    - On each hold's common fur region, the residual changed by -2.4 % to +1.3 %, and it stays about four times
      the stave's (Saved/W18Rebuild/s18_fur_compare_v4.json). So the longer run-up did not resolve the speckle.
    - That pair does not rule out temporal-history causes in general.
    - The fur cards' own geometry and material (flat, overlapping blades at macro range) are a separate defect,
      which no run-up changes.

    runup=auto: two frames per history sample, to fill it with margin. runup=<n>: exactly n frames (4 is the
    engine's default, v3's condition). The values set are read back, or the capture refuses."""
    samples = unreal.SystemLibrary.get_console_variable_float_value("r.TSR.History.SampleCount")
    if not samples >= 8.0:                     # 0 means the variable was not found; TSR's own minimum is 8
        raise RuntimeError(f"yumi FP review: r.TSR.History.SampleCount reads {samples!r}")
    if option == "auto":
        frames = int(math.ceil(RUNUP_PER_HISTORY_SAMPLE * samples))
    elif option.isdigit() and int(option) >= 1:
        frames = int(option)
    else:
        raise RuntimeError(f"yumi FP review: runup={option!r} is not auto or a positive frame count")
    unreal.SystemLibrary.execute_console_command(world(), f"r.HighResScreenshotDelay {frames}")
    got = unreal.SystemLibrary.get_console_variable_int_value("r.HighResScreenshotDelay")
    if got != frames:
        raise RuntimeError(f"yumi FP review: r.HighResScreenshotDelay reads {got}, not the {frames} set")
    return {"option": option, "r.TSR.History.SampleCount": samples, "r.HighResScreenshotDelay": frames,
            "per_history_sample": RUNUP_PER_HISTORY_SAMPLE if option == "auto" else None}


def exposure(ev100, volume=None, ids=False):
    """The fixed manual exposure (bias 1 - EV100). For the ID pass: bias 0, so an emissive of 1 is 1, and
    no bloom or vignette to bleed one part's colour into another's pixels."""
    if volume is None:
        volume = spawn(unreal.PostProcessVolume)
        volume.set_editor_property("unbound", True)
    s = volume.get_editor_property("settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", 0.0 if ids else -ev100 + 1.0),
                       ("bloom_intensity", 0.0 if ids else 0.675),
                       ("vignette_intensity", 0.0 if ids else 0.4)):
        s.set_editor_property(f"override_{key}", True)
        s.set_editor_property(key, value)
    volume.set_editor_property("settings", s)
    return volume


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
        # imported slot (import_runtime_weapon_yumi_rig.py: SetMaterials). The rows
        # and their check are verify_yumi_rig_materials.py's, against the same
        # serialized expectations (fp_material_bindings).
        self.expectations = expectations = B.load()
        self.solved = {}
        parts = [(f"{RIG}/SK_Weapon_18", self.mesh, comp),
                 (f"{RIG}/SM_Weapon_18_Ya", self.arrow.static_mesh_component.get_editor_property("static_mesh"),
                  self.arrow.static_mesh_component)]
        if self.paw is not None:
            parts.append((f"{PAWS}/SM_NyaakotoFP_PawL_Yumi", self.paw.static_mesh_component.get_editor_property("static_mesh"),
                          self.paw.static_mesh_component))
        self.parts = parts
        self.materials = self.check_materials("before any shot")

    def check_materials(self, when):
        """The material gate: each part's ordered rows against the serialized expectations."""
        rows, problems = {}, []
        for asset_path, mesh, component in self.parts:
            slots, drawn = B.asset_rows(mesh), B.component_rows(component)
            rows[asset_path] = B.as_json(slots, drawn)
            problems += B.check(asset_path, slots, drawn, self.expectations[asset_path])
        if problems:
            raise RuntimeError(f"yumi FP review: material gate ({when}): " + "; ".join(problems))
        return rows

    def apply_ids(self, ids):
        """Each part drawn in its unlit ID material: the fur cards and the W18 islands keep their alpha masks."""
        for asset_path, mesh, component in self.parts:
            part = "bow" if asset_path.endswith("SK_Weapon_18") else "arrow" if asset_path.endswith("_Ya") else "paw"
            for index, name, _path in B.asset_rows(mesh):
                component.set_material(index, ids["paw_fur"] if name == "M_NyaakotoFP_FurCards" else ids[part])

    def clear_ids(self):
        """Back to the assets' own slots. EmptyOverrideMaterials is no UFUNCTION, so each override is set to
        None: a null override draws the mesh's own slot (MeshComponent.cpp GetMaterial). The material gate
        then proves it."""
        for _asset_path, mesh, component in self.parts:
            for index, _name, _path in B.asset_rows(mesh):
                component.set_material(index, None)

    def component_socket(self, name):
        t = self.comp.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
        return (t.x, t.y, t.z)

    def evaluate(self, draw):
        """Hold the take at ``draw`` and refresh the bones on the game thread."""
        # The mode is single-node now, so OverrideAnimationData no longer
        # reinitializes: set the instance's time, then let it tick and refresh
        # the bones at that time.
        self.comp.set_position(draw, False)
        self.comp.override_animation_data(self.anim, False, False, draw, 0.0)

    def solve(self, hold):
        """A solved hold from the sockets this mesh actually poses at full draw (rebuilt ones after a rebuild):
        right_cheek, or a study cheek candidate (nock target and cant) by yumi_fp_holds.cheek_hold."""
        self.evaluate(1.0)
        grip_r, muzzle = self.component_socket("Grip_R"), self.component_socket("Muzzle")
        if HOLDS[hold]["solve"] == "right_cheek":
            rc = H.right_cheek(tuple(CONTROL["anchor_cm"]), tuple(CONTROL["rotation_deg"]), MESH_SCALE, grip_r,
                               muzzle)
            cand = STUDY["right_cheek"]["codex_candidate"]
            vs = "vs_codex_candidate"
        else:
            cand = STUDY[hold]
            rc = H.cheek_hold(tuple(cand["nock_target_cm"]), float(cand["cant_right_deg"]), MESH_SCALE, grip_r,
                              muzzle, tuple(cand["aim_cm"]))
            vs = "vs_study"
        rc["component_cm"] = {"Grip_R": grip_r, "Muzzle": muzzle}
        rc[vs] = {"anchor_cm": [a - b for a, b in zip(rc["anchor"], cand["anchor_cm"])],
                  "rotation_deg": [a - b for a, b in zip(rc["rot"], cand["rotation_deg"])]}
        HOLDS[hold].update(anchor=list(rc["anchor"]), rot=list(rc["rot"]))
        self.solved[hold] = rc

    def pose(self, hold):
        """Hang the bow from Grip_L at the anchor, and hold the take at the draw fraction."""
        h = HOLDS[hold]
        if h.get("solve") in ("right_cheek", "cheek"):
            self.solve(hold)
        self.bow.set_actor_scale3d(unreal.Vector(MESH_SCALE, MESH_SCALE, MESH_SCALE))
        self.bow.set_actor_rotation(frotator(h["rot"]), False)
        # Grip_L sits at the mesh origin on the identity Grip root, so the actor
        # origin is the anchor (the runtime recentres on the socket the same way).
        self.bow.set_actor_location(unreal.Vector(*h["anchor"]), False, False)
        self.evaluate(h["draw"])
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
        if hold in self.solved:
            rc = self.solved[hold]
            n = self.comp.get_socket_location("Grip_R")
            m = self.comp.get_socket_location("Muzzle")
            off = math.dist((n.x, n.y, n.z), rc["target_nock"])
            miss = math.hypot(*H.aim_miss((n.x, n.y, n.z), (m.x, m.y, m.z)))
            rows["solve"] = {"nock_off_target_cm": off, "aim_miss_cm": miss, "bound_cm": SOLVE_TOL_CM}
            if off > SOLVE_TOL_CM or miss > SOLVE_TOL_CM:
                raise RuntimeError(f"yumi FP review: {hold} posed its nock {off:.4f} cm off target and its arrow "
                                   f"{miss:.4f} cm off the aim point (bound {SOLVE_TOL_CM} cm)")
        return rows

    def assess(self, hold):
        """Socket math on the posed parts, for an eye-view hold: screen points against root's boxes, the
        reticle's clear line, the aim and the near plane. Recorded, never a gate: originals decide."""
        cam = CONTROL["camera"]
        aspect = cam["aspect"][0] / cam["aspect"][1]
        near = cam["near_plane_cm"]
        pts = {n: (lambda v: (v.x, v.y, v.z))(self.comp.get_socket_location(n)) for n in ("Grip_L", "Grip_R", "Muzzle")}
        ac = self.arrow.static_mesh_component
        pts["Nock"] = (lambda v: (v.x, v.y, v.z))(ac.get_socket_location("Nock"))
        pts["Tip"] = (lambda v: (v.x, v.y, v.z))(ac.get_socket_location("Tip"))
        out = {"eye_cm": pts, "near_plane_cm": near}
        out["screen_uv"] = {n: H.screen_uv(p, FOV, aspect) for n, p in pts.items() if p[0] > 1e-6}
        out["root_boxes"] = {n: H.in_box(out["screen_uv"][n], box) if n in out["screen_uv"] else False
                             for n, box in CONTROL["screen"].items()}
        out["aim_miss_cm"] = H.aim_miss(pts["Grip_R"], pts["Muzzle"])
        out["arrow_behind_near_plane"] = H.segment_behind(pts["Nock"], pts["Tip"], near)
        bounds = {}
        for name, actor in (("bow", self.bow), ("arrow", self.arrow), ("paw", self.paw)):
            if actor is None:
                continue
            o, e = actor.get_actor_bounds(False)
            bounds[name] = {"min_x_cm": o.x - e.x, "max_x_cm": o.x + e.x, "crosses_near_plane": o.x - e.x < near}
        out["bounds"] = bounds
        # The clear line (Grip_L to Muzzle) and the reticle, in half-heights from the screen centre.
        if "Grip_L" in out["screen_uv"] and "Muzzle" in out["screen_uv"]:
            (u0, v0), (u1, v1) = out["screen_uv"]["Grip_L"], out["screen_uv"]["Muzzle"]
            best = min(math.hypot((u0 + (u1 - u0) * t) * aspect, v0 + (v1 - v0) * t) for t in [k / 200 for k in range(201)])
            out["clear_line_to_reticle"] = {"half_heights": best, "reticle_clear_radius": cam["reticle_clear_radius"]}
        return out

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


def camera_record(cam, width, height):
    """The camera a hold was shot with, read back from the spawned actor."""
    cc = cam.camera_component
    loc, rot = cam.get_actor_location(), cam.get_actor_rotation()
    return {"field_of_view_deg": cc.get_editor_property("field_of_view"),
            "aspect_ratio": cc.get_editor_property("aspect_ratio"),
            "constrain_aspect_ratio": cc.get_editor_property("constrain_aspect_ratio"),
            "location_cm": [loc.x, loc.y, loc.z], "rotation_deg": [rot.pitch, rot.yaw, rot.roll],
            "resolution": [width, height]}


def hide(actors, hidden):
    """The set, its sky and its lights, out of (or back into) the ID pass: as actors, in the editor, and
    each component's visibility, since a sky or light component need not follow its actor's flag."""
    for a in actors:
        a.set_actor_hidden_in_game(hidden)
        a.set_is_temporarily_hidden_in_editor(hidden)
        for c in a.get_components_by_class(unreal.SceneComponent):
            c.set_visibility(not hidden, True)


def main():
    opts = parse_args()
    holds = [h for h in opts["holds"].split(",") if h]
    unknown = [h for h in holds if h not in HOLDS]
    if unknown:
        raise RuntimeError(f"yumi FP review: unknown holds {unknown}; known: {sorted(HOLDS)}")
    width, height = (int(x) for x in opts["res"].split("x"))
    out = ROOT / "Saved/YumiFP" / opts["out"]
    out.mkdir(parents=True, exist_ok=True)
    env = build_level()
    runup = highres_runup(opts["runup"])
    ev100 = float(opts["ev"]) if opts["ev"] else metered_ev100()
    volume = exposure(ev100)
    vm = Viewmodel(opts["paws"] != "0")
    ids = None
    if opts["ids"] != "0":
        w18 = f"{RIG}/Textures/T_Weapon_18_BaseColor"
        fur = f"{PAWS}/Textures/T_NyaakotoFP_FurCards_Albedo"
        ids = {"bow": id_material("M_YumiFP_ID_Bow", ID_COLOURS["bow"], mask=w18, clip=0.5),
               "arrow": id_material("M_YumiFP_ID_Arrow", ID_COLOURS["arrow"], mask=w18, clip=0.5, two_sided=True),
               "paw": id_material("M_YumiFP_ID_Paw", ID_COLOURS["paw"]),
               "paw_fur": id_material("M_YumiFP_ID_PawFur", ID_COLOURS["paw"], mask=fur, clip=0.33, two_sided=True,
                                      dither=True)}
    status = {"frames": 0, "queue": list(holds), "phase": "pose", "wait": 0, "written": [], "sockets": {}, "poses": {},
              "assess": {}, "id_files": {}, "regates": {}, "cameras": {}}

    def finish(message, error=False):
        # The exit belongs to -ExecutePythonScript's own executor (EditorPythonExecuter.cpp:58-128, RequestExit at 119-126). Releasing the
        # keep-alive makes its next tick complete its "Executing Python Script..." notification while the engine
        # still ticks, then defer QUIT_EDITOR a frame, so the notification's one-frame UpdateNotificationDeferred
        # ticker runs (SlateAsyncTaskNotificationImpl.cpp:262-304).
        #
        # Captures v2 and v3 instead called quit_editor here. QUIT_EDITOR closes the editor at once
        # (EditorServer.cpp:5990-5996: "Don't call quit_editor directly with slate"), so the executor's next tick
        # returned on the exit request. The plugin then completed the notification only at module shutdown
        # (OnShutdownModule, EditorPythonExecuter.cpp:214-218), after the last ticker tick. Its deferred update, holding the notification widget,
        # outlived Slate into FTSTicker's static destructor, the widget's destruction faulted, and the Mac error
        # handler's cursor loop (HandleErrorRestoreUI) spun until SIGKILL (Saved/YumiFP/capture_v*.exit_hang_sample.txt).
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def tick(delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            finish(f"YUMI_FP_REVIEW_FAILED: {exc!r}", error=True)

    def shoot(path, next_phase):
        status.update(phase="shot", current=path, started=time.time(), count=0, after=next_phase)
        unreal.SystemLibrary.execute_console_command(world(), f'HighResShot {width}x{height} filename="{path}"')

    def step():
        status["frames"] += 1
        LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        hold = status.get("hold")
        if status["phase"] == "pose":
            if not status["queue"]:
                manifest = {"level": LEVEL, "fov": FOV, "mesh_scale": MESH_SCALE, "holds": {h: HOLDS[h] for h in holds},
                            "files": {p: sha256(out / p) for p in status["written"]}, "sockets_cm": status["sockets"],
                            "poses_component_cm": status["poses"], "materials": vm.materials,
                            "materials_after_id_pass": status["regates"], "solved": vm.solved,
                            "assess": status["assess"], "id_files": status["id_files"], "id_colours": ID_COLOURS,
                            "control": {k: CONTROL[k] for k in ("source", "source_sha256")},
                            # What the analysis reads, as this run used it (never the study file as it is later).
                            "study": {"path": STUDY_PATH, "sha256": hashlib.sha256(STUDY_BYTES).hexdigest()},
                            "requested_holds": holds, "ids_enabled": ids is not None,
                            "eye_view_holds": [h for h in holds if "camera" not in HOLDS[h]],
                            "resolution": [width, height], "cameras": status["cameras"],
                            "assessment_camera": {k: CONTROL["camera"][k] for k in (
                                "first_person_fov_deg", "aspect", "near_plane_cm", "reticle_clear_radius")},
                            "set_materials": SET_MATERIALS, "sun": SUN, "ev100": ev100, "exposure_bias": 1.0 - ev100,
                            "highres_runup": runup, "assets_sha256": imported_assets(),
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
            status["poses"][hold] = vm.check_pose(hold)
            status["sockets"][hold] = vm.nock_arrow()
            eye_view = "camera" not in HOLDS[hold]
            if eye_view:
                status["assess"][hold] = vm.assess(hold)
            cam = camera_for(hold, width, height)
            status["cameras"][hold] = camera_record(cam, width, height)
            LEVELS.pilot_level_actor(cam)
            LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, cam=cam, eye_view=eye_view)
            return
        if status["phase"] == "light":
            status["count"] += 1
            if status["count"] < 150:                                  # Lumen, TSR and exposure settle
                return
            shoot(out / f"{hold}.png", "ids" if (ids and status["eye_view"]) else "next")
            return
        if status["phase"] == "shot":
            p = status["current"]
            if not p.is_file() or p.stat().st_mtime < status["started"]:
                status["count"] += 1
                if status["count"] > 4000:
                    finish(f"YUMI_FP_REVIEW_FAILED: {p} was not written", error=True)
                return
            status["written"].append(p.name)
            if status["after"] == "ids":
                # The ID pass: each part in its unlit colour, the set and its lights hidden, no bloom.
                vm.apply_ids(ids)
                hide(env, True)
                exposure(ev100, volume, ids=True)
                status.update(phase="id_settle", count=0)
                return
            if status["after"] == "restore":
                status["id_files"][hold] = p.name
                vm.clear_ids()
                hide(env, False)
                exposure(ev100, volume)
                status["regates"][hold] = vm.check_materials(f"after the {hold} ID pass")
            ACTORS.destroy_actor(status["cam"])
            status["queue"].pop(0)
            status["phase"] = "pose"
            return
        if status["phase"] == "id_settle":
            status["count"] += 1
            if status["count"] < 60:                                   # TSR settles on the unlit frame
                return
            shoot(out / f"{hold}_ids.png", "restore")

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)



# -ExecutePythonScript runs this file in __main__'s namespace (PythonScriptPlugin.cpp RunFile: the console or
# default globals, both __main__'s), so the capture runs as before. measure_fp_fur_cost.py imports the module for
# its scene and holds without starting a capture.
if __name__ == "__main__":
    main()
