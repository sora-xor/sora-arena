"""Adapt three CC0 Poly Haven pine saplings into authored HI/Mac estate foliage.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_pine_saplings.py
The pinned upstream glTF and 2K PBR textures are stored in SourceArt. No
external fetch, paid asset, gameplay collision or landscape height change.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "Content/SourceArt/Environment/PolyHaven/PineSaplingSmall"
UP = ART / "Upstream"
TEX = ART / "Textures"
SOURCE = UP / "pine_sapling_small_1k.gltf"
PREFIX = "pine_sapling_small"
PINNED_SOURCE = {
    "pine_sapling_small_1k.gltf": "f358c01926861dd082f32dba60f7c9fba232b585a985cf38c0d2229eecf4bc48",
    "pine_sapling_small.bin": "b4d2fc73d53f1d8717eb5ef9a2c66957d2a53152787e543aace88fcd6fca94ef",
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


for filename, expected in PINNED_SOURCE.items():
    assert sha(UP / filename) == expected, filename

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
variants = {letter: bpy.data.objects[f"{PREFIX}_{letter}"] for letter in "abc"}
assert sum(sum(len(face.vertices) - 2 for face in obj.data.polygons)
           for obj in variants.values()) == 398144
assert all({m.name for m in obj.data.materials} ==
           {f"{PREFIX}_bark", f"{PREFIX}_twig"} for obj in variants.values())
for obj in tuple(bpy.data.objects):
    if obj.type == "MESH" and obj not in variants.values():
        bpy.data.objects.remove(obj, do_unlink=True)


def texture(role: str, channel: str, *, upstream=False):
    if upstream:
        path = UP / "textures" / f"{PREFIX}_{role}_{channel}_1k.jpg"
    else:
        extension = "png" if channel == "mask" else "jpg"
        path = TEX / f"{PREFIX}_{role}_{channel}_2k.{extension}"
    assert path.is_file(), path
    return bpy.data.images.load(str(path), check_existing=True)


def pbr_material(role: str):
    name = "M_NyaagyuPine_Bark" if role == "bark" else "M_NyaagyuPine_Needles"
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    nodes = material.node_tree.nodes
    nodes.clear()
    links = material.node_tree.links
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Metallic"].default_value = 0
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = texture(role, "diff")
    links.new(albedo.outputs["Color"], shader.inputs["Base Color"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.image = texture(role, "arm")
    arm.image.colorspace_settings.name = "Non-Color"
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = texture(role, "nor_gl", upstream=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    if role == "twig":
        mask = nodes.new("ShaderNodeTexImage")
        mask.image = texture("twig", "mask")
        mask.image.colorspace_settings.name = "Non-Color"
        links.new(mask.outputs["Color"], shader.inputs["Alpha"])
        material.surface_render_method = "DITHERED"
    return material


materials = {role: pbr_material(role) for role in ("bark", "twig")}


def triangle_count(obj):
    return sum(len(face.vertices) - 2 for face in obj.data.polygons)


def decimate(obj, ratio):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("Retain_scanned_pine_silhouette", "DECIMATE")
    modifier.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return triangle_count(obj)


mesh_records = []
hi_objects = []
mac_objects = []
for letter, original in variants.items():
    original.select_set(False)
    bpy.ops.object.select_all(action="DESELECT")
    original.select_set(True)
    bpy.context.view_layer.objects.active = original
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    separated = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    assert len(separated) == 2, (letter, [obj.name for obj in separated])
    parts = {}
    # Each glTF variant is laid out side-by-side. Re-center its own geometry
    # so Unreal placement is anchored at the trunk rather than the source row.
    world_bounds = [original.matrix_world @ Vector(corner) for corner in original.bound_box]
    x_center = (min(p.x for p in world_bounds) + max(p.x for p in world_bounds)) / 2
    for obj in separated:
        assert len(obj.data.materials) == 1
        role = "bark" if obj.data.materials[0].name.endswith("_bark") else "twig"
        assert role not in parts
        world_matrix = obj.matrix_world.copy()
        for vertex in obj.data.vertices:
            p = world_matrix @ vertex.co
            vertex.co = (p.x - x_center, p.y, p.z)
        obj.matrix_world.identity()
        obj.data.materials.clear()
        obj.data.materials.append(materials[role])
        obj.name = f"PineSapling_{letter.upper()}_{role.title()}_HI"
        parts[role] = obj
    assert set(parts) == {"bark", "twig"}
    hi_parts = []
    for role, obj in parts.items():
        count = decimate(obj, 1.0 if role == "bark" else .62)
        print("PINE_HI_PART", letter, role, count, flush=True)
        assert count > (300 if role == "bark" else 5000)
        hi_parts.append(obj)
    mac_parts = []
    for obj in hi_parts:
        copy = obj.copy()
        copy.data = obj.data.copy()
        bpy.context.collection.objects.link(copy)
        copy.name = obj.name.replace("_HI", "_MAC")
        role = "bark" if "_Bark_" in copy.name else "twig"
        assert decimate(copy, 1.0 if role == "bark" else .30) > 300
        mac_parts.append(copy)

    for tier, pieces in (("HI", hi_parts), ("MAC", mac_parts)):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in pieces:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = pieces[0]
        bpy.ops.object.join()
        mesh = bpy.context.object
        mesh.name = f"SM_NyaagyuPine_{letter.upper()}_{tier}"
        assert {m.name for m in mesh.data.materials} == {
            "M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"}
        if tier == "HI":
            hi_objects.append(mesh)
        else:
            mac_objects.append(mesh)
        corners = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
        low = [round(min(p[i] for p in corners), 4) for i in range(3)]
        high = [round(max(p[i] for p in corners), 4) for i in range(3)]
        print("PINE_TIER_BOUNDS", letter, tier, low, high, flush=True)
        assert -.03 < low[2] < .03 and .8 < high[2] < 1.4
        assert max(abs(low[0]), abs(high[0])) < .65
        count = triangle_count(mesh)
        assert count > (35000 if tier == "HI" else 10000)
        # FBX slots contain no machine-specific review image paths.
        slot_materials = list(mesh.data.materials)
        original_names = [material.name for material in slot_materials]
        for material in slot_materials:
            material.name += "_SourceReview"
        export_slots = [bpy.data.materials.new(name) for name in original_names]
        for index, export_slot in enumerate(export_slots):
            mesh.data.materials[index] = export_slot
        bpy.ops.object.select_all(action="DESELECT")
        mesh.select_set(True)
        bpy.context.view_layer.objects.active = mesh
        path = ART / f"{mesh.name}.fbx"
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
                                 object_types={"MESH"}, apply_unit_scale=True,
                                 axis_forward="-Y", axis_up="Z", add_leaf_bones=False,
                                 bake_anim=False, path_mode="STRIP", embed_textures=False)
        for index, original_mat in enumerate(slot_materials):
            mesh.data.materials[index] = original_mat
        for export_slot in export_slots:
            bpy.data.materials.remove(export_slot)
        for material, name in zip(slot_materials, original_names):
            material.name = name
        mesh_records.append({"variant": letter, "tier": tier.lower(), "name": mesh.name,
                             "fbx": path.name, "fbx_sha256": sha(path),
                             "source_triangles": count,
                             "bounds_m": {"min": low, "max": high},
                             "material_slots": ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"],
                             "nanite": tier == "HI",
                             "unreal_asset": f"/Game/Generated/Environment/Foliage/{mesh.name}.{mesh.name}"})
        mesh.hide_render = tier == "MAC"
        mesh.hide_set(tier == "MAC")

# Review layout; each exported mesh remains origin-centered in its FBX.
for index, mesh in enumerate(hi_objects):
    mesh.location.x = (index - 1) * 1.55
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.025))
ground = bpy.context.object
ground.name = "Review_ground_only"
ground.data.materials.append(bpy.data.materials.new("M_Review_Ground"))
bpy.ops.object.camera_add(location=(2.5, -5.0, 2.8))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, .7)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 4.7
bpy.context.scene.camera = camera
for location, energy in (((-3, -4, 5), 700), ((3, 3, 4), 450)):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = 4
    light.rotation_euler = (Vector((0, 0, .7)) - light.location).to_track_quat("-Z", "Y").to_euler()
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 800
scene.render.image_settings.file_format = "PNG"
preview = ART / "Preview_NyaagyuPine.png"
scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
scene.render.filepath = "//Preview_NyaagyuPine.png"
for material in tuple(bpy.data.materials):
    if material.users == 0:
        bpy.data.materials.remove(material)
for image in tuple(bpy.data.images):
    if image.users == 0 and image.name != "Render Result":
        bpy.data.images.remove(image)
for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.filepath = bpy.path.relpath(str(Path(bpy.path.abspath(image.filepath)).resolve()),
                                          start=str(ART))
blend = ART / "NyaagyuPine_Source.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))


def files_under(directory):
    return [{"path": str(p.relative_to(ART)), "bytes": p.stat().st_size,
             "sha256": sha(p)} for p in sorted(directory.rglob("*")) if p.is_file()]


manifest = {
    "schema_version": 1,
    "asset_id": PREFIX,
    "upstream_page": "https://polyhaven.com/a/pine_sapling_small",
    "upstream_api": "https://api.polyhaven.com/files/pine_sapling_small",
    "license": "CC0-1.0; https://polyhaven.com/license",
    "authors": ["Rico Cilliers", "Rob Tuytel"],
    "generator": "scripts/art/create_nyaagyu_pine_saplings.py",
    "description": "Three scanned pine-sapling forms; two PBR zones, needle cutout mask, HI Nanite and conventional Mac tiers; campaign visual foliage only",
    "upstream_files": files_under(UP),
    "texture_files": files_under(TEX),
    "source_blend": blend.name,
    "source_blend_sha256": sha(blend),
    "preview": preview.name,
    "preview_sha256": sha(preview),
    "material_slots": ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"],
    "meshes": mesh_records,
    "instances_in_nyaagyu_estate": 9,
    "gameplay_collision": False,
}
(ART / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAGYU_PINE_READY", [(r["variant"], r["tier"], r["source_triangles"])
                             for r in mesh_records], flush=True)
