"""Third-person review originals of Nyaakoto's paws, cuffs and poses in Unreal, in the game's own materials.

Root's request (20:31 and 20:37 UTC, 2026-10-26): capture the actual saved Unreal materials at original full
resolution, covering:
- both paws, empty and holding;
- the pad-facing and back views;
- the cuffs;
- the full guard and strike poses;
- each shot's LOD, stated.
Capture the current state before revising normals.

Run in the pinned editor with a renderer, after import_nyaakoto_third_person.py (the body, its LODs and clips) and
import_nyaakoto_pbr.py (the game's material instances):
  scripts/toolchain/run-editor-script.sh --editor scripts/unreal/render_nyaakoto_tp_review.py \\
      NYAAKOTO_TP_REVIEW_COMPLETE <log> -- out=<new folder> [res=3840x2160] [shots=<names>] [runup=auto|<n>]

It builds a fresh uncooked level, /Game/ArtReview/NyaakotoTP/L_NyaakotoTP_<time> (ignored, as Content/ArtReview/ is).
- **The character:** /Game/Generated/Meshes/SK_NyaagyuSamurai on a SkeletalMeshActor at the origin, facing +X. Its
  slots are bound as the game binds them (SoraCharacterBase::BuildCat: each M_Hero_X slot to
  /Game/Generated/Characters/Nyaakoto/MI_Nyaakoto_X). The material gate checks all 23 component materials before every
  shot. The manifest records each instance's parent, parameters and textures, and the master's blend mode, sidedness
  and shading model.
- **The poses:** A_NyaagyuSamurai_Guard at its first frame, and A_NyaagyuSamurai_StrikeMakko at its raise and hit
  frames. The paws are also shot in the reference pose ("rest", in their names): the bind pose with no clip. It is
  not a game pose. It shows the pads, which face into the curl in the guard, from clear of the body, and its gate is
  the record's bind sockets. A clip is set on the single-node instance (SetAnimation: OverrideAnimationData alone keeps the old asset once
  the mode is single-node, SkeletalMeshComponent.cpp:4433-4449), then held at the time and evaluated.
  The pose gate: both grip sockets within the readback's 1 cm and 2 deg of the stance's targets.
- **The states:** holding has both PawEmpty morphs at 0; empty has both at 1. SetMorphTarget's weights are applied after
  the animation's curves at every evaluation (SkeletalMeshComponent.cpp:3301-3302), and they are read back.
- **The LOD:** forced with SetForcedLOD(lod + 1). Where the predicted LOD has not followed, the mesh asset is cleared
  and set again: this editor-world component never ticks, so only setting the asset runs UpdateLODStatus (s131 stopped
  at "forced 2, predicted 0"). The forced value and the predicted LOD are then read back (a forced LOD n predicts
  LOD n - 1, SkinnedMeshComponent.cpp:4751-4755).
- **The cameras** (nyaakoto_tp_review_geometry):
  - **paws:** docs/art-direction/data/nyaakoto_tp_review_plan.json gives each pair's target and ranked directions in
    its grip socket's posed frame. The first is taken whose sight line clears the posed body: LOD0's skin as voxels,
    each moved by its bone's transform from the reference pose. A holding and an empty shot of one paw and view share
    a camera.
  - **cuffs:** round the posed forearm at the wrist, the first clear one, the shot's own arm excepted.
  - **the full body:** fixed views.
- **The light:** the yumi review's daylight. A SkyAtmosphere sun of 20,000 lux stands 50 deg up, from the character's
  front left, behind thin haze. With it are its real-time sky light and fixed manual exposure metered from the sun:
  EV100 = log2(E / 2.5), bias 1 - EV100. The only set is a dark floor slab under the feet.
- **The image:** HighResShot at the requested size (3840x2160 by default: the originals at full resolution).
  r.ScreenPercentage is 100 and read back, texture streaming is off, and the run-up is set from TSR's history
  (render_yumi_fp_review.highres_runup).

Writes Saved/NyaakotoThirdPerson/Review/<out>/<shot>.png and manifest.json. The manifest records:
- every file's SHA-256;
- each shot's camera as read back, and its choice among the candidates (rank, scores, what blocked the better ones);
- the pose gate, the morph weights, and the forced and predicted LOD;
- the material rows and every instance's parameters;
- each LOD's build settings: normals have been recomputed since s128, Interchange's default;
- the packages' hashes;
- the light, exposure and console variables.
If the run fails, manifest.partial.json records what was done.

These are editor review originals in the editor's renderer: not the game's camera, lighting or post-process, and not an
admission.
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

require_running_engine("Nyaakoto third-person review")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "art"))
import nyaakoto_tp_review_geometry as G  # noqa: E402

ROOT = Path(unreal.Paths.project_dir()).resolve()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LEVELS = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
SKEL = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
ASSETS = unreal.EditorAssetLibrary
M = unreal.MathLibrary
MESH_PATH = "/Game/Generated/Meshes/SK_NyaagyuSamurai"
CLIPS = {"guard": "/Game/Generated/Animations/A_NyaagyuSamurai_Guard",
         "strike": "/Game/Generated/Animations/A_NyaagyuSamurai_StrikeMakko"}
MATERIALS = "/Game/Generated/Characters/Nyaakoto"
MASTER = f"{MATERIALS}/M_Nyaakoto_PBR"
LEVEL = f"/Game/ArtReview/NyaakotoTP/L_NyaakotoTP_{int(time.time())}"
MARKER = "NYAAKOTO_TP_REVIEW_COMPLETE"
RECORD_PATH = "Content/SourceArt/Characters/Hero/runtime_skin_manifest.json"
RECORD_BYTES = (ROOT / RECORD_PATH).read_bytes()
TP = json.loads(RECORD_BYTES.decode("utf-8"))["third_person"]
# v2 adds the "_solo" rankings the rest-pose shots use (s132); s131 used nyaakoto_tp_review_plan.json.
PLAN_PATH = "docs/art-direction/data/nyaakoto_tp_review_plan_v2.json"
# The sun: the yumi review's 20,000 lux at 50 deg up behind thin haze, turned to come from the character's front left
# (yaw 150: travelling toward -X and +Y).
SUN = {"pitch": -50.0, "yaw": 150.0, "lux": 20000.0, "kelvin": 6500.0, "mie": 6.0, "fog": 0.03}
FLOOR = ("M_NyaakotoTP_Floor", (0.09, 0.055, 0.035), 0.22)
POSE_TOL_CM, POSE_TOL_DEG = 1.0, 2.0
BIND_TOL_CM = 0.5              # the plan's bind bone heads against Unreal's reference pose
SCALARS = ("CoatBlendEnabled", "RoughnessScale", "MetallicScale")
VECTORS = ("Tint", "WhiteFurTint")
TEXTURES = ("AlbedoMap", "NormalMap", "ORMMap", "WhiteFurAlbedoMap", "WhiteFurNormalMap", "WhiteFurORMMap")
BUILD_SETTINGS = ("recompute_normals", "recompute_tangents", "use_mikk_t_space", "compute_weighted_normals",
                  "use_high_precision_tangent_basis", "use_full_precision_u_vs", "remove_degenerates",
                  "threshold_position", "threshold_tangent_normal", "threshold_uv", "morph_threshold_position",
                  "bone_influence_limit")
CVARS = ("r.ScreenPercentage", "r.AntiAliasingMethod", "r.TSR.History.SampleCount", "r.HighResScreenshotDelay",
         "r.TextureStreaming", "r.DynamicGlobalIlluminationMethod", "r.ReflectionMethod", "r.Shadow.Virtual.Enable")
RUNUP_PER_HISTORY_SAMPLE = 2
SETTLE, FIRST_SETTLE = 150, 400   # editor frames before a shot (the yumi review's 150), and before the first


def fail(message):
    raise RuntimeError("nyaakoto TP review: " + message)


def parse_args():
    opts = {"out": "", "res": f"{G.RESOLUTION[0]}x{G.RESOLUTION[1]}", "shots": "", "runup": "auto", "plan": PLAN_PATH}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=", 1)
            opts[k] = v
    return opts


def load(path):
    asset = unreal.load_asset(path)
    if asset is None:
        fail(f"missing asset {path}")
    return asset


def spawn(cls, loc=(0.0, 0.0, 0.0), rot=None):
    return ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), rot if rot is not None else unreal.Rotator(0.0, 0.0, 0.0))


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def vec(v):
    return (v.x, v.y, v.z)


def play_length(clip):
    """UAnimSequenceBase::GetPlayLength, or the animation library's sequence length where Python lacks it."""
    if hasattr(clip, "get_play_length"):
        return float(clip.get_play_length())
    return float(unreal.AnimationLibrary.get_sequence_length(clip))


