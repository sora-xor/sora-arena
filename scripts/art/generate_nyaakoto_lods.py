"""Build authored Nyaakoto skeletal distance LODs from the editable Blender source.

Run: blender -b --factory-startup --python scripts/art/generate_nyaakoto_lods.py

LOD0 is deliberately untouched. LOD1 thins the actual fur triangle cards and
reduces selected curved volumes; LOD2 removes cards and ornamental micro-forms.
The same 20-bone armature, 23 material identities and exact vector kamon remain.

Every LOD carries LOD0's body (nyaakoto_runtime_parts.py, the third-person
grip contract's slice A): anatomical sides, the sheathed sword set and the
source's open paws left out. The furred paws are meshed again for each LOD at
its own step (nyaakoto_tp_paws.LOD_STEPS), and each LOD's PawEmpty_R and
PawEmpty_L shape keys come from the same rule as LOD0's (empty_points, a rule
of position), so the empty and holding states hold at every distance. The
bounds are LOD0's.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyaakoto_runtime_parts as RP  # noqa: E402
import nyaakoto_tp_paws as TPP  # noqa: E402


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
by_name = {obj.name: obj for obj in parts}
ARMS = RP.arm_joints(by_name)


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
    "Shoulder_joint_", "Heel_paw_", "Tabi_toe_paw_",
    "Toe_", "Soft_nose_bridge", "White_nose_blaze",
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
base_bounds = runtime_manifest["bounds_m"]                 # LOD0's: the runtime body, not the editable source
for level in (1, 2):
    collection = bpy.data.collections.new(f"Nyaakoto_LOD{level}_Export")
    bpy.context.scene.collection.children.link(collection)
    pieces = []
    paws = {side: RP.fur_paw(side, ARMS, by_name, step=TPP.LOD_STEPS[level]) for side in ("R", "L")}
    paw_side = {paws[side][0].name: k + 1 for k, side in enumerate(("R", "L"))}   # 1 right, 2 left; 0 the rest
    for src in [p for p in parts if RP.kept(p.name)] + [paws[side][0] for side in ("R", "L")]:
        name = src.name
        if level == 2 and (name.startswith(FUR_CARDS) or name.startswith(LOD2_OMIT)):
            continue
        fresh = name.startswith(RP.FRESH)
        obj = src if fresh else src.copy()
        if not fresh:
            obj.data = src.data.copy()
        collection.objects.link(obj)
        if not fresh:
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
        tag = obj.data.attributes.new("nyaakoto_paw_side", "INT", "POINT")   # which paw, through the join
        tag.data.foreach_set("value", [paw_side.get(name, 0)] * len(obj.data.vertices))
        group_names = tuple(rig.data.bones.keys())
        groups = {bone: obj.vertex_groups.new(name=bone) for bone in group_names}
        for vertex in obj.data.vertices:
            bone = RP.rig_bone(name, obj.matrix_world @ vertex.co)
            groups[bone].add([vertex.index], 1.0, "REPLACE")
        pieces.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    mesh = bpy.context.object
    mesh.name = f"SK_NyaagyuSamurai_LOD{level}"
    side_of = np.empty(len(mesh.data.vertices), np.int32)
    mesh.data.attributes["nyaakoto_paw_side"].data.foreach_get("value", side_of)
    mesh.data.attributes.remove(mesh.data.attributes["nyaakoto_paw_side"])
    # The empty fists: LOD0's rule on this LOD's own paw vertices, 0 at bind (Blender 5.2 starts a key at 1.0, s90).
    mw = np.array([list(r) for r in mesh.matrix_world])
    inv = np.linalg.inv(mw)
    co = np.empty(len(mesh.data.vertices) * 3, np.float32)
    mesh.data.vertices.foreach_get("co", co)
    world = co.reshape(-1, 3).astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]
    mesh.shape_key_add(name="Basis", from_mix=False)
    morph = {}
    for k, side in enumerate(("R", "L")):
        key = mesh.shape_key_add(name=f"PawEmpty_{side}", from_mix=False)
        key.value = 0.0
        idx = np.nonzero(side_of == k + 1)[0]
        assert len(idx) == len(paws[side][1]["verts"]), (level, side, len(idx), len(paws[side][1]["verts"]))
        kco = co.reshape(-1, 3).copy()
        kco[idx] = (TPP.empty_points(world[idx], paws[side][1]["skeleton"]) @ inv[:3, :3].T + inv[:3, 3]).astype(np.float32)
        key.data.foreach_set("co", kco.ravel())
        moved = np.linalg.norm(kco[idx] - co.reshape(-1, 3)[idx], axis=1)
        morph[f"PawEmpty_{side}"] = {"paw_vertices": int(len(idx)), "moved_vertices": int((moved > 1e-7).sum()),
                                     "max_move_cm": round(float(moved.max()) * 100.0, 3)}
    assert [(kb.name, kb.value) for kb in mesh.data.shape_keys.key_blocks[1:]] == [("PawEmpty_R", 0.0), ("PawEmpty_L", 0.0)]
    paw_records = {side: RP.fur_paw_record(side, ARMS, paws[side][1]) for side in ("R", "L")}
    assert not any(r["failed"] for r in paw_records.values()), paw_records
    coat=mesh.data.color_attributes.get("CoatBlend")
    assert coat is not None and coat.domain=="CORNER"
    mesh.data.color_attributes.active_color=coat
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
        bake_anim=False, path_mode="STRIP", prioritize_active_color=True)
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
        "part_rules": "nyaakoto_runtime_parts.py: LOD0's body (slice A)",
        "paws": {"step_m": TPP.LOD_STEPS[level], "by_side": paw_records},
        "morph_targets": morph,
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
