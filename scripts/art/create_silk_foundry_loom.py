"""Generate original Silk Foundry floor loom source art and a Blender review.

Run: blender -b --factory-startup --python scripts/art/create_silk_foundry_loom.py

The editable blend keeps all parts separate and uses project-relative CC0 PBR
links. The FBX is a joined render mesh plus four UCX boxes in meter units.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/SilkFoundryLoom"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
NAME = "SM_SilkFoundry_LevyLoom"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
asset = bpy.data.collections.new("SilkFoundryLoom_Editable")
scene.collection.children.link(asset)


def basic(name, color, metallic=0.0, roughness=0.5, emission=0.0, sheen=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Sheen Weight"].default_value = sheen
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def palette(role, asset_id, scale):
    mat = basic("M_Env_" + role, (.25, .22, .18), role == "Metal", .55)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale,) * 3
    # Object coordinates keep texture scale in meters on long posts and beams.
    links.new(coordinates.outputs["Object"], mapping.inputs["Vector"])
    images = {}
    for channel, marker in (("diffuse", "_diff_"), ("normal", "_nor_dx_"), ("arm", "_arm_")):
        image = bpy.data.images.load(str(next((PALETTE / asset_id).glob("*" + marker + "*"))), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.name = channel
        node.image = image
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        images[channel] = node
    if role == "Timber":
        # Broad, low-contrast weathering breaks repetition across long rails.
        # Unreal uses the independently pinned timber PBR source at import.
        wear = nodes.new("ShaderNodeTexNoise")
        wear.inputs["Scale"].default_value = 2.6
        wear.inputs["Detail"].default_value = 2.0
        links.new(mapping.outputs["Vector"], wear.inputs["Vector"])
        tone = nodes.new("ShaderNodeValToRGB")
        tone.color_ramp.elements[0].position = .22
        tone.color_ramp.elements[0].color = (.62, .59, .53, 1)
        tone.color_ramp.elements[1].position = .78
        tone.color_ramp.elements[1].color = (1, .98, .95, 1)
        links.new(wear.outputs["Fac"], tone.inputs["Fac"])
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = .42
        links.new(images["diffuse"].outputs["Color"], mix.inputs[1])
        links.new(tone.outputs["Color"], mix.inputs[2])
        links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        links.new(images["diffuse"].outputs["Color"], bsdf.inputs["Base Color"])
    arm = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], arm.inputs["Color"])
    links.new(arm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(arm.outputs["Blue"], bsdf.inputs["Metallic"])
    rgb = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"], rgb.inputs["Color"])
    green = nodes.new("ShaderNodeMath")
    green.operation = "SUBTRACT"
    green.inputs[0].default_value = 1.0
    links.new(rgb.outputs["Green"], green.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(rgb.outputs["Red"], combine.inputs["Red"])
    links.new(green.outputs[0], combine.inputs["Green"])
    links.new(rgb.outputs["Blue"], combine.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .65
    links.new(combine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


TIMBER = palette("Timber", "wood_planks_dirt", 1.35)
METAL = palette("Metal", "rusty_metal_02", 1.3)
BRONZE = basic("M_Loom_AgedBronze", (.42, .28, .11), .82, .32)
IRON = basic("M_Loom_BlackIron", (.025, .034, .038), .79, .42)
SILK = basic("M_Loom_IndigoSilk", (.008, .022, .085), .0, .60, sheen=.25)
SILK_EDGE = basic("M_Loom_SilkSelvedge", (.54, .34, .10), .33, .30, sheen=.7)
THREAD = basic("M_Loom_IvoryWarp", (.72, .61, .39), .06, .34, sheen=.70)
CYAN = basic("M_Loom_ProductionCyan", (.025, .48, .66), .08, .26, emission=2.0)
RED = basic("M_Loom_LevyRed", (.70, .028, .018), .12, .26, emission=1.55)
GLASS = basic("M_Loom_SmokedGlass", (.017, .033, .048), .25, .18)
REVIEW_FLOOR = basic("M_Review_Charcoal", (.072, .081, .087), .04, .73)


def keep(obj, name, mat=None, collection=asset):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena Silk Foundry prop"
    return obj


def box(name, center, size, mat, bevel=.0, collection=asset):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = keep(bpy.context.object, name, mat, collection)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("machined_or_worn_edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def cylinder(name, center, radius, depth, mat, vertices=32, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=center, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def torus(name, center, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=8,
                                     location=center, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
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


def label(name, body, location, size, mat):
    bpy.ops.object.text_add(location=location, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.data.body = body
    obj.data.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = .001
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def fabric(name, y_front, y_back, z_front, z_back, material):
    # Slightly undulating panel: no simulation dependency and fully editable.
    verts = []
    faces = []
    x_count, y_count = 32, 14
    for j in range(y_count + 1):
        t = j / y_count
        y = y_front * (1 - t) + y_back * t
        z = z_front * (1 - t) + z_back * t
        for i in range(x_count + 1):
            x = -1.03 + 2.06 * i / x_count
            verts.append((x, y, z + .004 * math.sin(i * 1.72 + j * .66)))
    for j in range(y_count):
        for i in range(x_count):
            a = j * (x_count + 1) + i
            faces.append((a, a + 1, a + x_count + 2, a + x_count + 1))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    mesh.materials.append(material)
    solid = obj.modifiers.new("woven_silk_thickness", "SOLIDIFY")
    solid.thickness = .006
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=solid.name)
    return obj


# A floor loom's load path remains readable: posts and low rails support the
# back warp beam, twin suspended heddles, hand reed and front cloth take-up.
for side in (-1, 1):
    x = side * 1.28
    for y in (-.78, .79):
        box(f"Cedar_Leg_{side}_{y}", (x, y, .96), (.19, .19, 1.92), TIMBER, .018)
        box(f"Iron_LegFoot_{side}_{y}", (x, y, .07), (.215, .215, .13), IRON, .008)
    box(f"Lower_LongRail_{side}", (x, .0, .38), (.15, 1.76, .16), TIMBER, .014)
    box(f"Upper_LongRail_{side}", (x, .0, 1.88), (.15, 1.76, .13), TIMBER, .014)
    box(f"Timber_HeddleSupport_{side}", (x, .06, 2.12), (.22, .46, .23), TIMBER, .025)
    for y in (-.78, .79):
        for z in (.39, 1.87):
            cylinder(f"Bronze_JointPin_{side}_{y}_{z}", (x, y, z),
                     .040, .235, BRONZE, 16, (0, math.pi / 2, 0))

for y in (-.78, .79):
    box(f"CrossBeam_{y}", (0, y, 1.91), (2.74, .19, .17), TIMBER, .016)
    box(f"LowerCrossBeam_{y}", (0, y, .38), (2.74, .15, .17), TIMBER, .014)
box("Top_HeaterBeam", (0, .06, 2.17), (2.74, .20, .18), TIMBER, .018)

for y, title in ((.72, "Warp"), (-.65, "Cloth")):
    cylinder(f"{title}_TakeupRoll", (0, y, .96), .20, 2.50, TIMBER, 48,
             (0, math.pi / 2, 0))
    for side in (-1, 1):
        cylinder(f"{title}_RollBearing_{side}", (side * 1.27, y, .96),
                 .24, .10, IRON, 32, (0, math.pi / 2, 0))
        torus(f"{title}_BearingRim_{side}", (side * 1.33, y, .96), .20,
              .023, BRONZE, (0, math.pi / 2, 0))

for y, z, tag in ((.36, 1.23, "Rear"), (-.02, 1.20, "Front")):
    for z_offset in (-.15, .15):
        box(f"Heddle_{tag}_Rail_{z_offset}", (0, y, z + z_offset),
            (2.20, .047, .046), TIMBER, .005)
    for i in range(36):
        x = -.99 + i * 1.98 / 35
        tube(f"Heddle_{tag}_Cord_{i:02d}",
             [(x, y, z - .12), (x, y, z + .12)], .0027, THREAD)
    for side in (-1, 1):
        tube(f"Heddle_{tag}_Suspension_{side}",
             [(side * .9, y, z + .15), (side * .9, y, 2.08)], .007, THREAD)

box("Reed_Beater_Top", (0, -.31, 1.40), (2.30, .09, .08), TIMBER, .010)
box("Reed_Beater_Bottom", (0, -.31, 1.10), (2.30, .09, .08), TIMBER, .010)
for i in range(44):
    x = -1.06 + i * 2.12 / 43
    tube(f"Reed_Slat_{i:02d}", [(x, -.32, 1.14), (x, -.32, 1.37)], .0034, BRONZE)
for side in (-1, 1):
    tube(f"Reed_Hanger_{side}", [(side * 1.04, -.31, 1.40),
                                   (side * 1.04, -.31, 2.12)], .011, IRON)

for i in range(65):
    x = -1.00 + i * 2.0 / 64
    alternate = .025 if i % 2 else -.025
    tube(f"Ivory_WarpThread_{i:02d}",
         [(x, .69, 1.13), (x, .39, 1.24 + alternate),
          (x, .0, 1.20 - alternate), (x, -.31, 1.20), (x, -.40, 1.17)],
         .0031, THREAD)

fabric("Indigo_Silk_InProgress", -.55, -.10, 1.16, 1.20, SILK)
for side in (-1, 1):
    x = side * 1.034
    tube(f"Gold_Selvedge_{side}", [(x, -.55, 1.17), (x, -.10, 1.21)],
         .011, SILK_EDGE)
    for y in (-.52, -.43):
        box(f"Gold_SelvedgeMark_{side}_{y}", (x, y, 1.185),
            (.019, .024, .002), SILK_EDGE)

# A boat shuttle, treadles and direct drive crank supply credible hand-use.
box("Boat_Shuttle", (.22, -.41, 1.24), (.47, .10, .061), TIMBER, .024)
cylinder("Boat_Shuttle_Bobbin", (.22, -.41, 1.278), .022, .31,
         SILK_EDGE, 20, (0, math.pi / 2, 0))
for side in (-1, 1):
    x = side * .38
    box(f"Foot_Treadle_{side}", (x, -.16, .12), (.31, 1.16, .06), TIMBER, .012)
    tube(f"Foot_TreadleCord_{side}", [(x, .19, .15), (x, .17, 1.10)], .006, THREAD)
torus("Front_Handwheel_Rim", (1.46, -.65, .96), .31, .028,
      BRONZE, (0, math.pi / 2, 0))
for i in range(6):
    angle = i * math.tau / 6
    tube(f"Front_Handwheel_Spoke_{i}", [(1.46, -.65, .96),
         (1.46, -.65 + .29 * math.sin(angle), .96 + .29 * math.cos(angle))],
         .012, BRONZE)
cylinder("Front_Handwheel_Hub", (1.48, -.65, .96), .075, .07, IRON,
         24, (0, math.pi / 2, 0))

# Occupation technology is bolted onto the original hand-operated loom and
# monitors cloth production; it does not replace the mechanical load path.
box("Alien_LevyClamp", (-1.38, -.18, 1.72), (.22, .71, .16), IRON, .018)
box("Alien_LevyCase", (-1.48, -.43, 1.48), (.39, .28, .50), METAL, .026)
box("Alien_LevyGlass", (-1.48, -.578, 1.49), (.32, .018, .37), GLASS, .012)
for i in range(11):
    z = 1.32 + .031 * i
    box(f"Production_Bar_{i:02d}", (-1.55, -.592, z),
        (.11 if i < 8 else .035, .004, .010), CYAN if i < 8 else RED, .002)
label("Levy_Label_Japanese", "徴", (-1.42, -.595, 1.49), .125, RED)
label("Silk_Production_Label", "絹", (0, -.886, 1.91), .10, SILK_EDGE)
box("Silk_Production_Nameplate", (0, -.869, 1.91), (.44, .027, .18), BRONZE, .007)


# Export without absolute texture paths; editable source restores the links.
linked = [(node, node.image) for mat in (TIMBER, METAL)
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
    ((-1.28, 0, .96), (.20, 1.77, 1.92)),
    ((1.28, 0, .96), (.20, 1.77, 1.92)),
    ((0, .79, 1.91), (2.75, .20, .18)),
    ((0, -.78, 1.91), (2.75, .20, .18)),
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
box("Review_Floor", (0, 0, -.10), (4.4, 3.6, .19), REVIEW_FLOOR, .035, review)
bpy.ops.object.light_add(type="AREA", location=(-3.6, -4.5, 5.2))
key = bpy.context.object
key.data.energy = 750
key.data.shape = "DISK"
key.data.size = 4.5
key.rotation_euler = (Vector((0, 0, 1.1)) - key.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.light_add(type="AREA", location=(3.2, 2.0, 4.0))
rim = bpy.context.object
rim.data.energy = 820
rim.data.color = (.45, .74, 1.0)
rim.data.shape = "DISK"
rim.data.size = 3.4
rim.rotation_euler = (Vector((0, 0, 1.2)) - rim.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.camera_add(location=(-4.3, -5.1, 3.2))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 1.15)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 5.1
scene.camera = camera
scene.world.color = (.045, .049, .054)
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 1150
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.18
preview = OUT / "SilkFoundry_LevyLoom_Blender.png"
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(preview)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == "FILE":
        image.filepath = bpy.path.relpath(image.filepath, start=str(OUT))
for font_data in bpy.data.fonts:
    if font_data.filepath and Path(bpy.path.abspath(font_data.filepath)).resolve() == FONT.resolve():
        font_data.filepath = bpy.path.relpath(str(FONT), start=str(OUT))
blend = OUT / "SilkFoundry_LevyLoom.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_silk_foundry_loom.py",
    "generator_blender": bpy.app.version_string,
    "source_blend": blend.name,
    "preview": preview.name,
    "fbx": fbx.name,
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "source_parts": len(parts),
    "source_triangles": triangles,
    "collision_boxes": len(proxies),
    "bounds_m": bounds,
    "license": "Original project-owned geometry and authored silk/glass materials; no purchased meshes. Japanese font SIL OFL; linked wood/metal maps CC0 Poly Haven.",
    "texture_dependency": "../PolyHaven/manifest.json; project-relative links in .blend, no FBX texture paths",
    "palette_asset_ids": ["wood_planks_dirt", "rusty_metal_02"],
    "palette_manifest_sha256": hashlib.sha256((PALETTE / "manifest.json").read_bytes()).hexdigest(),
    "font_sha256": hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "units": "Blender meters; Unreal import converts to centimeters",
    "placement": "Silk Foundry chapter/arena decorative prop; visual mesh only, not canonical multiplayer collision",
    "scope": "Blender source art/review only; UE 5.8.2 import, gameplay lighting and frame rate unverified",
    "blend_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(preview.read_bytes()).hexdigest(),
    "fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("SILK_FOUNDRY_LOOM_READY", len(parts), triangles, bounds, preview)