def packages():
    """Every file of the imported namespaces the capture draws, by SHA-256: what the shots were of."""
    out = {}
    for folder, pattern in (("Content/Generated/Meshes", "*"), ("Content/Generated/Animations", "A_NyaagyuSamurai_*"),
                            ("Content/Generated/Characters/Nyaakoto", "*")):
        for p in sorted((ROOT / folder).rglob(pattern)):
            if p.is_file():
                out[p.relative_to(ROOT).as_posix()] = sha256(p)
    return out


def cvar(name):
    return unreal.SystemLibrary.get_console_variable_float_value(name)


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


def build_level():
    ASSETS.make_directory(LEVEL.rsplit("/", 1)[0])
    if not LEVELS.new_level(LEVEL):
        fail("could not create the level")
    floor = spawn(unreal.StaticMeshActor, (0.0, 0.0, -5.0))           # a 10 cm slab, its top at z = 0
    floor.static_mesh_component.set_static_mesh(load("/Engine/BasicShapes/Cube.Cube"))
    floor.static_mesh_component.set_material(0, plain_material(*FLOOR))
    floor.set_actor_scale3d(unreal.Vector(24.0, 24.0, 0.1))
    atmosphere = spawn(unreal.SkyAtmosphere)
    atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent).set_editor_property("mie_scattering_scale", SUN["mie"])
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
    for command, name, want in (("r.TextureStreaming 0", "r.TextureStreaming", 0.0),
                                ("r.ScreenPercentage 100", "r.ScreenPercentage", 100.0)):
        unreal.SystemLibrary.execute_console_command(world(), command)
        if abs(cvar(name) - want) > 1e-6:
            fail(f"{name} reads {cvar(name)}, not the {want} set")


