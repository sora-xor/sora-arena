"""Create the original Nyaagyu Arc carbine source, FBX, and Blender review image.

Run: blender -b --factory-startup --python scripts/art/create_arc_carbine.py
All geometry is original. Local +X is muzzle-forward, Z is up, and the local
origin is near the receiver/trigger. The source collection keeps editable parts;
the FBX is a single UV-unwrapped static mesh without external texture paths.
The review image is a Blender render, never an Unreal gameplay capture.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/Original"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
NAME = "SM_Nyaagyu_ArcCarbine"
BLEND = OUT / "Nyaagyu_ArcCarbine.blend"
FBX = OUT / (NAME + ".fbx")
PREVIEW = OUT / "Nyaagyu_ArcCarbine_Blender.png"
MANIFEST = OUT / "arc_carbine_manifest.json"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
asset = bpy.data.collections.new("ArcCarbine_Editable")
scene.collection.children.link(asset)


def material(name, color, metal=0.0, rough=.5, coat=0.0, glow=0.0, wear=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Coat Weight"].default_value = coat
    if glow:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = glow
    if wear:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = wear
        noise.inputs["Detail"].default_value = 3
        variation = nodes.new("ShaderNodeMapRange")
        variation.inputs["To Min"].default_value = rough * .78
        variation.inputs["To Max"].default_value = min(1.0, rough * 1.22)
        links.new(noise.outputs["Fac"], variation.inputs["Value"])
        links.new(variation.outputs["Result"], bsdf.inputs["Roughness"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .12
        bump.inputs["Distance"].default_value = .00008
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def palette(role, asset_id, scale):
    mat = material("M_Arc_" + role, (.24, .20, .15), role == "PatinatedMetal", .56)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale,) * 3
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    images = {}
    for channel, marker in (("diffuse", "_diff_"), ("normal", "_nor_dx_"), ("arm", "_arm_")):
        path = next((PALETTE / asset_id).glob("*" + marker + "*"))
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.name = channel
        node.image = image
        images[channel] = node
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
    links.new(images["diffuse"].outputs["Color"], bsdf.inputs["Base Color"])
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], channels.inputs["Color"])
    links.new(channels.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(channels.outputs["Blue"], bsdf.inputs["Metallic"])
    rgb = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"], rgb.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    links.new(rgb.outputs["Green"], invert.inputs[1])
    combined = nodes.new("ShaderNodeCombineColor")
    links.new(rgb.outputs["Red"], combined.inputs["Red"])
    links.new(invert.outputs[0], combined.inputs["Green"])
    links.new(rgb.outputs["Blue"], combined.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .55
    links.new(combined.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


LACQUER = material("M_Arc_OxbloodUrushi", (.074, .013, .012), .04, .22, .72, wear=44)
LACQUER_DARK = material("M_Arc_BlackUrushi", (.012, .015, .019), .05, .26, .58, wear=68)
BRONZE = material("M_Arc_AgedBronze", (.43, .24, .085), .92, .34, wear=96)
EDGE = material("M_Arc_BurnishedBronzeEdge", (.65, .42, .18), .93, .23, wear=115)
IRON = material("M_Arc_Gunmetal", (.038, .051, .061), .94, .35, wear=125)
CERAMIC = material("M_Arc_PorcelainInductor", (.47, .48, .42), .28, .30, wear=145)
COPPER = material("M_Arc_CoilCopper", (.48, .20, .075), .97, .23, wear=75)
JADE = material("M_Arc_IonJade", (.015, .42, .39), .25, .18, glow=2.2)
GLASS = material("M_Arc_SmokedGlass", (.025, .16, .16), .35, .13, glow=.18)
SILK = material("M_Arc_IndigoGripSilk", (.025, .044, .079), .0, .82, wear=160)
TIMBER = palette("Timber", "wood_planks_dirt", 2.5)
PATINA = palette("PatinatedMetal", "rusty_metal_02", 2.0)


def keep(obj, name, mat):
    obj.name = name
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena Arc carbine source geometry"
    return obj


def bevel(obj, amount, segments=2):
    if amount:
        mod = obj.modifiers.new("MachinedEdge", "BEVEL")
        mod.width = amount
        mod.segments = segments
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def box(name, center, size, mat, edge=.0015):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(obj, edge)


def cylinder(name, center, radius, depth, mat, vertices=20, axis="X"):
    rotation = (0, math.pi/2, 0) if axis == "X" else ((math.pi/2, 0, 0) if axis == "Y" else (0, 0, 0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=center, rotation=rotation)
    return bevel(keep(bpy.context.object, name, mat), min(.0012, depth*.18), 2)


def torus(name, x, radius, minor, mat):
    bpy.ops.mesh.primitive_torus_add(major_segments=24, minor_segments=6,
                                     location=(x, 0, .026), rotation=(0, math.pi/2, 0),
                                     major_radius=radius, minor_radius=minor)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat, sides=5):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 4
    curve.bevel_depth = radius
    curve.bevel_resolution = max(1, sides//2)
    spline = curve.splines.new("POLY")
    spline.points.add(len(points)-1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    asset.objects.link(obj)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj["author"] = "Original SORA Arena Arc carbine source geometry"
    return obj


def wedge(name, xz, half_width, mat):
    """An extruded polygon in XZ, with explicitly editable hard silhouette."""
    vertices = [(x, side*half_width, z) for side in (-1, 1) for x, z in xz]
    n = len(xz)
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    for i in range(n):
        j = (i+1) % n
        faces.append((i, j, n+j, n+i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena Arc carbine source geometry"
    return bevel(obj, .0015)


# Stock and receiver: a compact shoulder-fired carbine, lacquer inset over
# believable bronze/iron structure rather than a floating sci-fi outline.
wedge("ForgedReceiverCore", [(-.22,-.032),(.16,-.032),(.22,.020),(.15,.094),(-.17,.092),(-.23,.051)], .047, IRON)
wedge("RightUrushiReceiver", [(-.17,-.019),(.125,-.019),(.166,.022),(.116,.078),(-.14,.078)], .050, LACQUER)
box("ReceiverTopRail", (-.018,0,.104), (.376,.085,.022), BRONZE, .004)
box("ReceiverLowerRail", (.002,0,-.042), (.326,.083,.017), BRONZE, .003)
box("LeftStockSpar", (-.273,-.027,-.004), (.235,.019,.022), BRONZE, .003)
box("RightStockSpar", (-.273,.027,-.004), (.235,.019,.022), BRONZE, .003)
wedge("ShoulderStock_Lacquer", [(-.403,-.078),(-.328,-.074),(-.218,-.016),(-.248,.044),(-.354,.021),(-.414,-.010)], .036, LACQUER_DARK)
box("StockInsetTimber_Left", (-.343,-.037,-.030), (.102,.004,.050), TIMBER, .002)
box("StockInsetTimber_Right", (-.343,.037,-.030), (.102,.004,.050), TIMBER, .002)
box("BronzeButtplate", (-.419,0,-.038), (.017,.095,.130), PATINA, .003)
box("ButtplateWearLip", (-.428,0,-.038), (.003,.098,.136), EDGE, .0005)

# The indigo-wrapped grip sits slightly aft and below the mesh origin.
wedge("PistolGrip_OakCore", [(-.110,-.026),(-.048,-.026),(-.082,-.211),(-.145,-.206)], .032, TIMBER)
for index in range(7):
    z = -.057 - index*.021
    tube(f"IndigoIto_GripWrap_{index:02d}",
         [(-.146,-.033,z-.004),(-.132,-.037,z+.004),(-.097,.037,z+.010),(-.075,.035,z-.004)],
         .0024, SILK)
box("GripHeel_Ferrule", (-.113,0,-.210), (.074,.075,.018), BRONZE, .003)
box("TriggerGuard_Front", (-.018,0,-.088), (.012,.015,.099), BRONZE, .002)
box("TriggerGuard_Bottom", (-.060,0,-.141), (.112,.014,.011), BRONZE, .002)
box("TriggerGuard_Rear", (-.109,0,-.091), (.011,.015,.100), BRONZE, .002)
tube("ForgedTrigger", [(-.067,0,-.043),(-.067,0,-.087),(-.080,0,-.099)], .004, EDGE)
for side in (-1,1):
    box(f"ReceiverCheek_{side}", (-.061,side*.054,.031), (.270,.008,.067), LACQUER, .004)
    box(f"EngravedBrassLine_{side}", (-.048,side*.059,.067), (.227,.002,.002), EDGE, .0004)
    cylinder(f"ReceiverPin_{side}_A", (-.142,side*.061,.002), .005,.003, EDGE, 12, "Y")
    cylinder(f"ReceiverPin_{side}_B", (.084,side*.061,.002), .005,.003, EDGE, 12, "Y")

# Electrical induction train: porcelain core, individually readable copper
# winding, protected by open bronze ribs. This is visual only; kernel fire
# behavior and damage are defined elsewhere.
cylinder("PorcelainCore", (.277,0,.026), .027,.260,CERAMIC,24)
cylinder("BarrelInner", (.289,0,.026), .013,.370,IRON,20)
cylinder("BarrelShaft", (.393,0,.026), .019,.245,IRON,24)
for index in range(11):
    torus(f"CopperInductionCoil_{index:02d}", .173+index*.020, .039, .0045, COPPER)
for index in range(4):
    x = .162+index*.072
    torus(f"BronzeVentRib_{index:02d}", x, .047, .0028, BRONZE)
    box(f"VentRibFoot_{index:02d}", (x,0,-.031), (.007,.088,.012), BRONZE, .002)
box("VentHandguard_Top", (.292,0,.080), (.326,.080,.014), LACQUER_DARK, .003)
for side in (-1,1):
    box(f"HandguardRail_{side}", (.292,side*.053,.026), (.329,.008,.018), BRONZE, .002)
    for index in range(4):
        box(f"SilkFoundry_VentSlot_{side}_{index}", (.218+index*.045,side*.058,.026), (.023,.002,.005), IRON, .0007)
    tube(f"PlasmaConduit_{side}", [(.106,side*.055,-.007),(.195,side*.055,-.010),(.340,side*.055,-.010),(.447,side*.039,.011)],
         .0032, JADE)
box("ForwardGrip_Oak", (.252,0,-.052), (.105,.071,.025), TIMBER, .004)
for index in range(4):
    box(f"ForwardGrip_IndigoInlay_{index}", (.219+index*.019,0,-.067), (.007,.071,.003), SILK, .0005)

cylinder("MuzzleLockRing", (.484,0,.026), .033,.042,BRONZE,24)
cylinder("MuzzleBore", (.514,0,.026), .021,.020,IRON,24)
cylinder("MuzzleEmitter", (.526,0,.026), .013,.003,JADE,20)
torus("MuzzleBrightLip", .518, .026, .0026, EDGE)

# Sighting line is mechanically offset above the bore. The small cyan glass
# and crescent crest read up close but cannot obscure a competitive sightline.
box("RearSightBracket", (-.105,0,.139), (.060,.060,.052), BRONZE, .003)
box("RearSightGlass", (-.098,0,.169), (.033,.037,.010), GLASS, .001)
box("FrontSightBlade", (.444,0,.105), (.012,.008,.047), BRONZE, .001)
box("FrontSightPip", (.444,0,.130), (.005,.009,.004), JADE, .0005)
for side in (-1,1):
    box(f"Crest_Whisker_{side}", (-.009,side*.060,.031), (.073,.002,.0025), EDGE, .0003)
    box(f"Crest_Nose_{side}", (.030,side*.060,.026), (.011,.003,.010), EDGE, .0003)


parts = [obj for obj in asset.objects if obj.type == "MESH"]
source_triangles = sum(len(face.vertices)-2 for obj in parts for face in obj.data.polygons)
assert 3000 < source_triangles < 30000, source_triangles
corners = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
bounds = {key: [round(fn(p[axis] for p in corners), 4) for axis in range(3)]
          for key, fn in (("min", min), ("max", max))}

# FBX retains material IDs but never embeds absolute paths or third-party
# images. Linked CC0 maps remain project-relative in the editable .blend.
linked = [(node, node.image) for mat in (TIMBER, PATINA)
          for node in mat.node_tree.nodes if node.type == "TEX_IMAGE"]
for node, _ in linked:
    node.image = None
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
export_obj = bpy.context.object
export_obj.name = NAME
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(island_margin=.006)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, global_scale=1, axis_forward="-Y", axis_up="Z",
                         add_leaf_bones=False, bake_anim=False, path_mode="STRIP")
bpy.data.objects.remove(export_obj, do_unlink=True)
for node, image in linked:
    node.image = image


# Minimal neutral studio leaves the lacquer, patina and windings legible.
stage = bpy.data.collections.new("Review_Stage_NotForFBX")
scene.collection.children.link(stage)
floor_mat = material("M_Review_Charcoal", (.013,.018,.023), 0, .78)
bpy.ops.mesh.primitive_plane_add(size=2.5, location=(0,0,-.265))
floor = bpy.context.object
floor.name = "Review_Floor"
floor.data.materials.append(floor_mat)
for col in tuple(floor.users_collection):
    col.objects.unlink(floor)
stage.objects.link(floor)


def light(name, location, color, energy, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.rotation_euler = (Vector((.05,0,-.01))-obj.location).to_track_quat("-Z", "Y").to_euler()
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    stage.objects.link(obj)


light("WarmLanternKey", (-.25,-.8,.90), (1,.75,.49), 160, 1.2)
light("ColdArcRim", (.57,.65,.70), (.38,.78,1.0), 220, .8)
light("ReceiverSoftbox", (-.15,.47,.39), (1,.96,.88), 75, .7)
bpy.ops.object.camera_add(location=(.70,-1.11,.38))
camera = bpy.context.object
camera.name = "ArcCarbine_Review_Camera"
camera.rotation_euler = (Vector((.06,0,-.022))-camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 1.08
scene.camera = camera
scene.world.color = (.035,.043,.051)
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.65
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == "FILE":
        image.filepath = bpy.path.relpath(image.filepath, start=str(OUT))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_arc_carbine.py",
    "generator_blender": bpy.app.version_string,
    "source_blend": BLEND.name,
    "fbx": FBX.name,
    "preview": PREVIEW.name,
    "unreal_asset": f"/Game/Generated/Meshes/{NAME}.{NAME}",
    "source_parts": len(parts),
    "source_triangles": source_triangles,
    "bounds_m": bounds,
    "local_forward": "+X toward muzzle; +Z up",
    "mesh_origin_m": [0,0,0],
    "grip_web_m": [-.11,0,-.05],
    "grip_palm_center_m": [-.11,0,-.12],
    "muzzle_center_m": [.526,0,.026],
    "license": "Original project-owned geometry and shaders; linked timber/patina texture maps CC0 Poly Haven. No purchased assets.",
    "texture_dependency": "../../Environment/PolyHaven/manifest.json; project-relative links in .blend, no FBX texture paths",
    "palette_asset_ids": ["wood_planks_dirt", "rusty_metal_02"],
    "palette_manifest_sha256": hashlib.sha256((PALETTE / "manifest.json").read_bytes()).hexdigest(),
    "units": "Blender meters; Unreal FBX import converts to centimeters",
    "scope": "Visual standard weapon ID 1 only. No gameplay/stat changes. Blender review only; UE import, material fidelity and runtime frame rate unverified.",
    "blend_sha256": hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
}
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("ARC_CARBINE_READY",len(parts),source_triangles,bounds,PREVIEW)
