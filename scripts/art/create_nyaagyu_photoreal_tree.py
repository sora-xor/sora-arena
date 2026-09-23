"""Build a game-ready, editable Nyaagyu tree from Poly Haven's CC0 scan.

The complete upstream 1K glTF source and its geometry are stored under
Content/SourceArt/Environment/PolyHaven/TreeSmall02/Upstream. The game uses
our reduced HI/MAC meshes with separately pinned 2K PBR textures. Run:

  blender -b --python scripts/art/create_nyaagyu_photoreal_tree.py

This script does not fetch assets or change gameplay collision. It keeps the
model's three material zones and bakes its branch UV transform for Unreal.
"""
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/TreeSmall02"
UPSTREAM = ART / "Upstream"
TEXTURES = ART / "Textures"
SOURCE = UPSTREAM / "tree_small_02_1k.gltf"
MATERIALS = {
    "tree_small_02_branches": ("Branches", "branch", "branch_nor_gl"),
    "tree_small_02_leaves": ("Leaves", "leaves", "leaves_nor_gl"),
    "tree_small_02_trunk": ("Trunk", "", "nor_gl"),
}
UPSTREAM_SHA256 = {
    "tree_small_02_1k.gltf": "3062a709614c05b80fdc1e56583998bc3cb1027b0d52f956c8ecfb882ff8ca6d",
    "tree_small_02.bin": "8da6c3c389ad8748286d1b7488cd827f75ebdad9d8f59ef7dfb0916df5edc634",
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


for name, expected in UPSTREAM_SHA256.items():
    assert digest(UPSTREAM / name) == expected, f"Upstream geometry changed: {name}"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
source = next(obj for obj in bpy.data.objects if obj.type == "MESH" and obj.name == "tree_small_02_LOD0")
assert sum(len(poly.vertices) - 2 for poly in source.data.polygons) == 2062487

bpy.ops.object.select_all(action="DESELECT")
source.select_set(True)
bpy.context.view_layer.objects.active = source
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="MATERIAL")
bpy.ops.object.mode_set(mode="OBJECT")
parts = {}
for obj in [obj for obj in bpy.data.objects if obj.type == "MESH"]:
    assert len(obj.data.materials) == 1
    source_name = obj.data.materials[0].name
    assert source_name in MATERIALS and source_name not in parts
    parts[source_name] = obj
assert set(parts) == set(MATERIALS)


def texture(name):
    path = TEXTURES / f"tree_small_02_{name}_2k.jpg"
    assert path.is_file(), path
    image = bpy.data.images.load(str(path), check_existing=True)
    return image