def metered_ev100():
    return math.log2(SUN["lux"] / 2.5)


def exposure(ev100):
    volume = spawn(unreal.PostProcessVolume)
    volume.set_editor_property("unbound", True)
    s = volume.get_editor_property("settings")
    for key, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                       ("auto_exposure_apply_physical_camera_exposure", False),
                       ("auto_exposure_bias", -ev100 + 1.0), ("bloom_intensity", 0.675), ("vignette_intensity", 0.4),
                       ("motion_blur_amount", 0.0)):
        s.set_editor_property(f"override_{key}", True)
        s.set_editor_property(key, value)
    volume.set_editor_property("settings", s)
    return volume


def highres_runup(option="auto"):
    """r.HighResScreenshotDelay from TSR's history, as render_yumi_fp_review.highres_runup sets it (two frames per
    history sample by default), read back."""
    samples = cvar("r.TSR.History.SampleCount")
    if not samples >= 8.0:
        fail(f"r.TSR.History.SampleCount reads {samples!r}")
    if option == "auto":
        frames = int(math.ceil(RUNUP_PER_HISTORY_SAMPLE * samples))
    elif option.isdigit() and int(option) >= 1:
        frames = int(option)
    else:
        fail(f"runup={option!r} is not auto or a positive frame count")
    unreal.SystemLibrary.execute_console_command(world(), f"r.HighResScreenshotDelay {frames}")
    got = unreal.SystemLibrary.get_console_variable_int_value("r.HighResScreenshotDelay")
    if got != frames:
        fail(f"r.HighResScreenshotDelay reads {got}, not the {frames} set")
    return {"option": option, "r.TSR.History.SampleCount": samples, "r.HighResScreenshotDelay": frames}


