"""Skin the authored Nyaakoto source to the runtime samurai skeleton.

Run after create_nyaagyu_hero_character.py and rig_original_cats.py. The review
source remains editable/unrigged; this exports the campaign/Arena world visual
under the existing SK_NyaagyuSamurai and A_NyaagyuSamurai_Walk identities.
Armor, face, bow, arrows and kamon use rigid per-part weights so their authored
silhouettes survive movement. This is an animation integration pass, not a
production deformation/groom or a photoreal shipping-character claim.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
HERO = ROOT / "Content/SourceArt/Characters/Hero"
OUT = ROOT / "Content/SourceArt"
SOURCE = HERO / "Nyaagyu_HeroCharacter.blend"
MANIFEST = HERO / "runtime_skin_manifest.json"
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
source_record = json.loads((HERO / "manifest.json").read_text())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_record["blend_sha256"]
assert source_record["insignia_sha256"] == json.loads(
    (OUT / "UI/sora_logo_manifest.json").read_text())["source_sha256"]
source = bpy.data.collections["NyaagyuHero_Editable"]
parts = sorted((o for o in source.objects if o.type == "MESH"), key=lambda o: o.name)
assert len(parts) == source_record["source_parts"]


def rig_bone(name: str, world_position: Vector) -> str:
    if name.startswith("UserSupplied_SORAKamon_sode_") or name.startswith("Sode_kamon_backing_"):
        return "upperarm_L" if "_-1" in name else "upperarm_R"
    if name.startswith("UserSupplied_SORAKamon_waist"):
        return "pelvis"
    if name.startswith("UserSupplied_SORAKamon_chest"):
        return "spine"
    if name.startswith(("Skull", "Head_", "Lower_jaw", "Ear_", "Cheek_", "Muzzle_", "Eye_", "Vertical_pupil", "Corneal_", "Angular_", "Whisker_", "Tiger_", "Guard_hair_", "Soft_nose", "White_nose", "Forehead_", "Triangular_nose", "Philtrum", "Mouth_")):
        return "head"
    if name.startswith(("Fur_neck", "White_throat")):
        return "neck"
    if name.startswith("Tail_"):
        return "tail_01" if world_position.x > -.34 else "tail_02" if world_position.x > -.49 else "tail_03"
    if name.startswith(("Saya_", "Sageo_", "Katana_", "Obi_", "Resistance_sash", "Clan_mon", "Layered_hakama")):
        return "pelvis"
    if name.startswith(("Ebira_", "Ya_", "Yumi_", "Resistance_insignia", "Linen_under", "Indigo_samurai", "Under_kimono", "Do_")):
        return "spine"
    side = "L" if world_position.y < 0 else "R"
    if name.startswith(("Hakama_upper_leg", "Hakama_fold")):
        return f"thigh_{side}"
    if name.startswith(("Hakama_shin", "Kyahan_", "Greave_")):
        return f"shin_{side}"
    if name.startswith(("Heel_", "Tabi_", "Toe_", "Claw_")):
        return f"foot_{side}"
    if name.startswith(("Shoulder_", "Linen_sleeve", "Sode_")):
        return f"upperarm_{side}"
    if name.startswith(("Fur_forearm", "Kote_", "Karakuri_", "Wrist_cell_")):
        return f"forearm_{side}"
    if name.startswith(("Paw_hand", "Finger_", "Thumb_")):
        return f"hand_{side}"
    raise ValueError(f"Unclassified Nyaakoto source part: {name}")

runtime = bpy.data.collections.new("Nyaakoto_RuntimeSkin_NotReview")
bpy.context.scene.collection.children.link(runtime)
all_bones = ["root", "pelvis", "spine", "neck", "head", "tail_01", "tail_02", "tail_03"]
for side in ("L", "R"):
    all_bones.extend(f"{joint}_{side}" for joint in
                     ("upperarm", "forearm", "hand", "thigh", "shin", "foot"))
weights = Counter()
duplicates = []
for src in parts:
    obj = src.copy()
    obj.data = src.data.copy()
    runtime.objects.link(obj)
    obj.matrix_world = src.matrix_world.copy()
    obj.name = f"Runtime_{src.name}"
    # The sculpted cheek and short-fur meshes have no UVs in the art-review
    # source. Give them stable face-plane coordinates before the final join so
    # the runtime fur normal/albedo maps do not collapse to one texel.
    if not obj.data.uv_layers:
        uv = obj.data.uv_layers.new(name="UVMap")
        for loop in obj.data.loops:
            point = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = ((point.y + .8) * 2.4, (point.z - .55) * 2.4)
    # Splitting source parts keeps hard armor, crest paths and arrow fletching
    # coherent while preserving every authored material slot on final join.
    groups = {bone: obj.vertex_groups.new(name=bone) for bone in all_bones}
    for vertex in obj.data.vertices:
        bone = rig_bone(src.name, obj.matrix_world @ vertex.co)
        groups[bone].add([vertex.index], 1.0, "REPLACE")
        weights[bone] += 1
    duplicates.append(obj)
assert all(sum(1 for group in obj.data.vertices[0].groups) == 1 for obj in duplicates if obj.data.vertices)
assert weights["head"] > 1000 and weights["spine"] > 1000
bpy.ops.object.select_all(action="DESELECT")
for obj in duplicates:
    obj.select_set(True)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
mesh = bpy.context.object
mesh.name = "SK_NyaagyuSamurai"
assert len(mesh.data.vertices) == sum(weights.values())
assert all(len(vertex.groups) == 1 for vertex in mesh.data.vertices)

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
rig = bpy.context.object
rig.name = "RIG_NyaagyuSamurai"
bones = rig.data.edit_bones
bones.remove(bones[0])


def bone(name, head, tail, parent=None):
    b = bones.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = bones[parent]


bone("root", (0, 0, 0), (0, 0, .20))
bone("pelvis", (0, 0, .65), (0, 0, .85), "root")
bone("spine", (0, 0, .85), (0, 0, 1.19), "pelvis")
bone("neck", (0, 0, 1.19), (0, 0, 1.39), "spine")
bone("head", (0, 0, 1.39), (0, 0, 1.75), "neck")
bone("tail_01", (-.12, 0, .70), (-.30, 0, .78), "pelvis")
bone("tail_02", (-.30, 0, .78), (-.48, 0, .9), "tail_01")
bone("tail_03", (-.48, 0, .9), (-.63, 0, 1.03), "tail_02")
for side, sign in (("L", -1), ("R", 1)):
    bone(f"upperarm_{side}", (0, sign * .23, 1.24), (.035, sign * .34, 1.01), "spine")
    bone(f"forearm_{side}", (.035, sign * .34, 1.01), (.085, sign * .38, .83), f"upperarm_{side}")
    bone(f"hand_{side}", (.085, sign * .38, .83), (.09, sign * .39, .73), f"forearm_{side}")
    bone(f"thigh_{side}", (0, sign * .14, .66), (0, sign * .15, .36), "pelvis")
    bone(f"shin_{side}", (0, sign * .15, .36), (0, sign * .15, .10), f"thigh_{side}")
    bone(f"foot_{side}", (0, sign * .15, .10), (.18, sign * .15, .055), f"shin_{side}")
bpy.ops.object.mode_set(mode="OBJECT")
assert len(rig.data.bones) == 20 and set(all_bones) == set(rig.data.bones.keys())
modifier = mesh.modifiers.new("Nyaakoto_SourcePartSkin", "ARMATURE")
modifier.object = rig
mesh.parent = rig
rig.animation_data_create()
actions = {}
# Keep the painted iris packed in the editable runtime .blend, but omit its
# image node while exporting FBX. Blender otherwise embeds the artist's
# absolute workstation path even with path_mode="STRIP".
iris_nodes = bpy.data.materials["M_Hero_BlueEye"].node_tree.nodes
iris_links = bpy.data.materials["M_Hero_BlueEye"].node_tree.links
iris_node = iris_nodes["Painted radial iris pigment"]
iris_image = iris_node.image
iris_nodes.remove(iris_node)
for clip, frames in (("Idle", 96), ("Walk", 32)):
    action = bpy.data.actions.new(rig.name + "_" + clip)
    action.use_fake_user = True
    rig.animation_data.action = action
    for pose in rig.pose.bones:
        pose.rotation_mode = "XYZ"
        pose.rotation_euler = (0, 0, 0)
        pose.location = (0, 0, 0)
    for frame in range(1, frames + 2, 4):
        t = (frame - 1) / frames * math.tau
        for side, sign in (("L", -1), ("R", 1)):
            rig.pose.bones[f"thigh_{side}"].rotation_euler[2] = math.sin(t) * .24 * sign if clip == "Walk" else 0
            rig.pose.bones[f"shin_{side}"].rotation_euler[2] = max(0, -math.sin(t) * sign) * .30 if clip == "Walk" else 0
            rig.pose.bones[f"upperarm_{side}"].rotation_euler[2] = -math.sin(t) * .12 * sign if clip == "Walk" else math.sin(t) * .006
        rig.pose.bones["pelvis"].location[1] = abs(math.sin(t)) * .009 if clip == "Walk" else math.sin(t) * .003
        rig.pose.bones["spine"].rotation_euler[0] = math.sin(t) * .009
        rig.pose.bones["tail_02"].rotation_euler[0] = math.sin(t) * .08
        for pose in rig.pose.bones:
            pose.keyframe_insert(data_path="rotation_euler", frame=frame, group=pose.name)
            pose.keyframe_insert(data_path="location", frame=frame, group=pose.name)
    actions[clip] = action
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = frames + 1
    bpy.context.scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    filename = "SK_NyaagyuSamurai.fbx" if clip == "Idle" else "A_NyaagyuSamurai_Walk.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / filename), use_selection=True,
        object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z",
        apply_unit_scale=True, add_leaf_bones=False, use_armature_deform_only=True,
        bake_anim=True, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_simplify_factor=0,
        path_mode="STRIP")
iris_node = iris_nodes.new("ShaderNodeTexImage")
iris_node.name = "Painted radial iris pigment"
iris_node.image = iris_image
iris_links.new(iris_node.outputs["Color"], iris_nodes["Principled BSDF"].inputs["Base Color"])
iris_links.new(iris_node.outputs["Color"], iris_nodes["Bump"].inputs["Height"])
rig.animation_data.action = actions["Idle"]
bpy.context.scene.frame_set(1)
for src in parts:
    src.hide_render = True
    src.hide_set(True)
runtime_blend = HERO / "Nyaakoto_RuntimeSkin.blend"
preview = HERO / "Nyaakoto_RuntimeSkin_Blender.png"
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 32
bpy.context.scene.render.resolution_x = 1000
bpy.context.scene.render.resolution_y = 1200
bpy.context.scene.render.resolution_percentage = 100
bpy.context.scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(runtime_blend))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

record = {
    "schema_version": 1,
    "generator": "scripts/art/rig_nyaakoto_runtime.py",
    "source_blend": str(SOURCE.relative_to(ROOT)),
    "source_blend_sha256": source_record["blend_sha256"],
    "runtime_blend": runtime_blend.name,
    "runtime_blend_sha256": sha(runtime_blend),
    "runtime_preview": preview.name,
    "runtime_preview_sha256": sha(preview),
    "source_parts": len(parts),
    "source_vertices": len(mesh.data.vertices),
    "source_triangles": source_record["source_triangles"],
    "skeletal_fbx": "SK_NyaagyuSamurai.fbx",
    "skeletal_fbx_sha256": sha(OUT / "SK_NyaagyuSamurai.fbx"),
    "walk_fbx": "A_NyaagyuSamurai_Walk.fbx",
    "walk_fbx_sha256": sha(OUT / "A_NyaagyuSamurai_Walk.fbx"),
    "skeleton_bones": all_bones,
    "sora_kamon_svg_sha256": source_record["insignia_sha256"],
    "sora_kamon_placements": source_record["sora_kamon_placements"],
    "head_weighted_vertices": weights["head"],
    "rigging": "20-bone inherited runtime skeleton; rigid source-part skin; idle/walk only",
    "limitations": "No production deformation, lip sync, authored combat animation, strand groom, UE 5.8.2 visual review, or photoreal quality qualification. Bow and sheathed katana are back/hip presentation geometry, not interactive draw or mounting rigs.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAKOTO_RUNTIME_SKIN_COMPLETE", len(parts), len(mesh.data.vertices), len(rig.data.bones), weights["head"])
