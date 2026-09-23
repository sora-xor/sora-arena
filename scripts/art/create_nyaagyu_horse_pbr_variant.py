"""UV and shade the current horse without changing its editable geometry.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_pbr_variant.py

This produces a separate source/render/FBX so the historical tack study and
its provenance remain intact. The horse is still static and anatomically
stylized; this pass improves its surface response.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
HORSE = ROOT / "Content/SourceArt/Horses/Nyaagyu"
PBR = HORSE / "PBR"
BASE = json.loads((HORSE / "manifest.json").read_text())
MATERIALS = json.loads((PBR / "manifest.json").read_text())
BLEND = PBR / "Nyaagyu_HorseAndTack_PBR.blend"
FBX = PBR / "SM_Nyaagyu_HorseAndTack_PBR.fbx"
REVIEW = PBR / "Nyaagyu_HorseAndTack_PBR_Review.png"
BEFORE_ANATOMY = PBR / "Nyaagyu_HorseAndTack_PBR_BeforeAnatomy.png"
BEFORE_SECOND_PASS = PBR / "Nyaagyu_HorseAndTack_PBR_PreSecondPass.png"
MANIFEST = PBR / "variant_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(HORSE / BASE["source_blend"]) == BASE["blend_sha256"]
assert sha(HORSE / BASE["fbx"]) == BASE["fbx_sha256"]
assert MATERIALS["base_horse_blend_sha256"] == BASE["blend_sha256"]
assert MATERIALS["base_horse_fbx_sha256"] == BASE["fbx_sha256"]
assert MATERIALS["sora_logo_sha256"] == BASE["insignia_sha256"]
assert BEFORE_SECOND_PASS.stat().st_size > 1000
for item in MATERIALS["sources"]:
    assert sha(PBR / item["file"]) == item["sha256"]
for item in MATERIALS["maps"]:
    for entry in item["maps"]:
        assert sha(PBR / entry["file"]) == entry["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(HORSE / BASE["source_blend"]))
scene = bpy.context.scene
parts = bpy.data.collections["NyaagyuHorse_Editable"]
meshes = sorted((obj for obj in parts.objects if obj.type == "MESH"), key=lambda o: o.name)
assert len(meshes) == BASE["source_parts"]


def geometry_fingerprint() -> str:
    digest = hashlib.sha256()
    for obj in meshes:
        digest.update(obj.name.encode())
        digest.update("|".join(material.name for material in obj.data.materials).encode())
        for vert in obj.data.vertices:
            point = obj.matrix_world @ vert.co
            digest.update(("%.7f,%.7f,%.7f;" % tuple(point)).encode())
        for poly in obj.data.polygons:
            digest.update((",".join(str(index) for index in poly.vertices) + ";").encode())
    return digest.hexdigest()


geometry_before = geometry_fingerprint()
exact_kamon = sorted(obj.name for obj in meshes if obj.name.startswith("SORA_kamon_exact_svg_"))
assert len(exact_kamon) == 8
for name in exact_kamon:
    assert bpy.data.objects[name]["source_svg_sha256"] == BASE["insignia_sha256"]

# World-oriented planar UVs have a consistent physical scale on the editable
# parts. Each polygon chooses the projection whose normal faces most toward
# the viewer; seams are inherent to the procedural mapping, never welded into
# or used to alter the source geometry. The maps are exact-wrap textures.
for obj in meshes:
    uv_layer = obj.data.uv_layers.get("Nyaagyu_PBR_UV") or obj.data.uv_layers.new(name="Nyaagyu_PBR_UV")
    for poly in obj.data.polygons:
        material = obj.data.materials[poly.material_index].name
        if material.startswith("M_Horse_"):
            # Short equine coat should retain a single physical fiber scale
            # across torso, neck, head, and limbs. The prior split projection
            # made the neck conspicuously smooth next to long body strokes.
            scale = 10.5
        else:
            scale = 8.0
        normal = obj.matrix_world.to_3x3() @ poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        for loop_index in poly.loop_indices:
            point = obj.matrix_world @ obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            if obj.name == "Horse_anatomical_core":
                # One continuous side projection avoids per-face axis flips on
                # the voxel-welded shoulder and throat. These tiny polygons
                # otherwise produce large pale mapping islands in the coat.
                u, v = point.x, point.z
            elif axis == 0:
                u, v = point.y, point.z
            elif axis == 1:
                u, v = point.x, point.z
            else:
                u, v = point.x, point.y
            uv_layer.data[loop_index].uv = (u * scale, v * scale)

assert geometry_fingerprint() == geometry_before

sets = {entry["name"]: {entry2["channel"]: PBR / entry2["file"] for entry2 in entry["maps"]}
        for entry in MATERIALS["maps"]}


def map_image(path: Path, non_color: bool):
    image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


for slot, config in MATERIALS["material_slots"].items():
    material = bpy.data.materials[slot]
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    bsdf = nodes.get("Principled BSDF")
    assert bsdf is not None
    for node in list(nodes):
        if node != bsdf and node.type != "OUTPUT_MATERIAL":
            nodes.remove(node)
    tex = sets[config["surface"]]
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.name = "Project_owned_albedo"
    albedo.image = map_image(tex["Albedo"], False)
    albedo.location = (-760, 240)
    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.name = "Material_slot_tint"
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    tint = config["tint"]
    multiply.inputs[2].default_value = (*tint, 1)
    multiply.location = (-460, 240)
    links.new(albedo.outputs["Color"], multiply.inputs[1])
    links.new(multiply.outputs["Color"], bsdf.inputs["Base Color"])

    packed = nodes.new("ShaderNodeTexImage")
    packed.name = "Project_owned_ORM"
    packed.image = map_image(tex["ORM"], True)
    packed.location = (-760, -50)
    orm = nodes.new("ShaderNodeSeparateColor")
    orm.mode = "RGB"
    orm.location = (-460, -50)
    links.new(packed.outputs["Color"], orm.inputs["Color"])
    links.new(orm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(orm.outputs["Blue"], bsdf.inputs["Metallic"])

    normal_image = nodes.new("ShaderNodeTexImage")
    normal_image.name = "Project_owned_NormalDX"
    normal_image.image = map_image(tex["NormalDX"], True)
    normal_image.location = (-760, -330)
    channels = nodes.new("ShaderNodeSeparateColor")
    channels.mode = "RGB"
    channels.location = (-460, -310)
    links.new(normal_image.outputs["Color"], channels.inputs["Color"])
    reverse_green = nodes.new("ShaderNodeMath")
    reverse_green.operation = "SUBTRACT"
    reverse_green.inputs[0].default_value = 1.0
    links.new(channels.outputs["Green"], reverse_green.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    combine.mode = "RGB"
    links.new(channels.outputs["Red"], combine.inputs["Red"])
    links.new(reverse_green.outputs[0], combine.inputs["Green"])
    links.new(channels.outputs["Blue"], combine.inputs["Blue"])
    bump = nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = .38
    links.new(combine.outputs["Color"], bump.inputs["Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

# The original static export is hidden in the editable source. Export a
# separate joined PBR mesh while leaving the individually named parts and
# all six gameplay attachment anchors in the new .blend.
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
bpy.ops.object.join()
export = bpy.context.object
export.name = "SM_Nyaagyu_HorseAndTack_PBR"
for collection in tuple(export.users_collection):
    collection.objects.unlink(export)
export_collection = bpy.data.collections["Unreal_Export_Only"]
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(
    filepath=str(FBX), use_selection=True, object_types={"MESH"},
    add_leaf_bones=False, apply_unit_scale=True, axis_forward="-Y", axis_up="Z",
    path_mode="STRIP",
)
# Blender records the currently opened .blend pathname in an FBX document
# metadata string even with STRIP texture paths. Replace that metadata value
# with the project-relative source identity at identical byte length; this
# does not touch vertices, UVs, materials, or any FBX length field.
fbx_bytes = FBX.read_bytes()
absolute_blend = str(HORSE / BASE["source_blend"]).encode()
relative_blend = ("Content/SourceArt/Horses/Nyaagyu/" + BASE["source_blend"]).encode()
assert fbx_bytes.count(absolute_blend) == 1
assert len(relative_blend) <= len(absolute_blend)
FBX.write_bytes(fbx_bytes.replace(absolute_blend, relative_blend.ljust(len(absolute_blend), b" ")))
export.hide_render = True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")

scene.render.filepath = str(REVIEW)
scene.cycles.samples = 32
bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

assert geometry_fingerprint() == geometry_before
assert all(obj.data.uv_layers.get("Nyaagyu_PBR_UV") for obj in meshes)
assert sorted(material.name for material in export.data.materials) == sorted(
    material.name for material in bpy.data.materials
    if material.name.startswith(("M_Horse_", "M_Tack_"))
)

record = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_horse_pbr_variant.py",
    "base_blend_sha256": BASE["blend_sha256"],
    "base_fbx_sha256": BASE["fbx_sha256"],
    "pbr_manifest_sha256": sha(PBR / "manifest.json"),
    "blend": BLEND.name, "blend_sha256": sha(BLEND),
    "fbx": FBX.name, "fbx_sha256": sha(FBX),
    "review": REVIEW.name, "review_sha256": sha(REVIEW),
    "before_anatomy_review": BEFORE_ANATOMY.name,
    "before_anatomy_review_sha256": sha(BEFORE_ANATOMY),
    "before_second_pass_review": BEFORE_SECOND_PASS.name,
    "before_second_pass_review_sha256": sha(BEFORE_SECOND_PASS),
    "source_parts": len(meshes),
    "source_triangles": sum(len(poly.vertices) - 2 for obj in meshes for poly in obj.data.polygons),
    "source_geometry_sha256": geometry_before,
    "material_slots": sorted(material.name for material in export.data.materials),
    "exact_sora_kamon_objects": exact_kamon,
    "sora_logo_sha256": BASE["insignia_sha256"],
    "anchors_m": BASE["anchors_m"],
    "unreal_asset": "/Game/ArtReview/Horses/NyaagyuPBR/SM_Nyaagyu_HorseAndTack_PBR.SM_Nyaagyu_HorseAndTack_PBR",
    "limitations": "Material/UV variant of the welded-body static horse source. Unrigged anatomy/tack remains stylized; no measured equine groom, tack wear scan, animation, riding simulation, or UE import validation.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_HORSE_PBR_VARIANT_COMPLETE", len(meshes), geometry_before, sha(FBX))
