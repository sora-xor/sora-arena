"""Replace the boxed torso armor in a *source-only* Nyaakoto comparison.

Usage: blender -b Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend \
  --python scripts/art/create_nyaakoto_do_study.py
The original hero is used as the fit mannequin and retained hidden in the
editable output. No runtime FBX or Unreal map is modified by this script.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoDoStudy"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "Content/SourceArt/Characters/Hero/Nyaakoto_RuntimeSkin.blend"
assert Path(bpy.data.filepath).resolve() == BASE.resolve(), "Load the pinned hero .blend first"

old_armor = [o for o in bpy.data.objects if o.name.startswith(("Do_lamellar_", "Do_rivet_", "Do_indigo_lacing_"))]
assert len(old_armor) >= 48, "Expected boxed cuirass source is missing"

# The runtime .blend contains a single skinned duplicate over the editable
# source. Render only the latter for a controlled geometry/material A/B.
runtime_source = bpy.data.objects.get("SK_NyaagyuSamurai")
assert runtime_source and runtime_source.type == "MESH"
runtime_source.hide_render = True
runtime_source.hide_set(True)
for source_part in bpy.data.collections["NyaagyuHero_Editable"].objects:
    source_part.hide_render = False
    source_part.hide_set(False)

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"

def aim(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()

camera = bpy.data.objects.get("Review_camera")
assert camera and camera.type == "CAMERA"
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 0.78
camera.location = (2.35, -0.68, 1.18)
aim(camera, (0.02, 0.0, 1.10))
scene.render.filepath = str(OUT / "Nyaakoto_Do_Before.png")
bpy.ops.render.render(write_still=True)

original_collection = bpy.data.collections.new("Original_BoxArmor_HiddenForComparison")
scene.collection.children.link(original_collection)
for obj in old_armor:
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    original_collection.objects.link(obj)
    obj.hide_render = True
    obj.hide_set(True)

parts = bpy.data.collections.new("Nyaakoto_Do_Editable")
scene.collection.children.link(parts)

def add_to_parts(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    parts.objects.link(obj)
    return obj

def make_material(name, color, roughness=0.7, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material

lacquer = make_material("M_Nyaakoto_Do_AgedBlackLacquer", (0.055, 0.058, 0.068), 0.37)
nodes = lacquer.node_tree.nodes
links = lacquer.node_tree.links
bsdf = nodes.get("Principled BSDF")
for input_name in ("Specular IOR Level", "IOR Level"):
    if input_name in bsdf.inputs:
        bsdf.inputs[input_name].default_value = 0.25
        break

def texture_node(name, filename, non_color):
    node = nodes.new("ShaderNodeTexImage")
    node.name = name
    node.image = bpy.data.images.load(str(OUT / filename), check_existing=True)
    if non_color:
        node.image.colorspace_settings.name = "Non-Color"
    return node

albedo = texture_node("ProjectOwned_Lacquer_Albedo", "T_Nyaakoto_Do_Lacquer_Albedo.png", False)
normal = texture_node("ProjectOwned_Lacquer_NormalDX", "T_Nyaakoto_Do_Lacquer_NormalDX.png", True)
orm = texture_node("ProjectOwned_Lacquer_ORM", "T_Nyaakoto_Do_Lacquer_ORM.png", True)
links.new(albedo.outputs["Color"], bsdf.inputs["Base Color"])
orm_split = nodes.new("ShaderNodeSeparateColor")
links.new(orm.outputs["Color"], orm_split.inputs["Color"])
links.new(orm_split.outputs["Green"], bsdf.inputs["Roughness"])
normal_split = nodes.new("ShaderNodeSeparateColor")
links.new(normal.outputs["Color"], normal_split.inputs["Color"])
green_flip = nodes.new("ShaderNodeMath")
green_flip.operation = "SUBTRACT"
green_flip.inputs[0].default_value = 1.0
links.new(normal_split.outputs["Green"], green_flip.inputs[1])
normal_join = nodes.new("ShaderNodeCombineColor")
links.new(normal_split.outputs["Red"], normal_join.inputs["Red"])
links.new(green_flip.outputs[0], normal_join.inputs["Green"])
links.new(normal_split.outputs["Blue"], normal_join.inputs["Blue"])
normal_map = nodes.new("ShaderNodeNormalMap")
normal_map.inputs["Strength"].default_value = 0.38
links.new(normal_join.outputs["Color"], normal_map.inputs["Color"])
links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])

silk = make_material("M_Nyaakoto_Do_IndigoOdoshiSilk", (0.025, 0.044, 0.095), 0.82)
silk_bsdf = silk.node_tree.nodes.get("Principled BSDF")
silk_bsdf.inputs["Sheen Weight"].default_value = 0.16
iron = make_material("M_Nyaakoto_Do_PatinatedIronEyelets", (0.16, 0.14, 0.11), 0.61, 0.82)
underlay = make_material("M_Nyaakoto_Do_DarkUnderlay", (0.018, 0.022, 0.031), 0.89)


def plate_position(theta, z, offset=0.0, flare=0.0):
    # Fitted to the source cat's cloth-backed thorax (front +X), with a slight
    # anatomical camber at the sternum instead of a flat rectangular plate.
    taper = max(0.0, min(1.0, (z - 0.93) / 0.42))
    rx = 0.242 - 0.034 * taper + flare
    ry = 0.283 - 0.045 * taper + flare * 0.78
    front = max(0.0, math.cos(theta))
    return (-0.018 + (rx + offset) * math.cos(theta) + 0.012 * front**4,
            (ry + offset * 0.78) * math.sin(theta), z)


def add_plate(name, row, low, high, theta_a=-1.72, theta_b=1.72, flare=0.0):
    segments = max(8, int((theta_b - theta_a) / 0.045))
    vertices = []
    for radial_offset in (0.0, -0.0048):
        for zlevel in (low, high):
            for step in range(segments + 1):
                theta = theta_a + (theta_b - theta_a) * step / segments
                scallop = 0.0020 * math.cos(6 * theta + row * 0.41) if zlevel == low else 0.0
                vertices.append(plate_position(theta, zlevel + scallop, radial_offset, flare))
    width = segments + 1
    faces = []
    uv_faces = []
    for i in range(segments):
        faces.append((i, i + 1, width + i + 1, width + i))
        u0, u1 = i / segments, (i + 1) / segments
        v0, v1 = (row + 0.03) / 7, (row + 0.97) / 7
        uv_faces.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
        faces.append((2*width + i, 3*width + i, 3*width + i + 1, 2*width + i + 1))
        uv_faces.append(((u0, v0), (u0, v1), (u1, v1), (u1, v0)))
        faces.append((width+i, width+i+1, 3*width+i+1, 3*width+i))
        uv_faces.append(((u0, v1), (u1, v1), (u1, v1), (u0, v1)))
        faces.append((i, 2*width+i, 2*width+i+1, i+1))
        uv_faces.append(((u0, v0), (u0, v0), (u1, v0), (u1, v0)))
    for side in (0, segments):
        faces.append((side, width+side, 3*width+side, 2*width+side))
        uv_faces.append(((0.0,0.0),(1.0,0.0),(1.0,1.0),(0.0,1.0)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(lacquer)
    layer = mesh.uv_layers.new(name="UVMap")
    for face, coords in zip(mesh.polygons, uv_faces):
        face.use_smooth = True
        for loop_id, uv in zip(face.loop_indices, coords):
            layer.data[loop_id].uv = uv
    obj = bpy.data.objects.new(name, mesh)
    parts.objects.link(obj)
    bevel = obj.modifiers.new("Rolled_lacquer_edge", "BEVEL")
    bevel.width = 0.0015
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    return obj


def braid(name, points, radius=0.0018, material=silk):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    line = curve.splines.new("POLY")
    line.points.add(len(points)-1)
    for target, coordinate in zip(line.points, points):
        target.co = (*coordinate, 1)
    obj = bpy.data.objects.new(name, curve)
    curve.materials.append(material)
    parts.objects.link(obj)
    return obj


def eyelet(name, point, radius=0.0042):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1, location=point)
    obj = add_to_parts(bpy.context.object)
    obj.name = name
    obj.scale = (radius * 0.38, radius, radius)
    obj.data.materials.append(iron)
    return obj


# A nonreflective backing hides cloth gaps but keeps the moving garment visible.
add_plate("Do_dark_backing", 0, 0.902, 1.323)
parts.objects["Do_dark_backing"].data.materials.clear()
parts.objects["Do_dark_backing"].data.materials.append(underlay)
parts.objects["Do_dark_backing"].location.x -= 0.008

# Small dark reveals, instead of interpenetrating coplanar bands, keep the
# surface watertight-looking at first-person distance without z-fighting.
row_limits = [(0.920+i*0.055, 0.973+i*0.055) for i in range(7)]
for row, (low, high) in enumerate(row_limits):
    add_plate(f"Do_formed_lacquer_plate_{row:02d}", row, low, high)
    # Odoshi crosses are actual cords, not a printed diagonal and not a grid
    # of brass studs. Holes connect adjacent rows in a restrained Edo layout.
    if row == 6:
        continue
    next_low = row_limits[row+1][0]
    for column, theta in enumerate((-1.24, -0.65, 0.0, 0.65, 1.24)):
        for side in (-1, 1):
            left = plate_position(theta + side*0.024, high-0.013, 0.008)
            right = plate_position(theta - side*0.024, next_low+0.015, 0.008)
            mid = tuple((a+b)*0.5 for a,b in zip(left,right))
            raised = (mid[0] + 0.005, mid[1], mid[2])
            braid(f"Odoshi_{row}_{column}_{side}", (left, raised, right))
            eyelet(f"Odoshi_eyelet_{row}_{column}_{side}_a", left)
            eyelet(f"Odoshi_eyelet_{row}_{column}_{side}_b", right)

# Five hanging kusazuri units, each built from three overlapping rows. The
# individual panels flare clear of the obi so the lower torso can articulate.
for panel in range(5):
    center_theta = (panel-2) * 0.50
    for row in range(3):
        high = 0.916 - row*0.060
        low = high - 0.057
        add_plate(f"Kusazuri_panel_{panel}_row_{row}", row+2, low, high,
                  center_theta-0.243, center_theta+0.243, flare=0.023+row*0.013)

# Preserve the exact user SVG crest as a separate, editable mesh pair. The
# existing source already imported the pinned paths; duplicating them avoids
# altering the original source or approximating the crest by a new drawing.
svg = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
svg_record = json.loads((svg.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(svg.read_bytes()).hexdigest() == svg_record["source_sha256"]
crest_sources = [o for o in bpy.data.objects if o.name.startswith("UserSupplied_SORAKamon_chest_Path_")]
assert len(crest_sources) == 2
for source in crest_sources:
    source.hide_render = True
    copied = source.copy()
    copied.data = source.data.copy()
    parts.objects.link(copied)
    copied.name = "DoExactSoraKamon_" + source.name.rsplit("_",1)[-1]
    copied.location.x += 0.046
    copied.hide_render = False
    copied.hide_set(False)
    copied["source_svg_sha256"] = svg_record["source_sha256"]

backing_source = bpy.data.objects.get("Resistance_insignia_backing")
if backing_source:
    backing_source.hide_render = True
    badge = backing_source.copy()
    badge.data = backing_source.data.copy()
    parts.objects.link(badge)
    badge.name = "Do_SoraKamon_Backing"
    badge.location.x += 0.046
    badge.hide_render = False
    badge.hide_set(False)

scene.render.filepath = str(OUT / "Nyaakoto_Do_After_Front.png")
bpy.ops.render.render(write_still=True)
camera.location = (2.1, -1.62, 1.28)
aim(camera, (0.02, 0.0, 1.11))
scene.render.filepath = str(OUT / "Nyaakoto_Do_After_ThreeQuarter.png")
bpy.ops.render.render(write_still=True)

# Export the new armor only. Curves are converted in temporary duplicates so
# the editable source retains spline control points and individual laces.
bpy.ops.object.select_all(action="DESELECT")
temp = []
for obj in parts.objects:
    if obj.type not in {"MESH", "CURVE"}:
        continue
    copied = obj.copy()
    copied.data = obj.data.copy()
    scene.collection.objects.link(copied)
    copied.hide_render = False
    copied.hide_set(False)
    temp.append(copied)
    copied.select_set(True)
    bpy.context.view_layer.objects.active = copied
    if copied.type == "CURVE":
        bpy.ops.object.convert(target="MESH")
        temp[-1] = bpy.context.object
        temp[-1].select_set(True)
bpy.context.view_layer.objects.active = temp[0]
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_Nyaakoto_Do_Study.fbx"),
                         use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, use_mesh_modifiers=True,
                         add_leaf_bones=False, bake_anim=False,
                         path_mode="STRIP")
for obj in temp:
    bpy.data.objects.remove(obj, do_unlink=True)

# Resolve linked image paths against the original hero file. Save once with
# absolute paths to switch Blender's active .blend directory, then rewrite
# them relative to the study file and save again. Blender otherwise rebases
# the new relative path against the *old* .blend location during Save As.
image_paths = {}
for img in bpy.data.images:
    if img.source != "FILE" or not img.filepath:
        continue
    absolute_path = Path(bpy.path.abspath(img.filepath)).resolve()
    assert absolute_path.is_file(), (img.name, absolute_path)
    image_paths[img.name] = absolute_path
    img.filepath = str(absolute_path)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Nyaakoto_Do_Study.blend"), relative_remap=False)
for name, absolute_path in image_paths.items():
    bpy.data.images[name].filepath = "//" + os.path.relpath(absolute_path, OUT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Nyaakoto_Do_Study.blend"), relative_remap=False)

mesh_parts = [o for o in parts.objects if o.type == "MESH"]
triangles = sum(sum(len(face.vertices)-2 for face in o.data.polygons) for o in mesh_parts)
manifest = {
    "schema_version": 1,
    "reference_blend_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "source_svg_sha256": svg_record["source_sha256"],
    "armor_collection": parts.name,
    "mesh_parts": len(mesh_parts),
    "braided_curve_parts": sum(o.type == "CURVE" for o in parts.objects),
    "source_mesh_triangles_before_modifiers": triangles,
    "render_camera": "fixed 900x900 torso crop; before, front, three-quarter",
    "files": [
        {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        for p in (OUT / "Nyaakoto_Do_Study.blend", OUT / "SM_Nyaakoto_Do_Study.fbx",
                  OUT / "Nyaakoto_Do_Before.png", OUT / "Nyaakoto_Do_After_Front.png",
                  OUT / "Nyaakoto_Do_After_ThreeQuarter.png")
    ],
    "historical_references": [
        "https://www.britishmuseum.org/collection/object/A_2017-3024-1-1-14",
        "https://www.metmuseum.org/exhibitions/listings/2009/art-of-the-samurai/photo-gallery",
    ],
    "limitations": "Source-only comparative formed-plate and odoshi study, not a museum reconstruction or shippable rig. New shell is not skinned, and SORA logo placement, cloth dynamics, texel density, and packaged-game shading remain to be reviewed.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAKOTO_DO_STUDY_READY", json.dumps({"mesh_parts": len(mesh_parts), "curve_parts": manifest["braided_curve_parts"], "triangles": triangles}))
