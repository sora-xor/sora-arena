"""Author an original Edo-inspired Nyaagyu estate dojo for SORA Arena.

Run with the pinned Blender 5.2 LTS:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_dojo.py

The editable .blend contains individual architectural parts and portable links
to the project's CC0 PBR palette. The FBX has one render mesh and separate UCX
boxes. Its source render is an art review, not evidence of Unreal visual quality.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuDojo"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
SORA_SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SORA_LOGO = json.loads((SORA_SVG.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(SORA_SVG.read_bytes()).hexdigest() == SORA_LOGO["source_sha256"]
NAME = "SM_Nyaagyu_EstateDojo"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
SCENE = bpy.context.scene
SCENE.unit_settings.system = "METRIC"
SCENE.unit_settings.scale_length = 1.0
EDITABLE = bpy.data.collections.new("Nyaagyu_EstateDojo_Editable")
SCENE.collection.children.link(EDITABLE)


def material(name, color, metal=0.0, rough=0.6, emission=0.0):
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


def palette(role, asset_id, scale):
    """Match existing Unreal material-slot roles while retaining Blender PBR links."""
    folder = PALETTE / asset_id
    mat = material("M_Env_" + role, (.30, .25, .20), rough=.72)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale,) * 3
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    images = {}
    for channel, marker in (("diffuse", "_diff_"), ("normal", "_nor_dx_"), ("arm", "_arm_")):
        path = next(folder.glob("*" + marker + "*"))
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.name = channel
        node.image = image
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        images[channel] = node
    links.new(images["diffuse"].outputs["Color"], shader.inputs["Base Color"])
    arm = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], arm.inputs["Color"])
    links.new(arm.outputs["Green"], shader.inputs["Roughness"])
    links.new(arm.outputs["Blue"], shader.inputs["Metallic"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"], split.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    links.new(split.outputs["Green"], invert.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(split.outputs["Red"], rgb.inputs["Red"])
    links.new(invert.outputs[0], rgb.inputs["Green"])
    links.new(split.outputs["Blue"], rgb.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .6
    links.new(rgb.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


TIMBER = palette("Timber", "wood_planks_dirt", 2.8)
STONE = palette("Stone", "stone_floor", 1.4)
IRON = material("M_Dojo_BlackenedIron", (.027, .032, .034), .72, .54)
PLASTER = material("M_Dojo_LimePlaster", (.57, .53, .44), 0, .91)
WASHI = material("M_Dojo_Washi", (.74, .66, .51), 0, .82)
SHADE = material("M_Dojo_CharredCedar", (.075, .059, .045), 0, .76)
ROOF = [material("M_Dojo_Kawara_%d" % i, color, 0, .82) for i, color in enumerate((
    (.10, .13, .145), (.13, .15, .16), (.075, .10, .11)))]
for tile in ROOF:
    # Subtle nonrepeating firing variation and lime deposits avoid a flat
    # single-color procedural roof while keeping this source fully original.
    nodes, links = tile.node_tree.nodes, tile.node_tree.links
    shader = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 48
    noise.inputs["Detail"].default_value = 4
    noise.inputs["Roughness"].default_value = .72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .25
    ramp.color_ramp.elements[0].color = (.043, .057, .065, 1)
    ramp.color_ramp.elements[1].position = .78
    ramp.color_ramp.elements[1].color = (.18, .20, .205, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .14
    bump.inputs["Distance"].default_value = .022
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
LACQUER = material("M_Dojo_ResistanceRed", (.37, .021, .022), .07, .36)
GOLD = material("M_Dojo_AgedBrass", (.41, .29, .13), .71, .39)
LANTERN = material("M_Dojo_LanternWashi", (.95, .56, .23), 0, .65, .3)


def keep(obj, name, mat=None, collection=EDITABLE):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena Edo-inspired dojo geometry"
    return obj


def box(name, loc, dims, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("worn_arris", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def beam(name, start, end, width, depth, mat):
    middle = (Vector(start) + Vector(end)) * .5
    delta = Vector(end) - Vector(start)
    obj = box(name, middle, (width, depth, delta.length), mat, .008)
    obj.rotation_euler = delta.to_track_quat("Z", "Y").to_euler()
    return obj


def mesh(name, vertices, faces, mat, mat_indices=None, materials=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    EDITABLE.objects.link(obj)
    mats = materials or [mat]
    for item in mats:
        obj.data.materials.append(item)
    if mat_indices:
        for poly, index in zip(data.polygons, mat_indices):
            poly.material_index = index
    obj["author"] = "Original SORA Arena Edo-inspired dojo geometry"
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=24, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=loc, rotation=rotation)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = radius
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, xyz in zip(spline.points, points):
        p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    EDITABLE.objects.link(obj)
    data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def text_mesh(name, body, loc, size, mat):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.data.body = body
    obj.data.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = .002
    obj.data.bevel_depth = .0008
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def sora_kamon(name, x, front_y, z, diameter):
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SORA_SVG))
    curves = [ob for ob in set(bpy.data.objects) - before if ob.type == "CURVE"]
    assert len(curves) == 2, [ob.name for ob in curves]
    corners = [ob.matrix_world @ Vector(corner) for ob in curves for corner in ob.bound_box]
    lo_x, hi_x = min(v.x for v in corners), max(v.x for v in corners)
    lo_y, hi_y = min(v.y for v in corners), max(v.y for v in corners)
    center_x, center_y = (lo_x + hi_x) / 2, (lo_y + hi_y) / 2
    scale = diameter / max(hi_x - lo_x, hi_y - lo_y)
    for i, ob in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.convert(target="MESH")
        ob = bpy.context.object
        for vertex in ob.data.vertices:
            p = ob.matrix_world @ vertex.co
            vertex.co = (x + (p.x - center_x) * scale, front_y,
                         z + (p.y - center_y) * scale)
        ob.matrix_world.identity()
        ob = keep(ob, f"UserSupplied_SORAKamon_{name}_Path_{i}")
        ob.data.materials.clear()
        ob.data.materials.append(GOLD)
        ob["source_svg_sha256"] = SORA_LOGO["source_sha256"]


# Raised plinth, cut stone courses, and visible ground-to-floor posts. The
# approximate footprint matches an existing 650 x 700 cm world-builder block.
box("Foundation_Core", (0, 0, .25), (6.30, 6.34, .50), STONE, .035)
for side in (-1, 1):
    y = side * 3.12
    for row in range(2):
        for col in range(13):
            x = -2.91 + col * .485 + (.24 if row % 2 else 0)
            if x > 3.06:
                continue
            box(f"FrontBack_Quoin_{side}_{row}_{col}", (x, y, .10 + .22*row),
                (.465, .13, .205), STONE, .01)
for side in (-1, 1):
    x = side * 3.12
    for row in range(2):
        for col in range(13):
            y = -2.9 + col * .48 + (.23 if row % 2 else 0)
            if y > 3.04:
                continue
            box(f"Gable_Quoin_{side}_{row}_{col}", (x, y, .10+.22*row),
                (.13, .46, .205), STONE, .01)

box("Raised_Timber_Floor", (0, 0, .69), (5.96, 5.84, .15), TIMBER, .015)
for x in (-2.76, -1.38, 0, 1.38, 2.76):
    for y in (-2.64, 0, 2.64):
        box(f"Underfloor_Pier_{x}_{y}", (x, y, .49), (.25, .25, .28), SHADE, .012)
for x in (-2.78, -1.39, 0, 1.39, 2.78):
    box(f"Floor_Joist_{x}", (x, 0, .58), (.095, 6.13, .13), SHADE, .009)

# A recessed front shoji line and an engawa at local -Y give depth and a
# convincing human-height scale when viewed from the road.
box("Front_Engawa", (0, -3.05, .74), (6.08, 1.08, .105), TIMBER, .012)
for index in range(13):
    x = -2.86 + index * .477
    box(f"Engawa_Board_Seam_{index:02d}", (x, -3.06, .799), (.012, 1.04, .005), SHADE)
for x in (-2.55, 0, 2.55):
    box(f"Engawa_Foot_{x}", (x, -3.37, .52), (.18, .18, .36), SHADE, .008)
for i in range(3):
    box(f"Shikidai_Step_{i}", (0, -3.66-i*.16, .57-i*.11),
        (2.00+i*.18, .24, .11), TIMBER, .01)

# Timber bay system, exposed nuki rails and ceiling perimeter. White plaster
# is nonstructural infill; the door leaves remain closed in this visual mesh.
post_x = (-2.84, -1.42, 0, 1.42, 2.84)
for side in (-1, 1):
    for x in post_x:
        box(f"Cedar_Post_{side}_{x}", (x, side*2.70, 2.12), (.165, .18, 2.75),
            TIMBER, .014)
    for z in (1.03, 3.24, 3.49):
        box(f"Nuki_FrontBack_{side}_{z}", (0, side*2.70, z),
            (5.91, .205, .14), TIMBER, .012)
for side in (-1, 1):
    for y in (-2.70, -.90, .90, 2.70):
        box(f"Gable_Post_{side}_{y}", (side*2.86, y, 2.13), (.17, .17, 2.72), TIMBER, .012)
    for z in (1.11, 3.24, 3.49):
        box(f"Gable_Nuki_{side}_{z}", (side*2.86, 0, z),
            (.20, 5.59, .13), TIMBER, .01)
    for idx, y in enumerate((-1.82, 0, 1.82)):
        box(f"Gable_Plaster_{side}_{idx}", (side*2.81, y, 2.16),
            (.065, 1.56, 1.95), PLASTER, .006)
        box(f"Gable_Wainscot_{side}_{idx}", (side*2.86, y, 1.21),
            (.082, 1.55, .42), SHADE, .004)
        for k in range(5):
            box(f"Gable_WainscotSeam_{side}_{idx}_{k}",
                (side*2.91, y-.62+k*.31, 1.21), (.006, .012, .39), TIMBER)
for idx, x in enumerate((-2.13, -.71, .71, 2.13)):
    box(f"Rear_Plaster_{idx}", (x, 2.68, 2.33), (1.29, .06, 1.66), PLASTER, .008)
    box(f"Rear_Wainscot_{idx}", (x, 2.71, 1.18), (1.26, .09, .40), SHADE, .004)


def shoji_bay(index, center_x):
    # The paper panels sit behind a complete thin cedar lattice, offset into
    # the veranda shade. Their small elements matter at near-FPS distance.
    y = -2.765
    bottom, top = .94, 3.23
    box(f"Shoji_Paper_{index}", (center_x, y+.014, (bottom+top)/2),
        (1.28, .022, top-bottom), WASHI)
    for side in (-1, 1):
        box(f"Shoji_Jamb_{index}_{side}", (center_x+side*.65, y-.018, 2.08),
            (.045, .045, 2.32), SHADE, .004)
    for col in range(1, 5):
        box(f"Shoji_KumikoV_{index}_{col}", (center_x-.65+col*.26, y-.03, 2.08),
            (.013, .025, 2.27), TIMBER, .002)
    for row in range(1, 9):
        box(f"Shoji_KumikoH_{index}_{row}",
            (center_x, y-.031, bottom+row*(top-bottom)/9),
            (1.30, .025, .013), TIMBER, .002)
    cylinder(f"Shoji_Pull_{index}", (center_x+.47, y-.058, 1.96),
             .025, .018, IRON, 16, (math.pi/2, 0, 0))


for index, center_x in enumerate((-2.13, -.71, .71, 2.13)):
    shoji_bay(index, center_x)

# Layered roof assembly: 4.1 m deep slopes, 0.7 m eaves, individual shallow
# curved kawara tiles, overlapping courses, ridge caps and hanging end caps.
eave_z, ridge_z, half_eave_y = 3.67, 5.06, 3.74
box("Roof_Ceiling", (0, 0, 3.56), (6.46, 6.57, .11), SHADE, .016)
for x in (-3.12, -2.34, -1.56, -.78, 0, .78, 1.56, 2.34, 3.12):
    for side in (-1, 1):
        beam(f"Exposed_Rafter_{x}_{side}", (x, 0, ridge_z-.21),
             (x, side*3.68, eave_z-.18), .105, .13, TIMBER)
for side in (-1, 1):
    y = side*3.69
    box(f"Eave_Fascia_{side}", (0, y, eave_z-.08),
        (7.03, .13, .15), SHADE, .018)
    for i in range(14):
        x = -3.25+i*.5
        box(f"Eave_Bracket_{side}_{i}", (x, side*3.47, 3.47),
            (.095, .46, .25), TIMBER, .008)

tile_vertices, tile_faces, tile_materials = [], [], []
cols, rows = 34, 11
tile_dx = 7.26 / cols
tile_dy = half_eave_y / rows
for side in (-1, 1):
    for row in range(rows):
        for col in range(cols):
            x0 = -3.63 + col*tile_dx
            # Repeated offset courses and a slight pan/cap curve catch highlights.
            offset = .025 if row % 2 else 0
            y0 = row*tile_dy
            start = len(tile_vertices)
            for iy in range(3):
                y = y0 + iy*(tile_dy+.018)/2
                yy = side * min(half_eave_y, y)
                base_z = ridge_z-(ridge_z-eave_z)*abs(yy)/half_eave_y
                for ix in range(5):
                    fx = ix/4
                    x = x0+fx*tile_dx
                    bulge = .025*math.sin(math.pi*fx)
                    toe = .013 if iy==2 else 0
                    tile_vertices.append((x, yy, base_z+.037+bulge+toe+offset))
            for iy in range(2):
                for ix in range(4):
                    a = start+iy*5+ix
                    tile_faces.append((a, a+1, a+6, a+5) if side < 0
                                      else (a+5, a+6, a+1, a))
                    tile_materials.append((col*11+row*7) % 17 == 0 and 2 or
                                          ((col+row*3) % 5 == 0 and 1 or 0))
roof_tiles = mesh("Kawara_CurvedTileCourses", tile_vertices, tile_faces, ROOF[0],
                  tile_materials, ROOF)
for side in (-1, 1):
    for row in range(rows):
        y = side*min(half_eave_y, (row+1)*tile_dy)
        z = ridge_z-(ridge_z-eave_z)*abs(y)/half_eave_y+.064
        tube(f"Kawara_Overlap_{side}_{row}", [(-3.63,y,z),(3.63,y,z)], .010, ROOF[2])
for col in range(cols):
    x = -3.56+(col+.5)*tile_dx
    cylinder(f"Ridge_RoundCap_{col}", (x, 0, ridge_z+.08), .105,
             tile_dx+.008, ROOF[(col%7)==0 and 1 or 0], 16, (0, math.pi/2, 0))
for side in (-1, 1):
    # Raised gable verge strip frames the end wall and expresses roof pitch.
    x = side*3.60
    for slope_side in (-1, 1):
        beam(f"Gable_Vergebord_{side}_{slope_side}",
             (x, 0, ridge_z+.065), (x, slope_side*half_eave_y, eave_z+.05),
             .055, .12, ROOF[2])
for side in (-1, 1):
    # Triangular lime infill, tucked behind the gable-end rake boards.
    x = side*2.82
    vertices = [(x,-2.7,3.55), (x,2.7,3.55), (x,0,4.67)]
    mesh(f"Gable_PlasterTriangle_{side}", vertices, [(0,1,2)], PLASTER)
    for sl in (-1,1):
        beam(f"Gable_TimberDiagonal_{side}_{sl}", (x,0,4.70),
             (x,sl*2.70,3.54), .07,.12,TIMBER)

# Front hall sign and exact supplied SORA mon (no recreated logo paths).
box("Dojo_FrontSign", (0, -2.84, 3.43), (1.82, .10, .37), SHADE, .014)
text_mesh("Dojo_JapaneseSign", "猫柳生道場", (0,-2.906,3.39), .23, GOLD)
for x in (-1.12, 1.12):
    cylinder(f"Kamon_Disc_{x}", (x,-2.89,3.43), .137,.020, IRON,32,(math.pi/2,0,0))
    sora_kamon("dojo_left" if x < 0 else "dojo_right", x, -2.906,3.43,.205)
for x in (-2.60,2.60):
    box(f"Lantern_Bracket_{x}", (x,-2.94,3.13), (.20,.48,.10),SHADE,.01)
    box(f"Lantern_Frame_{x}", (x,-3.23,2.89), (.26,.25,.40),SHADE,.009)
    box(f"Lantern_Glow_{x}", (x,-3.366,2.89), (.20,.012,.33),LANTERN,.004)
    for side in (-1,1):
        box(f"Lantern_Vert_{x}_{side}", (x+side*.105,-3.385,2.89),
            (.014,.013,.35),SHADE,.002)
    for z in (2.77,2.98):
        box(f"Lantern_Horiz_{x}_{z}", (x,-3.385,z),(.22,.013,.013),SHADE,.002)

# Preserve the editable source as separate, physically legible parts. Export a
# temporary combined render mesh so Unreal sees one material-slotted asset.
parts = [ob for ob in EDITABLE.objects if ob.type == "MESH"]
triangles = sum(len(poly.vertices)-2 for ob in parts for poly in ob.data.polygons)
corners = [ob.matrix_world @ Vector(corner) for ob in parts for corner in ob.bound_box]
minimum = [round(min(p[axis] for p in corners), 3) for axis in range(3)]
maximum = [round(max(p[axis] for p in corners), 3) for axis in range(3)]
linked_images = [(node,node.image) for mat in (TIMBER,STONE)
                 for node in mat.node_tree.nodes if node.type=="TEX_IMAGE"]
for node,_ in linked_images:
    node.image=None
bpy.ops.object.select_all(action="DESELECT")
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
render = bpy.context.object
render.name = NAME
render["author"] = "Original SORA Arena Edo-inspired dojo geometry"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
proxies=[]
for i,(loc,dims) in enumerate([
    ((0,0,1.95),(5.8,5.55,3.9)),
    ((0,-3.10,.43),(6.05,1.03,.86)),
    ((0,0,4.31),(7.18,7.40,1.55)),
]):
    proxies.append(box(f"UCX_{NAME}_{i:02d}",loc,dims,IRON))
bpy.ops.object.select_all(action="DESELECT")
render.select_set(True)
for obj in proxies:
    obj.select_set(True)
bpy.context.view_layer.objects.active=render
fbx=OUT/(NAME+".fbx")
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
    object_types={"MESH"},apply_unit_scale=True,global_scale=1.0,
    axis_forward="-Y",axis_up="Z",add_leaf_bones=False,bake_anim=False,path_mode="STRIP")
for ob in proxies:
    bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.objects.remove(render,do_unlink=True)
for node,image in linked_images:
    node.image=image

# Art-review stage: a ground strip and raking warm/cool light show the roof and
# facade depth. Review image is intentionally labelled in the manifest as
# Blender source art, never an Unreal capture or an AAA performance claim.
stage=bpy.data.collections.new("ArtReview_NotForFBX")
SCENE.collection.children.link(stage)
stage_floor=box("ArtReview_Floor",(0,0,-.16),(8.3,9.2,.30),STONE,.045)
for old in tuple(stage_floor.users_collection):old.objects.unlink(stage_floor)
stage.objects.link(stage_floor)
def area(name,loc,color,energy,size,target):
    bpy.ops.object.light_add(type="AREA",location=loc)
    ob=bpy.context.object
    ob.name=name
    ob.data.energy=energy
    ob.data.color=color
    ob.data.shape="DISK"
    ob.data.size=size
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler()
    return ob
area("Warm_Evening_Key",(-5.2,-7.3,9.0),(1,.72,.49),1550,8,(0,0,2.5))
area("Cool_Sky_Fill",(4.7,3.5,9.0),(.58,.72,1),1150,8,(0,0,2.5))
area("Front_Lantern_Fill",(1,-6.0,4.0),(1,.65,.40),260,4,(0,-2,2.5))
bpy.ops.object.camera_add(location=(10.3,-12.6,8.3))
camera=bpy.context.object
camera.name="Dojo_ArtReview_Camera"
camera.rotation_euler=(Vector((0,0,2.36))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO"
camera.data.ortho_scale=12.9
SCENE.camera=camera
SCENE.world.color=(.10,.12,.16)
SCENE.render.engine="CYCLES"
SCENE.cycles.samples=40
SCENE.cycles.use_denoising=True
SCENE.render.resolution_x=1600
SCENE.render.resolution_y=1100
SCENE.render.resolution_percentage=100
SCENE.view_settings.view_transform="AgX"
SCENE.view_settings.exposure=-.9
preview=OUT/"Nyaagyu_EstateDojo_Blender.png"
SCENE.render.image_settings.file_format="PNG"
SCENE.render.filepath=str(preview)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source=="FILE":
        image.filepath=bpy.path.relpath(image.filepath,start=str(OUT))
for font in bpy.data.fonts:
    if font.filepath and Path(bpy.path.abspath(font.filepath)).resolve() == FONT.resolve():
        font.filepath=bpy.path.relpath(str(FONT),start=str(OUT))
blend=OUT/"Nyaagyu_EstateDojo.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest={
    "schema_version":1,
    "name":NAME,
    "generator":"scripts/art/create_nyaagyu_dojo.py",
    "generator_blender":bpy.app.version_string,
    "source_blend":blend.name,
    "fbx":fbx.name,
    "preview":preview.name,
    "fbx_sha256":hashlib.sha256(fbx.read_bytes()).hexdigest(),
    "blend_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
    "preview_sha256":hashlib.sha256(preview.read_bytes()).hexdigest(),
    "sora_kamon_svg_sha256":SORA_LOGO["source_sha256"],
    "font_sha256":hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "palette_manifest_sha256":hashlib.sha256((PALETTE/"manifest.json").read_bytes()).hexdigest(),
    "palette_asset_ids":["wood_planks_dirt","stone_floor"],
    "unreal_asset":f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "source_parts":len(parts),
    "source_triangles":triangles,
    "roof_tile_count":cols*rows*2,
    "shoji_bays":4,
    "collision_boxes":3,
    "bounds_m":{"min":minimum,"max":maximum},
    "placement_origin":"Building ground center; local -Y is public frontage toward estate road",
    "placement_cm":"Replace the MapId 0 Building(P, FVector(650,700,Height), ...) visual at P; use yaw 0 for northern row and 180 for southern row, preserve the deterministic campaign collision box.",
    "collision_guidance":"The three UCX boxes are art-review proxies. Preserve the existing campaign kernel-compatible building collision in WorldBuilder; do not admit this decorative mesh into multiplayer map geometry without a versioned collision update.",
    "license":"Original project-owned geometry; exact user-supplied SORA SVG crest retains user-provided provenance. Linked timber and stone maps are CC0 Poly Haven, and Japanese Noto font is SIL OFL. No purchased assets.",
    "history_reference":[
        {"url":"https://kyoto.travel/en/destinations/the-former-retreat-of-tomomi-iwakura/","note":"Edo-era samurai-residence shikidai, veranda and shoin room arrangement inform the fictional dojo massing."},
        {"url":"https://www.nihonminkaen.jp/shukuba_english.html","note":"Museum documentation of an Edo-period samurai house gate and pantile roof informs the material language; this is not a reconstruction."}
    ],
    "scope":"Original source art and Blender review render. Unreal import, in-game presentation, historical reconstruction, and AAA performance are not established by this manifest."
}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("NYAAGYU_DOJO_READY",len(parts),triangles,(minimum,maximum),preview,flush=True)