def material(role, prefix, normal_name):
    mat = bpy.data.materials.new(f"M_NyaagyuTree_{role}")
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    nodes.clear()
    links = mat.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    stem = prefix + "_" if prefix else ""
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = texture(stem + "diff")
    links.new(albedo.outputs["Color"], shader.inputs["Base Color"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.image = texture(stem + "arm")
    arm.image.colorspace_settings.name = "Non-Color"
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    normal = nodes.new("ShaderNodeTexImage")
    # The editable Blender source uses upstream OpenGL normals. The Unreal
    # material uses separately pinned 2K DirectX normal maps.
    normal.image = bpy.data.images.load(
        str(UPSTREAM / "textures" / f"tree_small_02_{normal_name}_1k.jpg"),
        check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    if role == "Leaves":
        alpha_path = TEXTURES / "tree_small_02_leaves_alpha_2k.png"
        alpha = nodes.new("ShaderNodeTexImage")
        alpha.image = bpy.data.images.load(str(alpha_path), check_existing=True)
        alpha.image.colorspace_settings.name = "Non-Color"
        links.new(alpha.outputs["Color"], shader.inputs["Alpha"])
        mat.surface_render_method = "DITHERED"
    return mat


for source_name, obj in parts.items():
    role, prefix, normal_name = MATERIALS[source_name]
    obj.name = f"NyaagyuTree_{role}_HI"
    # KHR_texture_transform on the branch atlas is (3, .6) + (0, .4),
    # applied to TEXCOORD_1. Baking it to UV0 makes FBX/UE import unambiguous.
    primary = obj.data.uv_layers["UVMap"]
    if role == "Branches":
        secondary = obj.data.uv_layers["UVMap.001"]
        for a, b in zip(primary.data, secondary.data):
            a.uv = (b.uv.x * 3.0, b.uv.y * .6 + .4)
    obj.data.uv_layers.remove(obj.data.uv_layers["UVMap.001"])
    obj.data.materials.clear()
    obj.data.materials.append(material(role, prefix, normal_name))
    assert len(obj.data.uv_layers) == 1


def decimate(obj, ratio):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("Preserve_scanned_silhouette", "DECIMATE")
    modifier.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


# Preserve the bark/trunk while thinning the dense scanned leaf geometry.
# Each tier is an actual authored mesh, so Mac never relies on Nanite fallback.
hi_ratios = {"Branches": .60, "Leaves": .14, "Trunk": .90}
hi_parts = []
for source_name, obj in parts.items():
    role = MATERIALS[source_name][0]
    count = decimate(obj, hi_ratios[role])
    print("TREE_HI_PART", role, count, flush=True)
    hi_parts.append(obj)

mac_ratios = {"Branches": .35, "Leaves": .22, "Trunk": .60}
mac_parts = []
for source_part in hi_parts:
    role = source_part.name.split("_")[1]
    copy = source_part.copy()
    copy.data = source_part.data.copy()
    bpy.context.collection.objects.link(copy)
    copy.name = f"NyaagyuTree_{role}_MAC"
    count = decimate(copy, mac_ratios[role])
    print("TREE_MAC_PART", role, count, flush=True)
    mac_parts.append(copy)


def joined(name, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = name
    assert len(merged.data.materials) == 3
    assert set(mat.name for mat in merged.data.materials) == {
        "M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"}
    return merged


hi = joined("SM_NyaagyuTree_HI", hi_parts)
mac = joined("SM_NyaagyuTree_MAC", mac_parts)
hi.hide_render = False
mac.hide_render = True
mac.hide_set(True)

# FBX needs only material slot identities: Unreal binds its own 2K PBR assets.
# Replace the preview materials with identically named untextured slots during
# export; Blender otherwise embeds machine-local image paths even when the
# export path mode is STRIP. Restore the real PBR nodes before render/save.
original_materials = {}
for obj in (hi, mac):
    original_materials[obj.name] = list(obj.data.materials)
slot_materials = {}
for mat in original_materials[hi.name]:
    name = mat.name
    mat.name = name + "_SourceReview"
    slot_materials[name] = bpy.data.materials.new(name)
for obj in (hi, mac):
    for index, original in enumerate(original_materials[obj.name]):
        obj.data.materials[index] = slot_materials[original.name.removesuffix("_SourceReview")]
records = []
for obj in (hi, mac):
    obj.hide_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = ART / f"{obj.name}.fbx"
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, global_scale=1.0, axis_forward="-Y", axis_up="Z",
        add_leaf_bones=False, bake_anim=False, path_mode="STRIP", embed_textures=False)
    verts = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = [round(min(v[i] for v in verts), 4) for i in range(3)]
    high = [round(max(v[i] for v in verts), 4) for i in range(3)]
    count = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
    assert low[2] > -.1 and high[2] > 4.45 and count > 50000
    records.append({"tier": "hi" if obj is hi else "mac", "name": obj.name,
                    "fbx": path.name, "fbx_sha256": digest(path),
                    "source_triangles": count, "bounds_m": {"min": low, "max": high},
                    "unreal_asset": f"/Game/Generated/Environment/Foliage/{obj.name}.{obj.name}",
                    "nanite": obj is hi})
    obj.hide_set(obj is mac)
for obj in (hi, mac):
    for index, original in enumerate(original_materials[obj.name]):
        obj.data.materials[index] = original
for original in original_materials[hi.name]:
    original.name = original.name.removesuffix("_SourceReview")
for temporary in slot_materials.values():
    bpy.data.materials.remove(temporary)

# A compact source-review preview is intentionally not a gameplay screenshot.
bpy.ops.mesh.primitive_plane_add(size=200)
ground = bpy.context.object
ground.name = "Preview_ground_only"
ground.location.z = -.02
preview_mat = bpy.data.materials.new("Preview_ground")
preview_mat.diffuse_color = (.28, .26, .20, 1)
ground.data.materials.append(preview_mat)
bpy.ops.object.camera_add(location=(7, -10, 6))
camera = bpy.context.object
direction = Vector((0, 0, 2.1)) - camera.location
camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 6.8
bpy.context.scene.camera = camera
for location, energy, size in (((-4, -5, 9), 1100, 7), ((4, 3, 7), 800, 5)):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector((0, 0, 2)) - light.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 760
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(ART / "Preview_NyaagyuTree.png")
scene.world = bpy.data.worlds.new("Soft_overcast_preview")
scene.world.color = (.32, .34, .36)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.filepath = bpy.path.relpath(str(Path(bpy.path.abspath(image.filepath)).resolve()),
                                          start=str(ART))
blend_path = ART / "NyaagyuTree_Source.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

upstream_records = []
for path in sorted(p for p in UPSTREAM.rglob("*") if p.is_file()):
    upstream_records.append({"path": str(path.relative_to(ART)), "bytes": path.stat().st_size,
                             "sha256": digest(path)})
texture_records = []
for path in sorted(TEXTURES.iterdir()):
    texture_records.append({"path": str(path.relative_to(ART)), "bytes": path.stat().st_size,
                            "sha256": digest(path)})
manifest = {
    "schema_version": 1,
    "asset_id": "tree_small_02",
    "upstream_page": "https://polyhaven.com/a/tree_small_02",
    "upstream_api": "https://api.polyhaven.com/files/tree_small_02",
    "license": "CC0-1.0; https://polyhaven.com/license",
    "authors": ["Rico Cilliers"],
    "generator": "scripts/art/create_nyaagyu_photoreal_tree.py",
    "description": "4.6 m scanned broadleaf tree; three PBR zones and cutout leaves; Nyaagyu campaign decoration only",
    "upstream_files": upstream_records,
    "texture_files": texture_records,
    "source_blend": blend_path.name,
    "source_blend_sha256": digest(blend_path),
    "preview": "Preview_NyaagyuTree.png",
    "preview_sha256": digest(ART / "Preview_NyaagyuTree.png"),
    "material_slots": ["M_NyaagyuTree_Branches", "M_NyaagyuTree_Leaves", "M_NyaagyuTree_Trunk"],
    "meshes": records,
    "instances_in_nyaagyu_estate": 10,
    "gameplay_collision": False,
}
(ART / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("SORA_PHOTOREAL_TREE_READY", [(r["tier"], r["source_triangles"]) for r in records], flush=True)
