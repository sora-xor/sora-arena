"""Build an editable, UV0-mapped oak material study of the dojo bokken.

The original combat mesh is left intact until this candidate passes a packaged
same-camera Unreal comparison. Geometry and contact dimensions are inherited
exactly; this pass authors the surface and its FBX texture-coordinate contract.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Weapons/Original"
OUT = ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR"
BASE_RECORD = json.loads((BASE / "manifest.json").read_text())
TEXTURES = json.loads((OUT / "texture_manifest.json").read_text())
BLEND = OUT / "Nyaagyu_DojoBokken_PBRStudy.blend"
FBX = OUT / "SM_Nyaagyu_DojoBokken_PBRStudy.fbx"
PREVIEW = OUT / "Nyaagyu_DojoBokken_PBRStudy_Blender.png"
MANIFEST = OUT / "manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert BASE_RECORD["name"] == "SM_Nyaagyu_DojoBokken"
assert sha(BASE / BASE_RECORD["source_blend"]) == BASE_RECORD["blend_sha256"]
assert sha(BASE / BASE_RECORD["fbx"]) == BASE_RECORD["fbx_sha256"]
assert TEXTURES["schema_version"] == 1
assert sha(OUT / TEXTURES["source"]) == TEXTURES["source_sha256"]
for item in TEXTURES["maps"].values():
    assert sha(OUT / item["file"]) == item["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(BASE / BASE_RECORD["source_blend"]))
collection = bpy.data.collections["DojoBokken_Editable"]
parts = sorted((obj for obj in collection.objects if obj.type == "MESH"), key=lambda obj: obj.name)
assert len(parts) == 16


def geometry_fingerprint() -> str:
    digest = hashlib.sha256()
    for obj in parts:
        digest.update(obj.name.encode())
        for vertex in obj.data.vertices:
            digest.update(("%.7f,%.7f,%.7f;" % tuple(obj.matrix_world @ vertex.co)).encode())
        for poly in obj.data.polygons:
            digest.update((",".join(str(value) for value in poly.vertices) + ";").encode())
    return digest.hexdigest()


geometry = geometry_fingerprint()
for obj in parts:
    # A single cylindrical seam runs under the hand-planed blank. The wood
    # fibers in the authored albedo run vertically along the sword's X axis.
    for old in tuple(obj.data.uv_layers):
        obj.data.uv_layers.remove(old)
    uv = obj.data.uv_layers.new(name="UV0")
    for poly in obj.data.polygons:
        material = obj.data.materials[poly.material_index].name
        for loop_index in poly.loop_indices:
            point = obj.matrix_world @ obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            if material == "M_Bokken_EndGrain":
                u, v = .5 + point.y / .13, .5 + point.z / .13
            else:
                angle = math.atan2(point.y, point.z - .008)
                u = angle / math.tau + .5
                v = (point.x + .310) / 1.067
            uv.data[loop_index].uv = (u, v)
    assert len(obj.data.uv_layers) == 1
assert geometry_fingerprint() == geometry


def image_for(channel: str, non_color: bool):
    path = OUT / TEXTURES["maps"][channel]["file"]
    image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    return image


albedo = image_for("Albedo", False)
normal = image_for("NormalDX", True)
orm = image_for("ORM", True)
tints = {
    "M_Bokken_SeasonedWhiteOak": (.90, .86, .80),
    "M_Bokken_HandOiledGrip": (.64, .56, .46),
    "M_Bokken_EndGrain": (.70, .60, .49),
    "M_Bokken_QuietWoodGrain": (.36, .29, .23),
}
for name, tint in tints.items():
    material = bpy.data.materials[name]
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Coat Weight"].default_value = .08
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = albedo
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1
    mix.inputs[2].default_value = (*tint, 1)
    links.new(tex.outputs["Color"], mix.inputs[1])
    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])

    packed = nodes.new("ShaderNodeTexImage")
    packed.image = orm
    channels = nodes.new("ShaderNodeSeparateColor")
    channels.mode = "RGB"
    links.new(packed.outputs["Color"], channels.inputs["Color"])
    links.new(channels.outputs["Green"], bsdf.inputs["Roughness"])

    normal_tex = nodes.new("ShaderNodeTexImage")
    normal_tex.image = normal
    split = nodes.new("ShaderNodeSeparateColor")
    split.mode = "RGB"
    links.new(normal_tex.outputs["Color"], split.inputs["Color"])
    invert_y = nodes.new("ShaderNodeMath")
    invert_y.operation = "SUBTRACT"
    invert_y.inputs[0].default_value = 1
    links.new(split.outputs["Green"], invert_y.inputs[1])
    rejoin = nodes.new("ShaderNodeCombineColor")
    rejoin.mode = "RGB"
    links.new(split.outputs["Red"], rejoin.inputs["Red"])
    links.new(invert_y.outputs[0], rejoin.inputs["Green"])
    links.new(split.outputs["Blue"], rejoin.inputs["Blue"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = .35
    links.new(rejoin.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    material.diffuse_color = (*tint, 1)

assert geometry_fingerprint() == geometry
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
duplicates = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
export = bpy.context.object
export.name = "SM_Nyaagyu_DojoBokken_PBRStudy"
bpy.ops.export_scene.fbx(
    filepath=str(FBX), use_selection=True, object_types={"MESH"},
    apply_unit_scale=True, global_scale=1.0, axis_forward="-Y", axis_up="Z",
    add_leaf_bones=False, bake_anim=False, path_mode="STRIP",
)
fbx_bytes = FBX.read_bytes()
source_path = str(BASE / BASE_RECORD["source_blend"]).encode()
relative_path = ("Content/SourceArt/Weapons/Original/" + BASE_RECORD["source_blend"]).encode()
assert fbx_bytes.count(source_path) == 1 and len(relative_path) <= len(source_path)
FBX.write_bytes(fbx_bytes.replace(source_path, relative_path.ljust(len(source_path), b" ")))
bpy.data.objects.remove(export, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")

scene = bpy.context.scene
scene.render.filepath = str(PREVIEW)
scene.cycles.samples = 48
bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

record = {
    "schema_version": 1,
    "generator": "scripts/art/create_dojo_bokken_pbr_study.py",
    "base_blend_sha256": BASE_RECORD["blend_sha256"],
    "base_fbx_sha256": BASE_RECORD["fbx_sha256"],
    "texture_manifest_sha256": sha(OUT / "texture_manifest.json"),
    "source_blend": BLEND.name,
    "blend_sha256": sha(BLEND),
    "fbx": FBX.name,
    "fbx_sha256": sha(FBX),
    "preview": PREVIEW.name,
    "preview_sha256": sha(PREVIEW),
    "geometry_sha256": geometry,
    "source_parts": len(parts),
    "source_triangles": sum(len(poly.vertices) - 2 for obj in parts for poly in obj.data.polygons),
    "material_slots": sorted(tints),
    "unreal_asset": "/Game/Generated/ArtReview/DojoBokkenPBR/SM_Nyaagyu_DojoBokken_PBRStudy.SM_Nyaagyu_DojoBokken_PBRStudy",
    "scope": "Editable material/UV study with unchanged combat geometry. No gameplay promotion until packaged UE 5.8.2 visual and performance review.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("DOJO_BOKKEN_PBR_STUDY_READY", geometry, sha(FBX))
