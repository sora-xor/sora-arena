"""Adapt Poly Haven's pinned CC0 Fern 02 scan for Estate source-art review.

Run with Blender 5.2 LTS:
    blender -b --factory-startup --python scripts/art/create_nyaagyu_fern_shoulder.py

This deliberately does not import assets into Unreal or place campaign collision.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/Fern02"
UP = ART / "Upstream"
GLTF = UP / "fern_02_4k.gltf"
SOURCE_HASH = "7d5d458d4be38edceff922586234fa906377db5257e66d7cdde34b37e79788f7"
GROUND_DIFF = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing/ScanForestLeaves02/forest_leaves_02_diffuse_2k.jpg"
GROUND_ARM = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing/ScanForestLeaves02/forest_leaves_02_arm_2k.png"
GROUND_NORMAL = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing/ScanForestLeaves02/forest_leaves_02_nor_dx_2k.png"


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def md5(path: Path) -> str:
    value = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def official_url(path: Path) -> str:
    if path.name == "fern_02_4k.gltf":
        return "https://dl.polyhaven.org/file/ph-assets/Models/gltf/4k/fern_02/fern_02_4k.gltf"
    if path.name == "fern_02.bin":
        return "https://dl.polyhaven.org/file/ph-assets/Models/gltf/8k/fern_02/fern_02.bin"
    tier = "4k" if "_4k." in path.name else "2k"
    fmt = path.suffix.removeprefix(".")
    assert fmt in ("jpg", "png")
    return f"https://dl.polyhaven.org/file/ph-assets/Models/{fmt}/{tier}/fern_02/{path.name}"


assert sha(GLTF) == SOURCE_HASH
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(GLTF))
originals = {letter: bpy.data.objects[f"fern_02_{letter}"] for letter in "abcd"}
expected_source_tris = {"a": 784, "b": 2384, "c": 2248, "d": 816}
assert {letter: len(obj.data.polygons) for letter, obj in originals.items()} == expected_source_tris


def image(name: str, tier: str, *, normal_gl: bool = False):
    extension = "png" if name == "alpha" else "jpg"
    suffix = "nor_gl" if normal_gl else name
    path = UP / "textures" / f"fern_02_{suffix}_{tier}.{extension}"
    assert path.is_file(), path
    loaded = bpy.data.images.load(str(path), check_existing=True)
    if name in ("alpha", "arm", "nor_dx", "nor_gl"):
        loaded.colorspace_settings.name = "Non-Color"
    return loaded


def fern_material(tier: str):
    mat = bpy.data.materials.new(f"M_NyaagyuFern02_{tier.upper()}")
    mat.use_nodes = True
    mat.use_backface_culling = False
    mat.surface_render_method = "DITHERED"
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0.0
    shader.inputs["Roughness"].default_value = 0.75
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    albedo = nodes.new("ShaderNodeTexImage")
    albedo.label = "CC0 scanned frond albedo"
    albedo.image = image("diff", tier)
    links.new(albedo.outputs["Color"], shader.inputs["Base Color"])
    mask = nodes.new("ShaderNodeTexImage")
    mask.label = "Separate official 4K/2K leaf mask; glTF JPEG alone lacks alpha"
    mask.image = image("alpha", tier)
    links.new(mask.outputs["Color"], shader.inputs["Alpha"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.image = image("arm", tier)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = image("nor_dx", tier, normal_gl=True)
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    return mat


material_4k = fern_material("4k")
material_2k = fern_material("2k")


def triangles(obj):
    return sum(len(face.vertices) - 2 for face in obj.data.polygons)


def world_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return ([round(min(p[i] for p in points), 5) for i in range(3)],
            [round(max(p[i] for p in points), 5) for i in range(3)])


def export(obj, path):
    # FBX material identity is stable; PBR texture binding is explicit in the
    # manifest and Unreal importer. Keep the editable .blend fully textured.
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
                             object_types={"MESH"}, apply_unit_scale=True,
                             axis_forward="-Y", axis_up="Z", bake_anim=False,
                             add_leaf_bones=False, path_mode="STRIP",
                             embed_textures=False)


def decimated_copy(obj, letter):
    copy = obj.copy()
    copy.data = obj.data.copy()
    bpy.context.collection.objects.link(copy)
    copy.name = f"SM_NyaagyuFern02_{letter.upper()}_MAC_LOD1"
    copy.data.materials.clear()
    copy.data.materials.append(material_2k)
    bpy.ops.object.select_all(action="DESELECT")
    copy.select_set(True)
    bpy.context.view_layer.objects.active = copy
    modifier = copy.modifiers.new("Conventional_MAC_distance_LOD1", "DECIMATE")
    modifier.ratio = 0.53
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    assert triangles(copy) < triangles(obj) * .70
    return copy


meshes = []
hi_parts = {}
mac_parts = {}
for letter, original in originals.items():
    # The upstream scene arranges four clumps in a 2 x 2 catalog. Bake each
    # object's transform and recenter its true footprint for independent use.
    transform = original.matrix_world.copy()
    points = [transform @ vertex.co for vertex in original.data.vertices]
    xmin = min(p.x for p in points)
    xmax = max(p.x for p in points)
    ymin = min(p.y for p in points)
    ymax = max(p.y for p in points)
    zmin = min(p.z for p in points)
    center = Vector(((xmin + xmax) * .5, (ymin + ymax) * .5, zmin))
    for vertex, point in zip(original.data.vertices, points):
        vertex.co = point - center
    original.matrix_world.identity()
    original.name = f"SM_NyaagyuFern02_{letter.upper()}_HI"
    original.data.materials.clear()
    original.data.materials.append(material_4k)
    hi_parts[letter] = original
    mac = decimated_copy(original, letter)
    mac_parts[letter] = mac
    for tier, mesh in (("HI", original), ("MAC_LOD1", mac)):
        mesh.hide_render = tier != "HI"
        low, high = world_bounds(mesh)
        assert -.01 < low[2] < .01 and .15 < high[2] < .5
        assert len(mesh.data.uv_layers) >= 1
        path = ART / f"{mesh.name}.fbx"
        export(mesh, path)
        meshes.append({"variant": letter, "tier": tier.lower(), "fbx": path.name,
                       "fbx_sha256": sha(path), "triangles": triangles(mesh),
                       "bounds_m": {"min": low, "max": high},
                       "material_slot": mesh.data.materials[0].name,
                       "nanite_candidate": tier == "HI"})

# Eight unlinked, varied-size clumps on one northern/right shoulder. This is a
# first-person composition study; placement is not written into WorldBuilder.
placements = [
    ("b", (.66, -1.02, .025), .10, 1.17),
    ("a", (1.48, -.72, .030), 1.85, .83),
    ("c", (.54, -.12, .038), -1.12, 1.04),
    ("d", (1.71, .30, .040), .64, .91),
    ("b", (1.06, .97, .045), 2.36, .68),
    ("a", (2.24, 1.34, .050), -.70, .91),
    ("d", (.47, 1.84, .055), 1.49, 1.12),
    ("c", (1.64, 2.21, .060), .28, .74),
]
preview_instances = []
for letter, location, angle, scale in placements:
    instance = hi_parts[letter].copy()
    instance.data = hi_parts[letter].data
    bpy.context.collection.objects.link(instance)
    instance.name = f"PreviewOnly_NorthernShoulder_{letter.upper()}"
    instance.location = location
    instance.rotation_euler.z = angle
    instance.scale = (scale, scale, scale)
    preview_instances.append((letter, instance))

# Hide export masters; the preview contains only independently placed
# clumps. The ground is an existing pinned CC0 scan, not part of the FBXs.
for mesh in hi_parts.values():
    mesh.hide_render = True


def ground_material():
    mat = bpy.data.materials.new("PreviewOnly_ForestLeaves02_ground")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    for path in (GROUND_DIFF, GROUND_ARM, GROUND_NORMAL):
        assert path.is_file(), path
    color = nodes.new("ShaderNodeTexImage")
    color.image = bpy.data.images.load(str(GROUND_DIFF), check_existing=True)
    links.new(color.outputs["Color"], shader.inputs["Base Color"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.image = bpy.data.images.load(str(GROUND_ARM), check_existing=True)
    arm.image.colorspace_settings.name = "Non-Color"
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    # Existing ground scan has a DirectX normal; Blender is OpenGL. Invert G
    # in shader for this preview. The source texture remains byte-identical.
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(GROUND_NORMAL), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    separate = nodes.new("ShaderNodeSeparateColor")
    links.new(normal.outputs["Color"], separate.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    links.new(separate.outputs["Green"], invert.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(separate.outputs["Red"], combine.inputs["Red"])
    links.new(invert.outputs[0], combine.inputs["Green"])
    links.new(separate.outputs["Blue"], combine.inputs["Blue"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(combine.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    return mat


# Slightly raised leaf-silt shoulder alongside a deliberately clear path.
vertices = []
faces = []
uvs = []
nx, ny = 100, 84
for yi in range(ny + 1):
    y = -5.0 + yi / ny * 13.0
    for xi in range(nx + 1):
        x = -5.0 + xi / nx * 13.0
        shoulder = .09 / (1 + math.exp(-6 * (x - .25)))
        irregular = .016 * math.sin(7 * x + 1.7 * y) + .012 * math.sin(10 * y + x)
        vertices.append((x, y, shoulder + irregular - .04))
        uvs.append((xi / nx * 2.9, yi / ny * 2.9))
for yi in range(ny):
    for xi in range(nx):
        a = yi * (nx + 1) + xi
        faces.append((a, a + 1, a + nx + 2, a + nx + 1))
mesh_data = bpy.data.meshes.new("PreviewOnly_ground_mesh")
mesh_data.from_pydata(vertices, [], faces)
mesh_data.update()
uv_layer = mesh_data.uv_layers.new(name="UV0")
for polygon in mesh_data.polygons:
    for loop_index in polygon.loop_indices:
        uv_layer.data[loop_index].uv = uvs[mesh_data.loops[loop_index].vertex_index]
ground = bpy.data.objects.new("PreviewOnly_scan_ground", mesh_data)
bpy.context.collection.objects.link(ground)
ground.data.materials.append(ground_material())

camera_at = Vector((-.28, -2.24, 1.63))
target = Vector((.95, .11, -.08))
bpy.ops.object.camera_add(location=camera_at)
camera = bpy.context.object
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 35
bpy.context.scene.camera = camera
world = bpy.data.worlds.new("PreviewOnly_overcast_world")
bpy.context.scene.world = world
world.color = (.46, .5, .56)
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.55, .6, .66, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .55
bpy.ops.object.light_add(type="AREA", location=(-1.5, -2.7, 3.9))
sun = bpy.context.object
sun.data.energy = 410
sun.data.shape = "DISK"
sun.data.size = 4.5
sun.rotation_euler = (Vector((1.0, .7, 0)) - sun.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.render.resolution_x = 1280
scene.render.resolution_y = 820
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(ART / "Preview_Fern02_EyeHeight_SourceOnly.png")
bpy.ops.render.render(write_still=True)
for letter, instance in preview_instances:
    instance.data = mac_parts[letter].data
scene.render.filepath = str(ART / "Preview_Fern02_MAC_Fallback_SourceOnly.png")
bpy.ops.render.render(write_still=True)
for letter, instance in preview_instances:
    instance.data = hi_parts[letter].data
scene.render.filepath = "//Preview_Fern02_EyeHeight_SourceOnly.png"

for loaded in bpy.data.images:
    if loaded.source == "FILE" and loaded.filepath:
        loaded.filepath = bpy.path.relpath(str(Path(bpy.path.abspath(loaded.filepath)).resolve()),
                                           start=str(ART))
blend = ART / "NyaagyuFern02_ShoulderStudy.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

manifest = {
    "schema_version": 1,
    "asset_id": "fern_02",
    "upstream_page": "https://polyhaven.com/a/fern_02",
    "upstream_api": "https://api.polyhaven.com/files/fern_02",
    "license": "CC0-1.0; https://polyhaven.com/license",
    "authors": {"Rob Tuytel": "scanning", "Rico Cilliers": "modeling"},
    "generator": "scripts/art/create_nyaagyu_fern_shoulder.py",
    "source_blend": blend.name,
    "source_blend_sha256": sha(blend),
    "preview": "Preview_Fern02_EyeHeight_SourceOnly.png",
    "preview_sha256": sha(ART / "Preview_Fern02_EyeHeight_SourceOnly.png"),
    "mac_fallback_preview": "Preview_Fern02_MAC_Fallback_SourceOnly.png",
    "mac_fallback_preview_sha256": sha(ART / "Preview_Fern02_MAC_Fallback_SourceOnly.png"),
    "source_tris_by_variant": expected_source_tris,
    "meshes": meshes,
    "review_eye_height_m": camera_at.z,
    "preview_placement_m": [{"variant": letter, "translation_m": loc,
                             "yaw_rad": angle, "scale": scale}
                            for letter, loc, angle, scale in placements],
    "campaign_placement_proposal_cm": {
        "status": "source-only; requires actual Unreal visual and collision review",
        "shoulder": "north/right, separated from WaterCourt southern/left cluster",
        "approximate_center": [-650, 1450, 0]
    },
    "gameplay_collision": False,
    "textures": {
        "4k": ["diff", "arm", "nor_gl", "nor_dx", "alpha"],
        "2k": ["diff", "arm", "nor_gl", "nor_dx", "alpha"]
    },
    "upstream_files": []
}
for path in sorted(UP.rglob("*")):
    if path.is_file():
        manifest["upstream_files"].append({"path": str(path.relative_to(ART)),
                                           "official_url": official_url(path),
                                           "bytes": path.stat().st_size,
                                           "md5": md5(path),
                                           "sha256": sha(path)})
(ART / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("FERN02_SOURCE_READY", len(meshes), "exports", flush=True)
