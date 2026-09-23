"""Author three original modular Edo / alien-occupation source props.

Run with Blender 5.2.2 LTS:
  blender -b --factory-startup --python scripts/art/create_edo_environment_props.py

All geometry is in meters, centered on a ground-plane origin for placement in
Unreal. FBX files contain one joined render mesh and named UCX collision boxes.
The .blend keeps editable parts and linked CC0 Poly Haven source textures. Its
render is an asset review image, not an Unreal gameplay screenshot.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/Original"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
SORA_SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SORA_LOGO_RECORD = json.loads((SORA_SVG.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(SORA_SVG.read_bytes()).hexdigest() == SORA_LOGO_RECORD["source_sha256"]
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
SCENE = bpy.context.scene
SCENE.unit_settings.system = "METRIC"
SCENE.unit_settings.scale_length = 1.0


def material(name, color, metal=0.0, rough=0.5, emission=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    if emission:
        shader.inputs["Emission Color"].default_value = (*color, 1)
        shader.inputs["Emission Strength"].default_value = emission
    return mat


def palette_material(role, asset_id, tile=1.0):
    """Source material uses the pinned CC0 maps; Unreal uses its own PBR instance."""
    folder = PALETTE / asset_id
    diffuse = next(folder.glob("*_diff_*"))
    normal = next(folder.glob("*_nor_dx_*"))
    arm = next(folder.glob("*_arm_*"))
    mat = material("M_Env_" + role, (0.3, 0.25, 0.19), role == "Metal", 0.65)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    coords.location = (-900, 0)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 0)
    mapping.inputs["Scale"].default_value = (tile, tile, tile)
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    images = {}
    for i, (channel, file) in enumerate((("diffuse", diffuse), ("normal", normal), ("arm", arm))):
        image = bpy.data.images.load(str(file), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = channel
        tex.location = (-460, 200 - i * 300)
        tex.image = image
        links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        images[channel] = tex
    links.new(images["diffuse"].outputs["Color"], shader.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    links.new(split.outputs["Blue"], shader.inputs["Metallic"])
    # Poly Haven normal files are DirectX; invert green for Blender's tangent convention.
    nsplit = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"], nsplit.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(nsplit.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(nsplit.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(nsplit.outputs["Blue"], combine.inputs["Blue"])
    bump = nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.8
    links.new(combine.outputs["Color"], bump.inputs["Color"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


TIMBER = palette_material("Timber", "wood_planks_dirt", 1.2)
METAL = palette_material("Metal", "rusty_metal_02", 1.3)
STONE = palette_material("Stone", "stone_floor", 0.9)
LACQUER = material("M_Env_VermilionLacquer", (0.30, 0.018, 0.012), 0.02, 0.31)
AGED_IRON = material("M_Env_BlackIron", (0.025, 0.034, 0.038), 0.82, 0.44)
BRASS = material("M_Env_AgedBrass", (0.44, 0.30, 0.11), 0.88, 0.32)
WASHI = material("M_Env_WashiPaper", (0.75, 0.55, 0.31), 0, 0.77, 0.25)
WARM_GLOW = material("M_Env_LanternGlow", (1.0, 0.35, 0.09), 0, 0.37, 3.0)
CYAN_GLOW = material("M_Env_AlienCyan", (0.012, 0.42, 0.57), 0.12, 0.20, 2.4)
RED_GLOW = material("M_Env_DebtRed", (0.55, 0.025, 0.025), 0.1, 0.25, 1.8)
INDIGO = material("M_Env_IndigoEnamel", (0.025, 0.065, 0.10), 0.25, 0.34)

ASSETS = {
    "SM_Edo_LanternPost": bpy.data.collections.new("Edo_LanternPost_Editable"),
    "SM_Nyaagyu_ToriiGate": bpy.data.collections.new("Nyaagyu_ToriiGate_Editable"),
    "SM_Alien_DebtKiosk": bpy.data.collections.new("Alien_DebtKiosk_Editable"),
}
for coll in ASSETS.values():
    SCENE.collection.children.link(coll)
active_collection = None


def keep(obj, name, mat=None):
    obj.name = name
    for coll in tuple(obj.users_collection):
        coll.objects.unlink(obj)
    active_collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["source"] = "Original SORA Arena environment prop"
    return obj


def box(name, location, dimensions, mat, bevel=0.0, segments=2):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("edge_wear_profile", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def cylinder(name, location, radius, depth, mat, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat, resolution=3):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = resolution
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    active_collection.objects.link(obj)
    data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def label(name, text, location, size, mat):
    bpy.ops.object.text_add(location=location, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.0015
    obj.data.bevel_depth = 0.0007
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def gate_sora_kamon(name, x, front_y, z, diameter, mat):
    """Project the exact supplied SVG paths onto the torii's front plane."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SORA_SVG))
    curves = [obj for obj in set(bpy.data.objects) - before if obj.type == "CURVE"]
    assert len(curves) == 2, [obj.name for obj in curves]
    corners = [obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
    lo_x, hi_x = min(v.x for v in corners), max(v.x for v in corners)
    lo_y, hi_y = min(v.y for v in corners), max(v.y for v in corners)
    center_x, center_y = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
    scale = diameter / max(hi_x - lo_x, hi_y - lo_y)
    for index, obj in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.object
        for vert in obj.data.vertices:
            p = obj.matrix_world @ vert.co
            vert.co = (x + (p.x - center_x) * scale, front_y,
                       z + (p.y - center_y) * scale)
        obj.matrix_world.identity()
        obj = keep(obj, f"UserSupplied_SORAKamon_{name}_Path_{index}")
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        obj["source_svg_sha256"] = SORA_LOGO_RECORD["source_sha256"]


def torii_lintel(name, half_width, bottom_z, height, depth, mat):
    """A slight upper-rail rise makes the gate silhouette legible at distance."""
    verts = []
    for x in (-half_width, -half_width * .7, 0, half_width * .7, half_width):
        rise = .11 * abs(x / half_width) ** 1.7
        for y in (-depth / 2, depth / 2):
            for z in (bottom_z + rise, bottom_z + height + rise):
                verts.append((x, y, z))
    faces = []
    for i in range(4):
        n = i * 4
        m = (i + 1) * 4
        faces.extend(((n, m, m + 1, n + 1), (n + 2, n + 3, m + 3, m + 2),
                      (n, n + 2, m + 2, m), (n + 1, m + 1, m + 3, n + 3)))
    faces += [(0, 1, 3, 2), (16, 18, 19, 17)]
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    active_collection.objects.link(obj)
    data.materials.append(mat)
    return obj


def torii_post(side):
    """Build a gently tapered timber post with a subtle inward crown."""
    rings = (0.43, 0.55, 0.95, 1.45, 2.15, 2.9, 3.65, 4.35, 4.84)
    sides = 40
    vertices = []
    for z in rings:
        t = (z - rings[0]) / (rings[-1] - rings[0])
        center_x = side * (2.35 - .043 * t)
        for index in range(sides):
            angle = math.tau * index / sides
            # A hewn timber is never a mathematically perfect lathed cylinder.
            radius = (.230 - .031 * t) * (1 + .009 * math.sin(5 * angle + z * 1.7)
                                            + .004 * math.sin(13 * angle - z * 2.1))
            vertices.append((center_x + radius * math.cos(angle),
                             radius * math.sin(angle), z))
    faces = []
    for ring in range(len(rings) - 1):
        for index in range(sides):
            next_index = (index + 1) % sides
            faces.append((ring*sides+index, ring*sides+next_index,
                          (ring+1)*sides+next_index, (ring+1)*sides+index))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(rings)-1)*sides+i for i in range(sides)))
    mesh = bpy.data.meshes.new(f"Torii_Post_{side}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"Torii_Post_{side}", mesh)
    active_collection.objects.link(obj)
    mesh.materials.append(LACQUER)
    for face in mesh.polygons[:-2]:
        face.use_smooth = True
    return obj


def torii_worn_lacquer(side, name, z0, z1, angle_center, angle_width):
    """Expose an irregular patch of underlying timber on the approach face."""
    columns, rows = 8, 3
    vertices = []
    for row in range(rows):
        for column in range(columns + 1):
            u = column / columns
            angle = angle_center + (u - .5) * angle_width
            saw = .026 * math.sin((column + 1) * 2.47 + side * .7)
            z = (z0 + saw if row == 0 else
                 z1 + .017 * math.sin(column * 3.13) if row == rows - 1 else
                 (z0 + z1) * .5 + .014 * math.sin(column * 1.81))
            t = (z - .43) / 4.41
            center_x = side * (2.35 - .043 * t)
            radius = (.230 - .031*t) * 1.018
            vertices.append((center_x + radius * math.cos(angle),
                             radius * math.sin(angle), z))
    faces = []
    for row in range(rows - 1):
        for column in range(columns):
            a = row * (columns+1) + column
            faces.append((a, a+1, a+columns+2, a+columns+1))
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    active_collection.objects.link(obj)
    mesh.materials.append(TIMBER)
    return obj


active_collection = ASSETS["SM_Edo_LanternPost"]
# A 3.6 m street post, socketed into stone, with a hung four-panel lantern.
box("Stone_Footing", (0, 0, .14), (.42, .42, .28), STONE, .018)
box("Timber_Post", (0, 0, 1.76), (.14, .14, 3.13), TIMBER, .015)
for z in (.40, 2.58, 3.20):
    box(f"Iron_PostCollar_{z}", (0, 0, z), (.165, .165, .055), AGED_IRON, .006)
box("Swept_Arm", (.29, 0, 3.27), (.68, .115, .11), TIMBER, .02)
box("Arm_EndCap", (.635, 0, 3.27), (.04, .14, .14), BRASS, .005)
tube("Lantern_Hanger", [(.59, 0, 3.22), (.59, 0, 3.07), (.59, 0, 2.99)], .008, AGED_IRON)
cylinder("Lantern_TopKnob", (.59, 0, 2.95), .065, .075, BRASS)
for z, width, depth in ((2.89, .49, .41), (2.82, .55, .46), (2.24, .48, .40), (2.19, .55, .46)):
    box(f"Lantern_Cap_{z}", (.59, 0, z), (width, depth, .055), TIMBER, .008)
for side in (-1, 1):
    x = .59 + side * .215
    box(f"Paper_X_{side}", (x, 0, 2.54), (.012, .35, .52), WASHI, .001)
    for j in (-1, 0, 1):
        box(f"X_Lattice_{side}_{j}", (x + side * .009, j * .115, 2.54), (.014, .012, .53), TIMBER, .001)
    y = side * .185
    box(f"Paper_Y_{side}", (.59, y, 2.54), (.42, .012, .52), WASHI, .001)
    for j in (-1, 0, 1):
        box(f"Y_Lattice_{side}_{j}", (.59 + j * .14, y + side * .008, 2.54), (.012, .014, .53), TIMBER, .001)
for z in (2.35, 2.53, 2.71):
    box(f"Horizontal_Lattice_{z}", (.59, -.195, z), (.47, .018, .012), TIMBER, .002)
cylinder("Amber_LightCore", (.59, 0, 2.52), .05, .35, WARM_GLOW, 16)
tube("Tassel_Cord", [(.59, 0, 2.16), (.59, 0, 2.02)], .007, INDIGO)
for j in range(7):
    a = j * math.tau / 7
    tube(f"Tassel_{j}", [(.59, 0, 2.02), (.59 + .017 * math.cos(a), .017 * math.sin(a), 1.91)], .002, INDIGO, 1)


active_collection = ASSETS["SM_Nyaagyu_ToriiGate"]
# 5.5 m wide gate, visible from the estate road. Occupation hardware is removable.
for side in (-1, 1):
    x = side * 2.35
    box(f"Torii_StoneBase_{side}", (x, 0, .22), (.55, .53, .44), STONE, .02)
    torii_post(side)
    for z in (.46, 3.75, 4.78):
        crown = side * (2.35 - .043 * max(0, (z-.43)/4.41))
        cylinder(f"Torii_AccentedCollar_{side}_{z}", (crown, 0, z),
                 .251 if z < 1 else .222, .035, AGED_IRON, 48)
    cylinder(f"Torii_PostCap_{side}", (side*2.307, 0, 4.89), .224,
             .10, BRASS, 48)
    torii_worn_lacquer(side, f"Torii_ExposedTimber_Foot_{side}",
                       .64, .85, -math.pi/2, .52)
    torii_worn_lacquer(side, f"Torii_ExposedTimber_Mid_{side}",
                       2.12, 2.25, -math.pi/2-.28, .36)
    torii_worn_lacquer(side, f"Torii_ExposedTimber_Upper_{side}",
                       3.44, 3.54, -math.pi/2+.37, .26)
torii_lintel("Curved_Kasagi", 2.88, 4.94, .36, .58, LACQUER)
torii_lintel("Kasagi_IronCrown", 2.96, 5.31, .055, .61, AGED_IRON)
box("Shimaki_Underbeam", (0, 0, 4.81), (5.15, .40, .14), LACQUER, .018)
box("Nuki_Crossbeam", (0, 0, 3.91), (5.20, .22, .20), TIMBER, .014)
for side in (-1, 1):
    box(f"Nuki_EndBrace_{side}", (side * 2.52, 0, 3.91), (.15, .31, .28), BRASS, .005)
    # Thin repair inlay gives the gate a distinct Nyaagyu resistance identity.
    tube(f"Rescue_RepairSeam_{side}", [(side*2.36, -.193, 2.55), (side*2.36, -.193, 3.48)], .007, BRASS)
label("Gate_NamePlaque", "猫柳生", (0, -.122, 4.05), .18, BRASS)
cylinder("Gate_SORAKamon_backplate", (0, -.324, 5.115), .165, .015,
         AGED_IRON, 32, (math.pi / 2, 0, 0))
gate_sora_kamon("gate", 0, -.337, 5.115, .255, BRASS)


active_collection = ASSETS["SM_Alien_DebtKiosk"]
# The debt machine reads as a hostile insertion into an Edo workshop.
box("Kiosk_StoneFoot", (0, 0, .10), (1.53, .80, .20), STONE, .025)
box("Kiosk_Shell", (0, .06, 1.11), (1.35, .58, 1.92), METAL, .048)
box("Kiosk_IndigoFront", (0, -.247, 1.25), (1.16, .04, 1.46), INDIGO, .018)
box("Kiosk_RoofLip", (0, -.01, 2.10), (1.50, .73, .10), AGED_IRON, .018)
for side in (-1, 1):
    x = side * .59
    box(f"Brass_EdgeRail_{side}", (x, -.283, 1.16), (.025, .028, 1.76), BRASS, .003)
    for z in (.40, .68, 1.92):
        cylinder(f"Rail_Rivet_{side}_{z}", (x, -.306, z), .019, .013, BRASS, 12, (math.pi / 2, 0, 0))
    for i in range(6):
        box(f"Coolant_Vent_{side}_{i}", (side*.56, .358, .65+i*.105), (.065, .02, .033), AGED_IRON, .003)
box("Display_Bezel", (0, -.31, 1.57), (.99, .055, .62), AGED_IRON, .022)
box("Holographic_Display", (0, -.342, 1.57), (.86, .008, .49), CYAN_GLOW, .005)
label("Debt_Title_Japanese", "負債", (0, -.352, 1.66), .15, RED_GLOW)
label("Debt_Number", "∞", (0, -.353, 1.45), .17, WASHI)
box("Deed_Receiver", (0, -.33, .98), (.74, .06, .16), AGED_IRON, .014)
box("Deed_Slot", (0, -.367, 1.01), (.59, .010, .029), RED_GLOW, .004)
for i in range(9):
    box(f"Grille_Slat_{i}", (-.28+i*.07, -.361, .72), (.024, .009, .16), BRASS, .002)
cylinder("Vault_Wheel", (0, -.38, .40), .21, .07, BRASS, 32, (math.pi / 2, 0, 0))
cylinder("Vault_Hub", (0, -.425, .40), .085, .04, AGED_IRON, 32, (math.pi / 2, 0, 0))
for j in range(8):
    a = j * math.tau / 8
    x = .17 * math.cos(a)
    z = .40 + .17 * math.sin(a)
    cylinder(f"Wheel_Pin_{j}", (x, -.428, z), .016, .026, AGED_IRON, 12, (math.pi / 2, 0, 0))
for side in (-1, 1):
    x = side * .53
    tube(f"Fiber_Umbilical_{side}", [(x, .36, .40), (x*1.19, .40, .63), (x*1.15, .38, 1.3), (x, .33, 1.83)], .021, CYAN_GLOW)
    cylinder(f"Alien_Antenna_{side}", (side*.50, .06, 2.20), .025, .21, AGED_IRON, 12)
    cylinder(f"Antenna_Tip_{side}", (side*.50, .06, 2.33), .045, .035, CYAN_GLOW, 16)


def collision_box(name, loc, dims):
    # Stored in FBX as UCX meshes, never part of the visible Blender preview.
    obj = box(name, loc, dims, AGED_IRON)
    return obj


collision = {
    "SM_Edo_LanternPost": [((0, 0, 1.75), (.18, .18, 3.5))],
    "SM_Nyaagyu_ToriiGate": [((-2.35, 0, 2.5), (.42, .42, 5.0)),
                                ((2.35, 0, 2.5), (.42, .42, 5.0)),
                                ((0, 0, 5.11), (5.75, .60, .49))],
    "SM_Alien_DebtKiosk": [((0, .04, 1.1), (1.4, .64, 2.2))],
}
# The editable .blend is the texture source of truth. The FBX importer is
# configured to ignore FBX textures and binds pinned Unreal PBR instances by
# material slot, so exporting image nodes would only embed machine-local paths.
linked_images = [(node, node.image) for mat in (TIMBER, METAL, STONE)
                 for node in mat.node_tree.nodes if node.type == "TEX_IMAGE"]
for node, _ in linked_images:
    node.image = None
stats = []
for asset_name, coll in ASSETS.items():
    active_collection = coll
    parts = [obj for obj in coll.objects if obj.type == "MESH"]
    triangles = sum(sum(len(poly.vertices)-2 for poly in ob.data.polygons) for ob in parts)
    corners = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
    minimum = [round(min(point[axis] for point in corners), 3) for axis in range(3)]
    maximum = [round(max(point[axis] for point in corners), 3) for axis in range(3)]
    # Join duplicates for a stable one-render-mesh FBX without destroying editable parts.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.duplicate()
    copies = list(bpy.context.selected_objects)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    render_obj = bpy.context.object
    render_obj.name = asset_name
    render_obj["author"] = "Original SORA Arena project-owned geometry"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    proxy_objects = []
    for i, (loc, dims) in enumerate(collision[asset_name]):
        proxy_objects.append(collision_box(f"UCX_{asset_name}_{i:02d}", loc, dims))
    bpy.ops.object.select_all(action="DESELECT")
    render_obj.select_set(True)
    for obj in proxy_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = render_obj
    fbx = OUT / (asset_name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, global_scale=1.0, axis_forward="-Y", axis_up="Z",
        add_leaf_bones=False, bake_anim=False, path_mode="STRIP")
    for obj in proxy_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.objects.remove(render_obj, do_unlink=True)
    stats.append({"name": asset_name, "fbx": fbx.name, "fbx_sha256": hashlib.sha256(fbx.read_bytes()).hexdigest(),
                  "editable_parts": len(parts), "source_triangles": triangles,
                  "collision_boxes": len(collision[asset_name]), "bounds_m": {"min": minimum, "max": maximum},
                  "world_builder_yaw_offset_deg": 0 if asset_name == "SM_Edo_LanternPost" else 90,
                  "placement_origin": "Ground plane at world origin; local -Y is the visible front",
                  "local_span_axis": "+X" if asset_name == "SM_Nyaagyu_ToriiGate" else "object-dependent"})
for node, image in linked_images:
    node.image = image


# Duplicate the editable assets into a compact review stage. No preview objects
# are exported; originals remain at the correct ground-plane origin in the blend.
preview = bpy.data.collections.new("Review_Stage_NotForFBX")
SCENE.collection.children.link(preview)
for asset_name, coll in ASSETS.items():
    offset = {"SM_Edo_LanternPost": -4.0, "SM_Nyaagyu_ToriiGate": 0,
              "SM_Alien_DebtKiosk": 4.05}[asset_name]
    for obj in coll.objects:
        clone = obj.copy()
        clone.data = obj.data
        clone.location.x += offset
        preview.objects.link(clone)
        obj.hide_render = True

active_collection = preview
box("Preview_StoneStage", (0, 0, -.13), (11.3, 3.1, .24), STONE, .06)
for x in (-4.0, 0, 4.05):
    box(f"Preview_AssetPedestal_{x}", (x, 0, -.01), (2.7 if x else 6.3, 1.25, .12), AGED_IRON, .025)

def area(name, loc, color, power, size, target=(0, 0, 2.1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = power
    obj.data.color = color
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return keep(obj, name)

area("Warm_Lantern_Key", (-4.3, -2.6, 5.5), (1, .68, .34), 450, 4.5)
area("Cool_Occupier_Rim", (4, 3.8, 6), (.42, .72, 1), 620, 5.0)
area("Front_Softbox", (1, -5.5, 6), (1, .93, .82), 780, 8.0)
bpy.ops.object.light_add(type="POINT", location=(-3.41, 0, 2.52))
lantern_light = keep(bpy.context.object, "Preview_Lantern_Interior")
lantern_light.data.energy = 34
lantern_light.data.color = (1, .48, .16)
bpy.ops.object.camera_add(location=(8.2, -16, 9.7))
camera = keep(bpy.context.object, "AssetReview_Camera")
camera.rotation_euler = (Vector((0, 0, 2.55)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 13.6
SCENE.camera = camera
SCENE.world.color = (.035, .045, .06)
SCENE.render.engine = "CYCLES"
SCENE.cycles.samples = 32
SCENE.cycles.use_denoising = True
SCENE.render.resolution_x = 1600
SCENE.render.resolution_y = 960
SCENE.render.resolution_percentage = 100
SCENE.view_settings.view_transform = "AgX"
SCENE.view_settings.exposure = -.7
preview_path = OUT / "Edo_Alien_PropReview_Blender.png"
SCENE.render.image_settings.file_format = "PNG"
SCENE.render.filepath = str(preview_path)
bpy.ops.render.render(write_still=True)

bpy.ops.object.camera_add(location=(6.8, -6.2, 4.3))
detail_camera = keep(bpy.context.object, "Kiosk_Detail_Camera")
detail_camera.rotation_euler = (Vector((4.05, 0, 1.22)) - detail_camera.location).to_track_quat("-Z", "Y").to_euler()
detail_camera.data.type = "ORTHO"
detail_camera.data.ortho_scale = 3.1
SCENE.camera = detail_camera
SCENE.render.resolution_x = 1024
SCENE.render.resolution_y = 1024
detail_path = OUT / "Alien_DebtKiosk_Detail_Blender.png"
SCENE.render.filepath = str(detail_path)
bpy.ops.render.render(write_still=True)
SCENE.camera = camera
SCENE.render.resolution_x = 1600
SCENE.render.resolution_y = 960
SCENE.render.filepath = str(preview_path)

blend = OUT / "Edo_Alien_Props.blend"
# The render above needs absolute paths in an unsaved headless scene. Store
# portable project-relative paths only after it is complete.
for image in bpy.data.images:
    if image.source == "FILE":
        image.filepath = bpy.path.relpath(image.filepath, start=str(OUT))
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest_path = OUT / "manifest.json"
manifest_path.write_text(json.dumps({
    "schema_version": 2,
    "generator": "scripts/art/create_edo_environment_props.py",
    "sora_kamon_svg_sha256": SORA_LOGO_RECORD["source_sha256"],
    "sora_kamon_placement": "Nyaagyu torii gate front lintel",
    "generator_blender": bpy.app.version_string,
    "license": "Original project-owned geometry; no purchased meshes. Linked palette maps are CC0 Poly Haven files with separate manifest.",
    "source_blend": blend.name,
    "preview": preview_path.name,
    "detail_preview": detail_path.name,
    "units": "Blender meters; Unreal import converts to centimeters",
    "fbx_design": "One joined render mesh per asset plus named UCX convex collision boxes; editable source parts remain in the .blend.",
    "lantern_light_local_z_m": 2.52,
    "texture_dependency": "../PolyHaven/manifest.json (relative links in source blend; FBX uses material roles without embedded paths)",
    "scope": "Original source art and Blender review render only. UE 5.8.2 import, materials, lighting, gameplay, and performance are unverified.",
    "assets": stats,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("EDO_ENVIRONMENT_PROPS_READY", [(a["name"], a["source_triangles"]) for a in stats], preview_path)