class Character:
    def __init__(self, plan):
        self.mesh = load(MESH_PATH)
        if not self.mesh.has_vertex_colors():
            fail("SK_NyaagyuSamurai has no vertex colours: the coat blend needs them")
        names = sorted(str(n) for n in self.mesh.get_all_morph_target_names())
        if names != sorted(G.MORPHS):
            fail(f"the morph targets read {names}")
        self.actor = spawn(unreal.SkeletalMeshActor)
        comp = self.actor.skeletal_mesh_component
        if hasattr(comp, "set_skeletal_mesh_asset"):
            comp.set_skeletal_mesh_asset(self.mesh)
        else:
            comp.set_skeletal_mesh(self.mesh)
        comp.set_update_animation_in_editor(True)
        self.comp = comp
        self.clips = {k: load(v) for k, v in CLIPS.items()}
        self.lengths = {k: play_length(c) for k, c in self.clips.items()}
        # From the component's default mode this changes the mode, so the single-node instance is made with this clip.
        comp.override_animation_data(self.clips["guard"], False, False, 0.0, 0.0)
        self.clip = "guard"
        self.lod_count = SKEL.get_lod_count(self.mesh)
        self.bind_game_materials()
        self.material_rows = self.check_materials("before any shot")
        self.voxels_bind = plan["body"]["voxels"]
        self.bind_heads = plan["body"]["bind_heads_cm"]
        self.ref = unreal.AnimPoseExtensions.get_reference_pose(self.mesh.get_editor_property("skeleton"))
        self.bind_check = self.check_bind()

    def bind_game_materials(self):
        """SoraCharacterBase::BuildCat's binding: each slot named M_Hero_X draws /Game/.../MI_Nyaakoto_X."""
        self.expected = []
        for i, slot in enumerate(self.mesh.get_editor_property("materials")):
            name = str(slot.get_editor_property("material_slot_name"))
            if not name.startswith("M_Hero_"):
                fail(f"slot {i} is {name}, not an M_Hero_ slot the game binds")
            inst = "MI_Nyaakoto_" + name[len("M_Hero_"):]
            mi = load(f"{MATERIALS}/{inst}.{inst}")
            self.comp.set_material(i, mi)
            self.expected.append((i, name, mi.get_path_name()))
        if len(self.expected) != 23:
            fail(f"{len(self.expected)} slots, not 23")

    def check_materials(self, when):
        drawn = [(i, m.get_path_name() if m else None) for i, m in enumerate(self.comp.get_materials())]
        problems = []
        if len(drawn) != len(self.expected):
            problems.append(f"the component draws {len(drawn)} materials for {len(self.expected)} slots")
        for (i, path), (_, name, want) in zip(drawn, self.expected):
            if path != want:
                problems.append(f"index {i} ({name}) draws {path}, not {want}")
        if problems:
            fail(f"material gate ({when}): " + "; ".join(problems))
        return [{"index": i, "slot": n, "material": p} for i, n, p in self.expected]

    def material_record(self):
        lib = unreal.MaterialEditingLibrary
        out = {}
        for _, name, path in self.expected:
            mi = unreal.load_asset(path)
            parent = mi.get_editor_property("parent")
            row = {"slot": name, "parent": parent.get_path_name() if parent else None, "scalars": {}, "vectors": {},
                   "textures": {}}
            for p in SCALARS:
                row["scalars"][p] = lib.get_material_instance_scalar_parameter_value(mi, p)
            for p in VECTORS:
                c = lib.get_material_instance_vector_parameter_value(mi, p)
                row["vectors"][p] = [c.r, c.g, c.b, c.a]
            for p in TEXTURES:
                t = lib.get_material_instance_texture_parameter_value(mi, p)
                row["textures"][p] = t.get_path_name() if t else None
            out[path] = row
        master = load(MASTER)
        return {"instances": out, "master": {"path": master.get_path_name(),
                                             "two_sided": bool(master.get_editor_property("two_sided")),
                                             "blend_mode": str(master.get_editor_property("blend_mode")),
                                             "shading_model": str(master.get_editor_property("shading_model"))}}

    def build_settings(self):
        rows = []
        for lod in range(self.lod_count):
            s = unreal.SkeletalMeshEditorSubsystem.get_lod_build_settings(self.mesh, lod)
            row = {"lod": lod}
            for key in BUILD_SETTINGS:
                try:
                    value = s.get_editor_property(key)
                    row[key] = value if isinstance(value, (bool, int, float)) else str(value)
                except Exception as exc:  # a property this engine names otherwise: recorded, not guessed
                    row[key] = f"unread: {exc.__class__.__name__}"
            rows.append(row)
        return rows

    def check_bind(self):
        """The plan's bind bone heads (from LOD0's FBX) against Unreal's reference pose: the voxels' frame."""
        worst = 0.0
        for bone, want in self.bind_heads.items():
            got = vec(unreal.AnimPoseExtensions.get_ref_bone_pose(self.ref, bone, unreal.AnimPoseSpaces.WORLD).translation)
            worst = max(worst, G.norm(G.sub(got, tuple(want))))
        if worst > BIND_TOL_CM:
            fail(f"the plan's bind bones are up to {worst:.3f} cm from Unreal's reference pose")
        return {"bones": len(self.bind_heads), "worst_cm": worst, "bound_cm": BIND_TOL_CM}

    def set_mesh(self, mesh):
        if hasattr(self.comp, "set_skeletal_mesh_asset"):
            self.comp.set_skeletal_mesh_asset(mesh)
        else:
            self.comp.set_skeletal_mesh(mesh)

    def set_state(self, pose, state, lod):
        """Force the LOD, hold the pose (a clip at its time, or the reference pose for "rest") with both morphs at the
        state's weight, and evaluate."""
        stance, u = G.pose_stance(pose, TP)
        self.comp.set_forced_lod(lod + 1)
        reset = int(self.comp.get_predicted_lod_level()) != lod
        if reset:
            # SetForcedLOD only stores the value. UpdateLODStatus applies it, and outside a tick (this editor-world
            # component never ticks) it runs only when the mesh asset is set (SkinnedMeshComponent.cpp:2754-2820).
            # s131 read forced 2, predicted 0, and stopped. So the asset is cleared and set again. SetSkeletalMesh
            # keeps the material overrides but clears the morph curves and re-initialises the animation
            # (SkeletalMeshComponent.cpp:3508-3591): the materials are bound again and gated, and the morphs and the
            # clip are set again below.
            self.set_mesh(None)
            self.set_mesh(self.mesh)
            self.bind_game_materials()
            self.clip = "reset"
        weight = 1.0 if state == "empty" else 0.0
        for name in G.MORPHS:
            self.comp.set_morph_target(name, weight, False)
        if pose == "rest":
            if self.clip is not None:
                self.comp.set_animation(None)
                self.clip = None
            self.comp.override_animation_data(None, False, False, 0.0, 0.0)
            return {"pose": pose, "clip": None, "u": 0.0, "time_s": 0.0, "play_length_s": None, "stance": None,
                    "state": state, "lod": lod, "mesh_reset_for_lod": reset}
        clip = "guard" if pose == "guard" else "strike"
        t = u * self.lengths[clip]
        if clip != self.clip:
            self.comp.set_animation(self.clips[clip])
            self.clip = clip
        self.comp.set_position(t, False)
        self.comp.override_animation_data(self.clips[clip], False, False, t, 0.0)
        return {"pose": pose, "clip": CLIPS[clip], "u": u, "time_s": t, "play_length_s": self.lengths[clip],
                "stance": stance, "state": state, "lod": lod, "mesh_reset_for_lod": reset}

    def check_state(self, want):
        """The pose, morph and LOD gates, after the evaluation has settled."""
        out = {"sockets": {}}
        targets = G.bind_targets(TP) if want["pose"] == "rest" else G.two_paw_targets(want["stance"])
        for sock, (pos, x, z) in targets.items():
            t = self.comp.get_socket_transform(sock, unreal.RelativeTransformSpace.RTS_COMPONENT)
            rot = t.rotation.rotator()
            got_x, got_z = vec(M.get_forward_vector(rot)), vec(M.get_up_vector(rot))
            err_cm = G.norm(G.sub(vec(t.translation), pos))
            err_deg = max(G.angle_deg(got_x, x), G.angle_deg(got_z, z))
            out["sockets"][sock] = {"component_cm": list(vec(t.translation)), "target_cm": list(pos),
                                    "error_cm": err_cm, "error_deg": err_deg}
            if err_cm > POSE_TOL_CM or err_deg > POSE_TOL_DEG:
                fail(f"{want['pose']}: {sock} is {err_cm:.3f} cm and {err_deg:.2f} deg from its target")
        out["morphs"] = {name: self.comp.get_morph_target(name) for name in G.MORPHS}
        weight = 1.0 if want["state"] == "empty" else 0.0
        if any(abs(v - weight) > 1e-6 for v in out["morphs"].values()):
            fail(f"the morphs read {out['morphs']}, not {weight}")
        out["forced_lod"] = int(self.comp.get_forced_lod())
        out["predicted_lod"] = int(self.comp.get_predicted_lod_level())
        if out["forced_lod"] != want["lod"] + 1 or out["predicted_lod"] != want["lod"]:
            fail(f"LOD{want['lod']} reads forced {out['forced_lod']}, predicted {out['predicted_lod']}")
        return out

    def posed_voxels(self):
        """Each body voxel moved by its bone's transform from the reference pose to the current pose."""
        rel = {}
        for bone in {v[0] for v in self.voxels_bind}:
            ref = unreal.AnimPoseExtensions.get_ref_bone_pose(self.ref, bone, unreal.AnimPoseSpaces.WORLD)
            posed = self.comp.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT)
            rel[bone] = M.compose_transforms(M.invert_transform(ref), posed)
        return [(b, vec(M.transform_location(rel[b], unreal.Vector(x, y, z)))) for b, x, y, z in self.voxels_bind]

    def socket_frame(self, sock):
        t = self.comp.get_socket_transform(sock, unreal.RelativeTransformSpace.RTS_WORLD)
        rot = t.rotation.rotator()
        axes = G.axes_from_xz(vec(M.get_forward_vector(rot)), vec(M.get_up_vector(rot)))
        right = vec(M.get_right_vector(rot))
        if G.norm(G.sub(axes[1], right)) > 1e-4:
            fail(f"{sock}'s right vector {right} is not Z ^ X {axes[1]}")
        return vec(t.translation), axes

    def bone(self, name):
        return vec(self.comp.get_socket_location(name))


