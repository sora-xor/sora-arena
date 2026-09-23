"""Build the original Nyaagyu irrigation sluice source mesh and review render.

Run with Blender 5.2.2 LTS:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_sluice.py

The editable .blend retains separate pieces and relative CC0 palette links.
The FBX contains one joined render mesh and three named UCX boxes, in meters.
The Blender image is a material/shape review, not an Unreal screenshot.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuSluice"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
NAME = "SM_Nyaagyu_IrrigationSluice"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
asset = bpy.data.collections.new("NyaagyuSluice_Editable")
scene.collection.children.link(asset)


def basic(name, color, metallic=0.0, roughness=0.5, glow=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if glow:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = glow
    return mat


def palette(role, asset_id, scale):
    record = PALETTE / asset_id
    mat = basic("M_Env_" + role, (.32, .27, .20), role == "Metal", .65)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale,) * 3
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    images = {}
    for channel, marker in (("diffuse", "_diff_"), ("normal", "_nor_dx_"), ("arm", "_arm_")):
        path = next(record.glob("*" + marker + "*"))
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.name = channel
        node.image = image
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        images[channel] = node
    links.new(images["diffuse"].outputs["Color"], bsdf.inputs["Base Color"])
    arm = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], arm.inputs["Color"])
    links.new(arm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(arm.outputs["Blue"], bsdf.inputs["Metallic"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"], split.inputs["Color"])
    invert_green = nodes.new("ShaderNodeMath")
    invert_green.operation = "SUBTRACT"
    invert_green.inputs[0].default_value = 1.0
    links.new(split.outputs["Green"], invert_green.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(split.outputs["Red"], rgb.inputs["Red"])
    links.new(invert_green.outputs[0], rgb.inputs["Green"])
    links.new(split.outputs["Blue"], rgb.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .72
    links.new(rgb.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


TIMBER = palette("Timber", "wood_planks_dirt", 1.1)
STONE = palette("Stone", "stone_floor", .85)
METAL = palette("Metal", "rusty_metal_02", 1.0)
BRONZE = basic("M_Sluice_AgedBronze", (.38, .24, .10), .82, .39)
IRON = basic("M_Sluice_BlackIron", (.024, .033, .038), .80, .44)
WATER = basic("M_Sluice_WaterEnamel", (.019, .13, .17), .25, .19)
CYAN = basic("M_Sluice_FlowCyan", (.018, .48, .60), .12, .25, 2.3)
RED = basic("M_Sluice_DebtRed", (.55, .018, .018), .08, .30, 1.6)
PAPER = basic("M_Sluice_Washi", (.67, .52, .31), 0, .75)


def keep(obj, name, mat=None, collection=asset):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena environment prop"
    return obj


def box(name, position, dimensions, mat, bevel=0.0, collection=asset):
    bpy.ops.mesh.primitive_cube_add(size=1, location=position)
    obj = keep(bpy.context.object, name, mat, collection)
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("rounded_edge_wear", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def cylinder(name, position, radius, depth, mat, vertices=32, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=position, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def torus(name, position, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=48, minor_segments=8,
                                     location=position, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    asset.objects.link(obj)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def label(name, text, location, size, mat):
    bpy.ops.object.text_add(location=location, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.data.body = text
    obj.data.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = .001
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


# Stone cheeks and a dark channel establish an Edo irrigation silhouette.
box("Channel_Bed", (0, .10, .08), (3.42, 1.60, .16), STONE, .025)
box("Water_Trough", (0, -.08, .17), (2.48, 1.34, .021), WATER, .007)
for side in (-1, 1):
    x = side * 1.47
    box(f"Stone_Abutment_{side}", (x, .10, .53), (.48, 1.60, 1.06), STONE, .04)
    box(f"Stone_Cap_{side}", (x, .10, 1.085), (.57, 1.70, .12), STONE, .022)
    box(f"Cedar_Post_{side}", (side * 1.18, .12, 1.72), (.20, .24, 2.14), TIMBER, .02)
    for z in (.83, 1.22, 2.56):
        box(f"Iron_PostBand_{side}_{z}", (side * 1.18, .12, z), (.218, .26, .062), IRON, .008)
    for y in (-.47, .59):
        cylinder(f"Bronze_Anchor_{side}_{y}", (x, y, 1.15), .052, .065, BRONZE, 20)

box("Upper_Sluice_Beam", (0, .12, 2.62), (2.72, .34, .25), TIMBER, .025)
box("Lower_Sluice_Beam", (0, .10, .77), (2.72, .22, .17), TIMBER, .014)
for i in range(9):
    x = -.92 + i * .23
    box(f"Vertical_Gate_Plank_{i:02d}", (x, .12, 1.47), (.215, .105, 1.47), TIMBER, .012)
    for z in (1.02, 2.02):
        cylinder(f"Plank_IronRivet_{i:02d}_{z}", (x, .058, z), .016, .018, IRON, 12,
                 (math.pi / 2, 0, 0))
for z in (1.06, 2.10):
    box(f"Transverse_IronStrap_{z}", (0, .045, z), (2.20, .035, .062), IRON, .006)

# Manual lift mechanism: the handwheel, drum, chain and paired rack plates
# visibly make the sluice plausible as a production workshop object.
cylinder("Winch_Shaft", (0, -.40, 2.84), .09, 2.50, BRONZE, 32, (0, math.pi / 2, 0))
for side in (-1, 1):
    x = side * 1.07
    cylinder(f"Winch_Shaft_Bearing_{side}", (x, -.40, 2.84), .15, .13, IRON,
             32, (0, math.pi / 2, 0))
    box(f"Rack_Guide_{side}", (side * .83, -.002, 1.86), (.10, .12, 1.55), BRONZE, .008)
    for i in range(8):
        box(f"Rack_Tooth_{side}_{i}", (side * .83, -.080, 1.18 + i * .19),
            (.14, .045, .042), IRON, .004)
for side in (-1, 1):
    x = side * .52
    cylinder(f"Lift_Drum_{side}", (x, -.40, 2.84), .21, .16, IRON, 32,
             (0, math.pi / 2, 0))
    tube(f"Lift_Cable_{side}", [(x, -.63, 2.84), (x, -.63, 2.17),
                                  (x, -.64, 1.98)], .012, BRONZE)
torus("Handwheel_Rim", (1.40, -.40, 2.84), .34, .028, BRONZE,
      (0, math.pi / 2, 0))
for i in range(6):
    angle = i * math.tau / 6
    y = -.40 + .31 * math.sin(angle)
    z = 2.84 + .31 * math.cos(angle)
    tube(f"Handwheel_Spoke_{i}", [(1.43, -.40, 2.84), (1.43, y, z)], .018, BRONZE)
cylinder("Handwheel_Hub", (1.46, -.40, 2.84), .075, .075, IRON, 24,
         (0, math.pi / 2, 0))

# Thin alien clamp and meter intrude onto hand-built timber, leaving the
# hydraulic mechanism readable and giving the occupation a local visual trace.
box("Alien_Meter_Housing", (-1.16, -.41, 1.85), (.53, .24, .72), METAL, .035)
box("Alien_Meter_Face", (-1.16, -.543, 1.91), (.39, .025, .40), IRON, .013)
cylinder("Alien_Meter_Dial", (-1.16, -.565, 1.93), .145, .028, CYAN, 48,
         (math.pi / 2, 0, 0))
cylinder("Alien_Meter_Center", (-1.16, -.583, 1.93), .065, .018, IRON, 32,
         (math.pi / 2, 0, 0))
for i in range(9):
    angle = math.pi * (.13 + .75 * i / 8)
    x = -1.16 + .12 * math.cos(angle)
    z = 1.93 + .12 * math.sin(angle)
    cylinder(f"Meter_Tick_{i}", (x, -.584, z), .008, .012,
             RED if i > 5 else BRONZE, 10, (math.pi / 2, 0, 0))
box("Alien_Debt_Clamp", (-1.16, -.42, 1.48), (.48, .28, .075), IRON, .012)
label("Debt_Levy_Mark", "債", (-1.16, -.579, 1.70), .13, RED)
box("Waterworks_Nameplate", (.07, -.082, 2.46), (.73, .027, .17), BRONZE, .008)
label("Waterworks_Japanese", "用水", (.07, -.101, 2.45), .105, PAPER)


# Remove texture references temporarily so exported FBX has no machine-local
# image paths. The saved Blender source restores project-relative image links.
linked = [(node, node.image) for mat in (TIMBER, STONE, METAL)
          for node in mat.node_tree.nodes if node.type == "TEX_IMAGE"]
for node, _ in linked:
    node.image = None
parts = [obj for obj in asset.objects if obj.type == "MESH"]
triangles = sum(len(face.vertices) - 2 for obj in parts for face in obj.data.polygons)
corners = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
bounds = {key: [round(fn(point[axis] for point in corners), 3) for axis in range(3)]
          for key, fn in (("min", min), ("max", max))}
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
render = bpy.context.object
render.name = NAME
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
proxies = []
for index, (position, dimensions) in enumerate((
    ((-1.47, .10, .53), (.48, 1.60, 1.06)),
    ((1.47, .10, .53), (.48, 1.60, 1.06)),
    ((0, .12, 2.62), (2.72, .34, .25)),
)):
    proxies.append(box(f"UCX_{NAME}_{index:02d}", position, dimensions, IRON))
bpy.ops.object.select_all(action="DESELECT")
render.select_set(True)
for obj in proxies:
    obj.select_set(True)
bpy.context.view_layer.objects.active = render
fbx = OUT / f"{NAME}.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, global_scale=1.0, axis_forward="-Y",
                         axis_up="Z", add_leaf_bones=False, bake_anim=False,
                         path_mode="STRIP")
for obj in proxies + [render]:
    bpy.data.objects.remove(obj, do_unlink=True)
for node, image in linked:
    node.image = image


review = bpy.data.collections.new("Review_Stage_NotForFBX")
scene.collection.children.link(review)
box("Review_Stone_Plinth", (0, .1, -.15), (4.05, 2.3, .26), STONE, .045, review)
bpy.ops.object.light_add(type="AREA", location=(-3.3, -4.2, 5.5))
key = bpy.context.object
key.data.energy = 680
key.data.shape = "DISK"
key.data.size = 5.0
key.rotation_euler = (Vector((0, 0, 1.2)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(2.9, 3.0, 4.7))
rim = bpy.context.object
rim.data.energy = 850
rim.data.color = (.49, .78, 1.0)
rim.data.shape = "DISK"
rim.data.size = 3.8
rim.rotation_euler = (Vector((0, 0, 1.4)) - rim.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.camera_add(location=(4.0, -6.0, 3.5))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 1.45)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 5.3
scene.camera = camera
scene.world.color = (.045, .052, .060)
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1450
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.25
preview = OUT / "Nyaagyu_IrrigationSluice_Blender.png"
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == "FILE":
        image.filepath = bpy.path.relpath(image.filepath, start=str(OUT))
for font_data in bpy.data.fonts:
    if font_data.filepath and Path(bpy.path.abspath(font_data.filepath)).resolve() == FONT.resolve():
        font_data.filepath = bpy.path.relpath(str(FONT), start=str(OUT))
blend = OUT / "Nyaagyu_IrrigationSluice.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_nyaagyu_sluice.py",
    "generator_blender": bpy.app.version_string,
    "source_blend": blend.name,
    "preview": preview.name,
    "fbx": fbx.name,
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "source_parts": len(parts),
    "source_triangles": triangles,
    "collision_boxes": len(proxies),
    "bounds_m": bounds,
    "license": "Original project-owned geometry; no purchased meshes. Japanese font SIL OFL; linked palette maps CC0 Poly Haven.",
    "texture_dependency": "../PolyHaven/manifest.json; project-relative links in .blend, no FBX texture paths",
    "palette_asset_ids": ["wood_planks_dirt", "rusty_metal_02", "stone_floor"],
    "palette_manifest_sha256": hashlib.sha256((PALETTE / "manifest.json").read_bytes()).hexdigest(),
    "font_sha256": hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "units": "Blender meters; Unreal import converts to centimeters",
    "placement": "Chapter 4 Nyaagyu Estate irrigation sites, offset toward the water channel; visual mesh only, never multiplayer collision",
    "scope": "Blender source art/review only; UE 5.8.2 import, gameplay lighting and frame rate unverified",
    "blend_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
    "fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("NYAAGYU_SLUICE_READY", manifest["source_parts"], triangles, bounds, preview)
