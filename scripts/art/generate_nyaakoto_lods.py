"""Build authored Nyaakoto skeletal distance LODs from the editable Blender source.

Run: blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py

LOD0 is deliberately untouched. LOD1 thins the actual fur triangle cards and
reduces selected curved volumes; LOD2 removes cards and ornamental micro-forms.
The same 20-bone armature, 23 material identities and exact vector kamon remain.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Content/SourceArt"
HERO = SOURCE / "Characters/Hero"
OUT = HERO / "LOD"
OUT.mkdir(parents=True, exist_ok=True)
RUNTIME = HERO / "Nyaakoto_RuntimeSkin.blend"
runtime_manifest = json.loads((HERO / "runtime_skin_manifest.json").read_text())
source_manifest = json.loads((HERO / "manifest.json").read_text())
pbr_manifest = json.loads((HERO / "PBR/manifest.json").read_text())
assert hashlib.sha256(RUNTIME.read_bytes()).hexdigest() == runtime_manifest["runtime_blend_sha256"]
assert runtime_manifest["source_blend_sha256"] == source_manifest["blend_sha256"]
bpy.ops.wm.open_mainfile(filepath=str(RUNTIME))
source = bpy.data.collections["NyaagyuHero_Editable"]
parts = sorted((obj for obj in source.objects if obj.type == "MESH"), key=lambda obj: obj.name)
assert len(parts) == source_manifest["source_parts"]
rig = bpy.data.objects["RIG_NyaagyuSamurai"]
assert len(rig.data.bones) == 20
rig.animation_data.action = None
# The editable runtime blend retains its packed eye painting. Exported FBXs
# retain the material identity/UVs but must not contain a local image path.
iris_nodes = bpy.data.materials["M_Hero_BlueEye"].node_tree.nodes
iris_node = iris_nodes.get("Painted radial iris pigment")
assert iris_node is not None
iris_nodes.remove(iris_node)


def rig_bone(name: str, p: Vector) -> str:
    if name.startswith(("UserSupplied_SORAKamon_sode_", "Sode_kamon_backing_")):
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
        return "tail_01" if p.x > -.34 else "tail_02" if p.x > -.49 else "tail_03"
    if name.startswith(("Saya_", "Sageo_", "Katana_", "Obi_", "Resistance_sash", "Clan_mon", "Layered_hakama")):
        return "pelvis"
    if name.startswith(("Ebira_", "Ya_", "Yumi_", "Resistance_insignia", "Linen_under", "Indigo_samurai", "Under_kimono", "Do_")):
        return "spine"
    side = "L" if p.y < 0 else "R"
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
    raise ValueError(f"Unclassified Nyaakoto LOD part: {name}")


FUR_CARDS = (
    "Head_tabby_stripe_fibers", "Head_face_mesh_fur",
    "Head_short_mesh_fur", "Head_white_mesh_fur",
    "Head_transition_mesh_fur", "Cheek_mesh_fur_", "Muzzle_mesh_fur_",
    "Fur_neck_mesh_fur_", "Ear_rim_fur_", "Ear_inner_fur_",
)
LOD2_OMIT = (
    "Guard_hair_", "Muzzle_follicle_", "Ear_rim_fur_", "Ear_inner_fur_",
    "Fur_neck_mesh_fur_",
    "Eye_upper_lid_", "Eye_lower_lid_", "Angular_brow_",
    "Do_rivet_", "Sode_rivet_", "Do_indigo_lacing_",
    "Greave_braid_", "Kote_binding_", "Hakama_fold_",
    "Yumi_grip_rattan_", "Katana_tsukamaki_cross_",
    "Ebira_lacing_",
)
CURVED = (
    "Skull", "Lower_jaw", "Cheek_ruff_", "Muzzle_pad_", "Eye_socket_",
    "Eye_iris_", "Vertical_pupil_", "Fur_neck", "White_throat_bib",
    "Shoulder_joint_", "Paw_hand_", "Heel_paw_", "Tabi_toe_paw_",
    "Toe_", "Finger_knuckle_", "Soft_nose_bridge", "White_nose_blaze",
    "Triangular_nose", "Tail_white_tip", "Clan_mon_roundel",
)


def thin_cards(obj, stride: int) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    discarded = [face for index, face in enumerate(bm.faces) if index % stride]
    bmesh.ops.delete(bm, geom=discarded, context="FACES")
    bmesh.ops.delete(bm, geom=[vertex for vertex in bm.verts if not vertex.link_faces],
                     context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


records = []
base_bounds = source_manifest["bounds_m"]
for level in (1, 2):
    collection = bpy.data.collections.new(f"Nyaakoto_LOD{level}_Export")
    bpy.context.scene.collection.children.link(collection)
    pieces = []
    for src in parts:
        name = src.name
        if level == 2 and (name.startswith(FUR_CARDS) or name.startswith(LOD2_OMIT)):
            continue
        obj = src.copy()
        obj.data = src.data.copy()
        collection.objects.link(obj)
        obj.matrix_world = src.matrix_world.copy()
        obj.hide_set(False)
        obj.hide_render = False
        if level == 1 and name.startswith(FUR_CARDS):
            thin_cards(obj, 5)
        elif name.startswith(CURVED) and len(obj.data.vertices) >= 160:
            modifier = obj.modifiers.new(f"LOD{level}_volume_reduction", "DECIMATE")
            modifier.ratio = .75 if level == 1 else .38
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        if not obj.data.vertices:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue
        if not obj.data.uv_layers:
            uv = obj.data.uv_layers.new(name="UVMap")
            for loop in obj.data.loops:
                p = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
                uv.data[loop.index].uv = ((p.y + .8) * 2.4, (p.z - .55) * 2.4)
        group_names = tuple(rig.data.bones.keys())
        groups = {bone: obj.vertex_groups.new(name=bone) for bone in group_names}
        for vertex in obj.data.vertices:
            bone = rig_bone(name, obj.matrix_world @ vertex.co)
            groups[bone].add([vertex.index], 1.0, "REPLACE")
        pieces.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    mesh = bpy.context.object
    mesh.name = f"SK_NyaagyuSamurai_LOD{level}"
    assert all(len(vertex.groups) == 1 for vertex in mesh.data.vertices)
    material_names = {material.name for material in mesh.data.materials}
    assert material_names == set(pbr_manifest["material_slots"]), material_names
    corners = [mesh.matrix_world @ Vector(point) for point in mesh.bound_box]
    bounds = {
        axis: [round(min(point[index] for point in corners), 4),
               round(max(point[index] for point in corners), 4)]
        for index, axis in enumerate("xyz")
    }
    for index, axis in enumerate("xyz"):
        assert math.isclose(bounds[axis][0], base_bounds["min"][index], abs_tol=.015)
        assert math.isclose(bounds[axis][1], base_bounds["max"][index], abs_tol=.015)
    modifier = mesh.modifiers.new("Nyaakoto_LOD_Skin", "ARMATURE")
    modifier.object = rig
    mesh.parent = rig
    mesh.hide_set(False)
    mesh.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    filename = f"SK_NyaagyuSamurai_LOD{level}.fbx"
    path = OUT / filename
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True,
        object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z",
        apply_unit_scale=True, add_leaf_bones=False, use_armature_deform_only=True,
        bake_anim=False, path_mode="STRIP")
    records.append({
        "level": level,
        "fbx": filename,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_parts": len(pieces),
        "vertices": len(mesh.data.vertices),
        "triangles": sum(len(face.vertices) - 2 for face in mesh.data.polygons),
        "bounds_m": bounds,
        "material_slots": sorted(material_names),
        "bone_names": sorted(rig.data.bones.keys()),
        "card_fur": "20% sampled source triangle cards" if level == 1 else "none; surface normal maps only",
    })
    mesh.hide_set(True)
    mesh.hide_render = True

manifest = {
    "schema_version": 1,
    "generator": "scripts/art/generate_nyaakoto_lods.py",
    "source_blend_sha256": runtime_manifest["runtime_blend_sha256"],
    "lod0_fbx_sha256": runtime_manifest["skeletal_fbx_sha256"],
    "sora_kamon_svg_sha256": runtime_manifest["sora_kamon_svg_sha256"],
    "lods": records,
    "license": "Original project-owned source geometry and distance LODs; user-supplied SORA crest retained exactly",
    "limitations": "LOD0 remains dense at close range. LOD1/2 are authored FBXs; cooked use requires Unreal LOD import and a package test. Screen-size thresholds and M1 Ultra frame cost need in-game measurement.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAKOTO_LODS_CREATED", [(r["level"], r["vertices"], r["triangles"]) for r in records])