def camera_for(shot, ch, plan, aspect):
    """(camera position, target, horizontal fov, record) for a shot, as nyaakoto_tp_review_geometry places it."""
    if shot["kind"] == "body":
        cam, target, distance = G.body_camera(shot["camera"], aspect)
        return cam, target, G.BODY_FOV_DEG, {"view": G.BODY_VIEWS[shot["camera"]], "distance_cm": distance}
    voxels = ch.posed_voxels()
    if shot["kind"] == "paw":
        p = plan["cameras"][shot["camera"]]
        origin, axes = ch.socket_frame(p["socket"])
        target = G.to_world(origin, axes, p["target_local_cm"])
        row = G.choose(p["candidates"], target, p["distance_cm"], voxels, lambda d: G.dir_to_world(axes, d))
        cand = p["candidates"][row["rank"]]
        return row["camera"], target, p["fov_deg"], {
            "socket": p["socket"], "socket_origin_cm": list(origin), "distance_cm": p["distance_cm"],
            "rank": row["rank"], "of": len(p["candidates"]), "clear": row["clear"], "blocked": row["blocked"],
            "joint": cand["joint"], "holding": cand["holding"], "empty": cand["empty"],
            "direction_world": list(row["direction"])}
    side = shot["side"]
    wrist, elbow = ch.bone(f"hand_{side}"), ch.bone(f"forearm_{side}")
    distance = G.cuff_distance(aspect)
    cands = G.cuff_candidates(wrist, elbow, side, shot["view"])
    row = G.choose(cands, wrist, distance, voxels, skip_bones=(f"forearm_{side}", f"hand_{side}"))
    return row["camera"], wrist, G.CUFF_FOV_DEG, {
        "wrist_cm": list(wrist), "elbow_cm": list(elbow), "distance_cm": distance, "rank": row["rank"],
        "of": len(cands), "clear": row["clear"], "blocked": row["blocked"],
        "preference": cands[row["rank"]]["preference"], "direction_world": list(row["direction"])}


