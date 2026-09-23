"""Build an isolated, editable quadruped rig and four-beat walk study.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_rig_study.py

The input is extracted from the immutable d319aad horse source. No existing
horse asset, game collision, animation, or Unreal importer is modified.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Horses/Nyaagyu/RigStudy"
OUT.mkdir(parents=True, exist_ok=True)
BASE_COMMIT = "d319aadae6ecf2bad1967f9462b6660f2136612a"
BASE_PATH = "Content/SourceArt/Horses/Nyaagyu/Nyaagyu_HorseAndTack.blend"
BASE_SHA = "0ea0b1b96752f02d7c1dd3d44b08b8b9241184e609394450e453cbe54e75d573"
NAME = "SK_Nyaagyu_Horse_RigStudy"
BLEND = OUT / "Nyaagyu_Horse_RigStudy.blend"
FBX = OUT / f"{NAME}.fbx"
FRAMES = (1, 10, 19, 28)
PREVIEWS = [OUT / f"Nyaagyu_Walk_Frame_{frame:02}.png" for frame in FRAMES]
MANIFEST = OUT / "manifest.json"


def sha(data_or_path):
    if isinstance(data_or_path, Path):
        return hashlib.sha256(data_or_path.read_bytes()).hexdigest()
    return hashlib.sha256(data_or_path).hexdigest()


pointer = subprocess.check_output(["git", "show", f"{BASE_COMMIT}:{BASE_PATH}"], cwd=ROOT)
base = subprocess.check_output(["git", "lfs", "smudge"], input=pointer, cwd=ROOT)
assert sha(base) == BASE_SHA, "The pinned horse source has changed"
with tempfile.NamedTemporaryFile(prefix="nyaagyu-horse-rig-base-", suffix=".blend") as source:
    source.write(base)
    source.flush()
    bpy.ops.wm.open_mainfile(filepath=source.name)

bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.frame_start, scene.frame_end = 1, 37
scene.render.fps = 30

source_collection = bpy.data.collections["NyaagyuHorse_Editable"]
source_collection.name = "NyaagyuHorse_RigStudy_Source"
export_collection = bpy.data.collections.get("Unreal_Export_Only")
if export_collection:
    for obj in tuple(export_collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(export_collection)
core = bpy.data.objects["Horse_anatomical_core"]
assert len(core.data.vertices) > 30000

arm_data = bpy.data.armatures.new(f"{NAME}_Armature")
arm = bpy.data.objects.new(NAME, arm_data)
scene.collection.objects.link(arm)
arm.show_in_front = True
arm_data.display_type = "STICK"
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")


def bone(name, head, tail, parent=None):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = head, tail
    b.roll = 0
    if parent:
        b.parent = arm_data.edit_bones[parent]
    return b


bone("root", (0, 0, 0), (0, 0, .18))
bone("pelvis", (-.75, 0, 1.04), (-.25, 0, 1.06), "root")
bone("spine", (-.25, 0, 1.06), (.23, 0, 1.09), "pelvis")
bone("chest", (.23, 0, 1.09), (.52, 0, 1.21), "spine")
bone("neck", (.51, 0, 1.20), (.79, 0, 1.61), "chest")
bone("head", (.79, 0, 1.61), (1.11, 0, 1.36), "neck")
bone("tail", (-.79, 0, 1.08), (-1.02, 0, .69), "pelvis")
bone("saddle_mount", (-.03, 0, 1.34), (-.03, 0, 1.48), "spine")
for label, side in (("L", -1), ("R", 1)):
    y = side * .215
    fore = ((.40, y, 1.12), (.48, y, .70), (.50, y, .29), (.52, y, .115), (.54, y, .055))
    hind = ((-.57, y, 1.10), (-.75, y, .69), (-.82, y, .37), (-.75, y, .115), (-.72, y, .055))
    for family, joints, parent in (("fore", fore, "chest"), ("hind", hind, "pelvis")):
        prior = parent
        for segment, (head, tail) in zip(("upper", "lower", "pastern", "hoof"), zip(joints, joints[1:])):
            name = f"{family}_{label}_{segment}"
            bone(name, head, tail, prior)
            prior = name
    bone(f"abumi_{label}", (-.035, side * .432, 1.10), (-.035, side * .432, .86), "saddle_mount")
    bone(f"tazuna_{label}", (1.10, side * .154, 1.33), (.183, side * .125, 1.35), "head")
bpy.ops.object.mode_set(mode="OBJECT")
arm.select_set(False)


def clamp(value):
    return min(1.0, max(0.0, value))


def smoothstep(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def body_weights(x, z):
    if x < -.24:
        w = smoothstep((x + .67) / .43)
        return {"pelvis": 1 - w, "spine": w}
    if x < .29:
        w = smoothstep((x + .24) / .53)
        return {"spine": 1 - w, "chest": w}
    if x < .57 or z < 1.18:
        return {"chest": 1.0}
    w = smoothstep((x - .57) / .25)
    if x > .79 and z > 1.29:
        h = smoothstep((x - .78) / .22)
        return {"neck": 1 - h, "head": h}
    return {"chest": 1 - w, "neck": w}


def limb_weights(family, side, z):
    lower_joint = .70 if family == "fore" else .69
    pastern_joint = .29 if family == "fore" else .37
    intervals = (("upper", lower_joint), ("lower", pastern_joint),
                 ("pastern", .115), ("hoof", 0))
    for index, (_, threshold) in enumerate(intervals[:-1]):
        if z >= threshold:
            transition = smoothstep((threshold + .055 - z) / .11)
            return {f"{family}_{side}_{intervals[index][0]}": 1 - transition,
                    f"{family}_{side}_{intervals[index + 1][0]}": transition}
    transition = smoothstep((.15 - z) / .09)
    return {f"{family}_{side}_pastern": 1 - transition,
            f"{family}_{side}_hoof": transition}


groups = {b.name: core.vertex_groups.new(name=b.name) for b in arm_data.bones if b.use_deform}
for vertex in core.data.vertices:
    x, y, z = (core.matrix_world @ vertex.co)
    weights = body_weights(x, z)
    if z < 1.10 and abs(y) > .065:
        family = "fore" if x > .14 else "hind" if x < -.37 else None
        if family:
            center = .49 if family == "fore" else -.71
            proximity = smoothstep((.38 - abs(x - center)) / .19)
            influence = smoothstep((1.09 - z) / .35) * smoothstep((abs(y) - .07) / .13) * proximity
            if influence > .001:
                for key in weights:
                    weights[key] *= 1 - influence
                for key, value in limb_weights(family, "L" if y < 0 else "R", z).items():
                    weights[key] = weights.get(key, 0) + influence * value
    total = sum(weights.values())
    for name, weight in weights.items():
        if weight > .0001:
            groups[name].add([vertex.index], weight / total, "REPLACE")
world = core.matrix_world.copy()
core.parent = arm
core.matrix_world = world
mod = core.modifiers.new("Quadruped_skin", "ARMATURE")
mod.object = arm
mod.use_deform_preserve_volume = True


def rigid_to_bone(obj, bone_name):
    matrix = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = matrix
    obj["rig_study_bone"] = bone_name


source_meshes = [o for o in source_collection.objects if o.type == "MESH"]
for obj in source_meshes:
    if obj == core:
        continue
    name = obj.name
    if name.startswith(("Horse_tail",)):
        target = "tail"
    elif name.startswith(("Horse_mane",)):
        target = "neck"
    elif name.startswith(("Horse_forelock", "Horse_eye", "Horse_ear", "Horse_inner_ear",
                          "Horse_nostril", "Horse_muzzle", "Horse_lower_lip")):
        target = "head"
    elif name.startswith(("Horse_fore_", "Horse_hind_")):
        family = "fore" if "_fore_" in name else "hind"
        side = "L" if "_-1_" in name else "R"
        target = f"{family}_{side}_hoof" if "_hoof" in name else f"{family}_{side}_pastern"
    elif name.startswith(("Omogai", "Kutsuwa")):
        target = "head"
    elif name.startswith(("Tazuna_",)):
        target = "tazuna_L" if "_-1" in name else "tazuna_R"
    elif name.startswith("Abumi_") or "abumi_" in name:
        target = "abumi_L" if "_-1" in name else "abumi_R"
    else:
        target = "saddle_mount"
    rigid_to_bone(obj, target)

anchor_bones = {
    "Horse_Root": "root", "Saddle_RiderSeat": "saddle_mount",
    "Tazuna_LeftGrip": "tazuna_L", "Tazuna_RightGrip": "tazuna_R",
    "Abumi_LeftFoot": "abumi_L", "Abumi_RightFoot": "abumi_R",
}
for name, target in anchor_bones.items():
    rigid_to_bone(bpy.data.objects[name], target)

# In-place walk: four independent contacts, LH -> LF -> RH -> RF. The phase
# order is sourced; angles and support timings are deliberately a study.
footfall = ("hind_L", "fore_L", "hind_R", "fore_R")
phase_offset = {name: i * .25 for i, name in enumerate(footfall)}


def sagittal_rotation(pose_bone, radians, frame, group):
    # Blender's bone-local Y follows the bone length. Euler Y therefore twists
    # the limb rather than swinging it in the horse's X/Z plane. Convert the
    # horse's world +Y sagittal hinge axis into each rest bone's local frame.
    rest = arm.data.bones[pose_bone.name].matrix_local.to_3x3()
    axis = (rest.inverted() @ Vector((0, 1, 0))).normalized()
    pose_bone.rotation_mode = "QUATERNION"
    pose_bone.rotation_quaternion = Quaternion(axis, radians)
    pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=group)


arm.animation_data_create()
walk = bpy.data.actions.new("AN_Nyaagyu_Horse_Walk4Beat_InPlace_36f")
arm.animation_data.action = walk
for frame in range(1, 38):
    t = (frame - 1) / 36
    scene.frame_set(frame)
    root = arm.pose.bones["root"]
    root.location.z = .010 * math.sin(4 * math.pi * t)
    root.keyframe_insert(data_path="location", frame=frame, group="root")
    for family in footfall:
        phase = (t - phase_offset[family]) % 1
        if phase < .63:  # ground-support interval; toe travels back in place
            pitch = -.16 + .32 * phase / .63
            fold = 0.0
        else:  # swing; recover leg and visibly clear the hoof
            u = (phase - .63) / .37
            pitch = .16 - .32 * u
            fold = math.sin(math.pi * u)
        sign = -1 if family.startswith("hind") else 1
        for segment, radians in (("upper", pitch),
                                  ("lower", sign * .27 * fold),
                                  ("pastern", -sign * .13 * fold),
                                  ("hoof", sign * .06 * fold)):
            p = arm.pose.bones[f"{family}_{segment}"]
            sagittal_rotation(p, radians, frame, family)
    for name, radians in (("neck", .022 * math.sin(4 * math.pi * t)),
                          ("head", -.016 * math.sin(4 * math.pi * t + .4)),
                          ("tail", .035 * math.sin(2 * math.pi * t))):
        p = arm.pose.bones[name]
        sagittal_rotation(p, radians, frame, name)

scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
arm.select_set(True)
for obj in source_meshes:
    obj.select_set(True)
for name in anchor_bones:
    bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(
    filepath=str(FBX), use_selection=True,
    object_types={"ARMATURE", "MESH", "EMPTY"},
    add_leaf_bones=False, apply_unit_scale=True,
    axis_forward="-Y", axis_up="Z", bake_anim=True,
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
)
bpy.ops.object.select_all(action="DESELECT")

cam = bpy.data.objects["Review_camera"]
cam.location = (0, -4.5, 1.50)
cam.rotation_euler = (Vector((0, 0, .91)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = 3.45
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.render.resolution_x = 1100
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for frame, preview in zip(FRAMES, PREVIEWS):
    scene.frame_set(frame)
    scene.render.filepath = str(preview)
    bpy.ops.render.render(write_still=True)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

source_manifest = json.loads(subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:Content/SourceArt/Horses/Nyaagyu/manifest.json"],
    cwd=ROOT))
logo = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
assert sha(logo) == source_manifest["insignia_sha256"]
assert len([o for o in source_meshes if o.name.startswith("SORA_kamon_exact_svg_")]) == 8
manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_nyaagyu_horse_rig_study.py",
    "validator": "scripts/art/validate_nyaagyu_horse_rig_study.py",
    "base_commit": BASE_COMMIT,
    "base_source_path": BASE_PATH,
    "base_source_sha256": BASE_SHA,
    "source_blend": BLEND.name,
    "source_blend_sha256": sha(BLEND),
    "fbx": FBX.name,
    "fbx_sha256": sha(FBX),
    "review_frames": [{"frame": f, "file": p.name, "sha256": sha(p)} for f, p in zip(FRAMES, PREVIEWS)],
    "source_parts": len(source_meshes),
    "skinned_core_vertices": len(core.data.vertices),
    "bone_names": sorted(b.name for b in arm_data.bones),
    "anchor_bones": anchor_bones,
    "walk": {"name": walk.name, "start_frame": 1, "end_frame": 37,
             "fps": 30, "footfall_order": list(footfall),
             "contact_frames": {name: 1 + i * 9 for i, name in enumerate(footfall)},
             "in_place": True},
    "local_forward": "+X horse-forward; +Z up; existing source -Y = Left anchor",
    "sora_logo_sha256": sha(logo),
    "tack_reference": {
        "abumi": "https://www.metmuseum.org/art/collection/search/712927",
        "mon_placement": "https://www.metmuseum.org/art/collection/search/35376",
        "walk_order": "https://vet.ucalgary.ca/summercamps/animal-interactions/tuesday/equine",
    },
    "license": "Original project-owned rig, animation and renders over the pinned project-owned horse geometry; exact user-supplied SORA SVG geometry retained.",
    "limitations": "Source-only quadruped deformation and walk-cycle study; not rideable, not photoreal, and not a historically or biomechanically verified gait. No rein simulation, saddle-contact dynamics, ground-contact IK, UE skeletal import, engine animation blueprint, gameplay collision, horse control, or in-game performance validation.",
}
MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_HORSE_RIG_STUDY_CREATED", len(source_meshes), len(arm_data.bones), len(core.data.vertices), [p.name for p in PREVIEWS])