def spawn_camera(loc, target, fov, width, height):
    rot = M.find_look_at_rotation(unreal.Vector(*loc), unreal.Vector(*target))
    cam = spawn(unreal.CameraActor, loc, rot)
    cc = cam.camera_component
    cc.set_editor_property("field_of_view", fov)
    cc.set_editor_property("aspect_ratio", width / height)
    cc.set_editor_property("constrain_aspect_ratio", True)
    l, r = cam.get_actor_location(), cam.get_actor_rotation()
    return cam, {"location_cm": list(vec(l)), "rotation_deg": [r.pitch, r.yaw, r.roll], "target_cm": list(target),
                 "field_of_view_deg": cc.get_editor_property("field_of_view"),
                 "aspect_ratio": cc.get_editor_property("aspect_ratio"), "resolution": [width, height]}


def main():
    opts = parse_args()
    if not opts["out"]:
        fail("out=<new folder name> is required")
    out = ROOT / "Saved/NyaakotoThirdPerson/Review" / opts["out"]
    if out.exists():
        fail(f"{out} exists: originals go to a new folder")
    width, height = (int(x) for x in opts["res"].split("x"))
    aspect = width / height
    plan_bytes = (ROOT / opts["plan"]).read_bytes()
    plan = json.loads(plan_bytes.decode("utf-8"))
    if tuple(plan["resolution"]) != (width, height):
        fail(f"the plan framed {plan['resolution']}, not {width}x{height}")
    if plan["inputs"]["runtime_skin_manifest"] != hashlib.sha256(RECORD_BYTES).hexdigest():
        fail("the plan was made from another runtime_skin_manifest.json")
    shots = G.shots()
    if opts["shots"]:
        wanted = opts["shots"].split(",")
        unknown = sorted(set(wanted) - {s["name"] for s in shots})
        if unknown:
            fail(f"unknown shots {unknown}")
        shots = [s for s in shots if s["name"] in wanted]
    out.mkdir(parents=True)
    build_level()
    runup = highres_runup(opts["runup"])
    ev100 = metered_ev100()
    exposure(ev100)
    unreal.SystemLibrary.execute_console_command(world(), "Editor.AsyncAssetCompilationFinishAll")
    ch = Character(plan)
    # The game's instances are bound now: finish any compilation they started before the first frame is judged.
    unreal.SystemLibrary.execute_console_command(world(), "Editor.AsyncAssetCompilationFinishAll")
    record = {"level": LEVEL, "engine": unreal.SystemLibrary.get_engine_version(), "resolution": [width, height],
              "shots_requested": [s["name"] for s in shots], "sun": SUN, "ev100": ev100, "exposure_bias": 1.0 - ev100,
              "floor": FLOOR, "highres_runup": runup,
              "inputs": {RECORD_PATH: hashlib.sha256(RECORD_BYTES).hexdigest(), opts["plan"]: hashlib.sha256(plan_bytes).hexdigest(),
                         "scripts/unreal/render_nyaakoto_tp_review.py": sha256(__file__), "scripts/art/nyaakoto_tp_review_geometry.py": sha256(G.__file__)},
              "materials": ch.material_rows, "material_parameters": ch.material_record(),
              "lod_build_settings": ch.build_settings(), "lod_count": ch.lod_count, "bind_check": ch.bind_check,
              "clips": {k: {"asset": CLIPS[k], "play_length_s": v} for k, v in ch.lengths.items()},
              "shots": {}, "files": {},
              "scope": "editor review originals in the game's materials: not the game's camera, light or "
                       "post-process, and not an admission"}
    status = {"frames": 0, "queue": list(shots), "phase": "state", "count": 0}

    def write_manifest(name):
        record["cvars"] = {k: cvar(k) for k in CVARS}
        record["packages_sha256"] = packages()
        (out / name).write_text(json.dumps(record, indent=1) + "\n")

    def finish(message, error=False):
        # As render_yumi_fp_review.finish: release the keep-alive and let -ExecutePythonScript's executor defer
        # QUIT_EDITOR (never quit_editor from a Slate callback: the exit hang, EDITOR_EXIT_HANG.md).
        unreal.unregister_slate_post_tick_callback(handle)
        (unreal.log_error if error else unreal.log)(message)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)

    def tick(delta):
        try:
            step()
        except Exception as exc:  # never spin on a failing callback
            try:
                write_manifest("manifest.partial.json")
            except Exception:
                pass
            finish(f"NYAAKOTO_TP_REVIEW_FAILED: {exc!r}", error=True)

    def step():
        status["frames"] += 1
        LEVELS.editor_invalidate_viewports()
        if status["frames"] < 30:
            return
        if status["phase"] == "state":
            if not status["queue"]:
                record["materials_after"] = ch.check_materials("after the last shot")
                write_manifest("manifest.json")
                finish(f"{MARKER}: {len(record['files'])} captures in {out}")
                return
            shot = status["queue"][0]
            status.update(shot=shot, want=ch.set_state(shot["pose"], shot["state"], shot["lod"]), phase="settle", count=0)
            return
        shot = status["shot"]
        if status["phase"] == "settle":
            status["count"] += 1
            if status["count"] < 20:
                return
            gates = ch.check_state(status["want"])
            ch.check_materials(f"before {shot['name']}")
            loc, target, fov, choice = camera_for(shot, ch, plan, aspect)
            cam, cam_record = spawn_camera(loc, target, fov, width, height)
            want = {k: v for k, v in status["want"].items() if k != "stance"}
            record["shots"][shot["name"]] = {"shot": shot, "state": want, "gates": gates, "camera": cam_record,
                                             "choice": choice}
            LEVELS.pilot_level_actor(cam)
            LEVELS.editor_set_game_view(True)
            status.update(phase="light", count=0, cam=cam)
            return
        if status["phase"] == "light":
            status["count"] += 1
            # Lumen, TSR and exposure settle; the first shot also waits out the shaders and the scene's first capture.
            if status["count"] < (FIRST_SETTLE if not record["files"] else SETTLE):
                return
            path = out / f"{shot['name']}.png"
            status.update(phase="shot", path=path, started=time.time(), count=0)
            unreal.SystemLibrary.execute_console_command(world(), f'HighResShot {width}x{height} filename="{path}"')
            return
        if status["phase"] == "shot":
            p = status["path"]
            if not p.is_file() or p.stat().st_mtime < status["started"]:
                status["count"] += 1
                if status["count"] > 6000:
                    fail(f"{p} was not written")
                return
            record["files"][p.name] = sha256(p)
            # The pose and morphs once more, after the shot: nothing moved while it rendered.
            record["shots"][shot["name"]]["gates_after"] = ch.check_state(status["want"])
            ACTORS.destroy_actor(status["cam"])
            status["queue"].pop(0)
            status["phase"] = "state"

    handle = unreal.register_slate_post_tick_callback(tick)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)


if __name__ == "__main__":
    main()
