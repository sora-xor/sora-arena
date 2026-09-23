"""Create original editable naginata source, one-mesh FBX, and Blender review.

Run: blender -b --factory-startup --python scripts/art/create_monofilament_naginata.py
Local +X points to the blade tip, +Z is up; meters. This is source art for
weapon ID 12, not a combat-stat or NFT-entitlement implementation.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/MonofilamentNaginata"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_MonofilamentNaginata"
BLEND = OUT / "Nyaagyu_MonofilamentNaginata.blend"
FBX = OUT / f"{NAME}.fbx"
PREVIEW = OUT / "Nyaagyu_MonofilamentNaginata_Blender.png"
DETAIL = OUT / "Nyaagyu_MonofilamentNaginata_Detail_Blender.png"
MANIFEST = OUT / "manifest.json"

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
asset = bpy.data.collections.new("Naginata_Editable")
scene.collection.children.link(asset)


def material(name, rgb, metallic, roughness, texture_scale=0, coat=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*rgb, 1)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    if texture_scale:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = texture_scale
        noise.inputs["Detail"].default_value = 3
        variation = nodes.new("ShaderNodeMapRange")
        variation.inputs["To Min"].default_value = max(.02, roughness * .82)
        variation.inputs["To Max"].default_value = min(.99, roughness * 1.18)
        links.new(noise.outputs["Fac"], variation.inputs["Value"])
        links.new(variation.outputs["Result"], bsdf.inputs["Roughness"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .13
        bump.inputs["Distance"].default_value = .00008
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


OAK = material("M_Nag_SmokedOak", (.18, .105, .047), .0, .68, 125)
LACQUER = material("M_Nag_IndigoUrushi", (.019, .028, .050), .02, .28, 60, .58)
SILK = material("M_Nag_WovenIndigoIto", (.031, .050, .083), .0, .78, 210)
STEEL = material("M_Nag_ForgedTamahagane", (.32, .39, .43), .96, .30, 90)
HA = material("M_Nag_PolishedHa", (.62, .69, .70), .99, .15, 80)
HAMON = material("M_Nag_Hamon", (.43, .48, .48), .90, .47, 120)
IRON = material("M_Nag_BlackenedIron", (.055, .063, .067), .91, .43, 84)
BRONZE = material("M_Nag_AgedBronze", (.40, .24, .09), .88, .37, 76)
CERAMIC = material("M_Nag_IvoryCeramic", (.59, .56, .46), .08, .31, 75)
COPPER = material("M_Nag_InductionCopper", (.48, .21, .075), .94, .25, 110)
EDGE = material("M_Nag_MonofilamentInlay", (.035, .37, .35), .32, .19, 0, emission=.30)


def keep(obj, name, mat=None):
    obj.name = name
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    asset.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena monofilament naginata source geometry"
    return obj


def bevel(obj, width=.0008):
    mod = obj.modifiers.new("CraftedEdge", "BEVEL")
    mod.width = width
    mod.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def box(name, center, size, mat, edge=.001):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(obj, edge) if edge else obj


def cylinder(name, x, radius, depth, mat, vertices=28):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=(x, 0, 0), rotation=(0, math.pi / 2, 0))
    return bevel(keep(bpy.context.object, name, mat), .00065)


def ring(name, x, radius, thickness, mat):
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=8,
                                     location=(x, 0, 0), rotation=(0, math.pi / 2, 0),
                                     major_radius=radius, minor_radius=thickness)
    return keep(bpy.context.object, name, mat)


def tube(name, points, radius, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, position in zip(spline.points, points):
        point.co = (*position, 1)
    obj = bpy.data.objects.new(name, curve)
    asset.objects.link(obj)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object, name)


def mesh(name, vertices, faces, mats, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    asset.objects.link(obj)
    obj["author"] = "Original SORA Arena monofilament naginata source geometry"
    for mat in mats:
        data.materials.append(mat)
    if indices:
        for face, index in zip(data.polygons, indices):
            face.material_index = index
    return obj


# Approximately 1.76 m of smoked oak, lacquered but with exposed grain near
# the rear hand. The ashigaru-length form remains balanced for a feline grip.
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=.019, radius2=.0155,
                                depth=1.76, location=(.07, 0, 0),
                                rotation=(0, math.pi / 2, 0))
keep(bpy.context.object, "SmokedOakTaperedShaft", OAK)
cylinder("IndigoUrushiShaftSleeve", .12, .0182, 1.28, LACQUER)
cylinder("ExposedRearOakGrip", -.615, .0196, .37, OAK)
cylinder("ButtIronFerrule", -.773, .023, .065, IRON)
ring("ButtBronzeSeam", -.736, .022, .0022, BRONZE)
bpy.ops.mesh.primitive_cone_add(vertices=28, radius1=.021, radius2=.004,
                                depth=.064, location=(-.837, 0, 0),
                                rotation=(0, -math.pi / 2, 0))
keep(bpy.context.object, "BluntGroundButtCap", IRON)

for grip_name, start, end, turns in (("Rear", -.62, -.32, 11),
                                     ("Front", .29, .60, 12)):
    for hand in (-1, 1):
        points = []
        steps = turns * 18
        for index in range(steps + 1):
            t = index / steps
            angle = hand * turns * math.tau * t
            x = start + (end - start) * t
            points.append((x, .0207 * math.cos(angle), .0207 * math.sin(angle)))
        tube(f"{grip_name}IndigoIto_{'Left' if hand < 0 else 'Right'}", points, .00125, SILK)
    for suffix, x in (("Start", start), ("End", end)):
        ring(f"{grip_name}Grip{suffix}BronzeRing", x, .0215, .002, BRONZE)

for index, x in enumerate((-.21, .08, .66, .80)):
    ring(f"ShaftSectionBronzeRing_{index:02d}", x, .0187, .0019, BRONZE)
ring("BladeSocketLowerIron", .891, .022, .005, IRON)
cylinder("KuchiganeBladeSocket", .927, .024, .083, BRONZE)
ring("BladeSocketOuterLip", .960, .026, .003, IRON)

# A small serviceable induction assembly sits on the socket, not across the
# blade. Ivory ceramic insulates the two copper leads from the forged steel.
box("CeramicEdgeCapacitor", (.916, -.025, .010), (.072, .013, .027), CERAMIC, .002)
for side in (-1, 1):
    z = side * .012
    tube(f"CopperEdgeLead_{'Upper' if side > 0 else 'Lower'}",
         [(.875, -.032, z), (.911, -.034, z), (.951, -.027, z), (.986, -.012, z)],
         .0015, COPPER)
    box(f"CeramicLeadTerminal_{side}", (.965, -.022, z), (.014, .006, .007), CERAMIC, .001)


def blade_profile(x):
    t = min(1.0, max(0.0, (x - .952) / .490))
    center = .010 + .021 * t + .092 * t * t
    width = .035 * (1 - .27 * t)
    thickness = .0041 * (1 - .50 * t)
    if t > .78:
        kissaki = max(.025, (1 - t) / .22)
        width *= kissaki ** .65
        thickness *= kissaki ** .55
        center += .004 * (1 - kissaki)
    return center, width, thickness


sections = [(.952 + .490 * i / 66) for i in range(67)]
vertices, faces, indices = [], [], []
for x in sections:
    center, width, thickness = blade_profile(x)
    vertices.extend([
        (x, 0, center - width),
        (x, -thickness * .65, center - width * .20),
        (x, -thickness, center + width * .44),
        (x, -thickness * .60, center + width),
        (x, thickness * .60, center + width),
        (x, thickness, center + width * .44),
        (x, thickness * .65, center - width * .20),
    ])
for section in range(len(sections) - 1):
    for edge in range(7):
        nxt = (edge + 1) % 7
        faces.append((section * 7 + edge, (section + 1) * 7 + edge,
                      (section + 1) * 7 + nxt, section * 7 + nxt))
        indices.append(1 if edge in (0, 6) else 0)
faces.extend([tuple(reversed(range(7))), tuple((len(sections) - 1) * 7 + i for i in range(7))])
indices.extend((0, 1))
mesh("ForgedCurvedNaginataBlade", vertices, faces, [STEEL, HA], indices)

for side in (-1, 1):
    points = []
    for index in range(118):
        x = .985 + .410 * index / 117
        center, width, thickness = blade_profile(x)
        z = center - width * .36 + .0010 * math.sin(index * .43)
        points.append((x, side * (thickness * .86 + .00015), z))
    tube(f"ForgedHamon_{'Near' if side < 0 else 'Far'}", points, .00055, HAMON)

edge_points = []
for index in range(151):
    x = .989 + .423 * index / 150
    center, width, _ = blade_profile(x)
    edge_points.append((x, -.00055, center - width - .0001))
tube("RestrainedMonofilamentEdgeInlay", edge_points, .00048, EDGE)

parts = [obj for obj in asset.objects if obj.type == "MESH"]
source_triangles = sum(len(face.vertices) - 2 for obj in parts for face in obj.data.polygons)
corners = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
bounds = {"min": [round(min(point[axis] for point in corners), 5) for axis in range(3)],
          "max": [round(max(point[axis] for point in corners), 5) for axis in range(3)]}

# Duplicate editable parts only for the single static-mesh export. The joined
# duplicate is removed before saving; the blend keeps all authored parts.
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

stage = bpy.data.collections.new("Review_Stage_NotForFBX")
scene.collection.children.link(stage)
floor_mat = material("M_Review_Charcoal", (.020, .026, .032), .0, .78)
bpy.ops.mesh.primitive_plane_add(size=16, location=(.26, 0, -.073))
floor = bpy.context.object
floor.name = "Review_Floor"
floor.data.materials.append(floor_mat)
for collection in tuple(floor.users_collection):
    collection.objects.unlink(floor)
stage.objects.link(floor)


def light(name, location, color, energy, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.rotation_euler = (Vector((.25, 0, .02)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    stage.objects.link(obj)


light("WarmLanternKey", (-.35, -1.0, 1.2), (1, .71, .45), 165, 1.6)
light("ColdForgedSteelRim", (.92, .70, 1.1), (.42, .75, 1), 165, 1.1)
light("ShaftSoftbox", (-.58, .52, .66), (1, .96, .86), 65, 1.0)
bpy.ops.object.camera_add(location=(.17, -3.2, .82))
camera = bpy.context.object
camera.name = "Naginata_Review_Camera"
camera.rotation_euler = (Vector((.27, 0, .025)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 2.60
scene.camera = camera
scene.world.color = (.013, .018, .025)
scene.render.engine = "CYCLES"
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.65
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)

# A second crop reveals the forged edge, socket and restrained electronics.
full_location = camera.location.copy()
full_rotation = camera.rotation_euler.copy()
full_scale = camera.data.ortho_scale
full_resolution = (scene.render.resolution_x, scene.render.resolution_y)
camera.location = (1.04, -1.15, .45)
camera.rotation_euler = (Vector((1.04, 0, .025)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.ortho_scale = .81
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.filepath = str(DETAIL)
bpy.ops.render.render(write_still=True)
camera.location = full_location
camera.rotation_euler = full_rotation
camera.data.ortho_scale = full_scale
scene.render.resolution_x, scene.render.resolution_y = full_resolution
scene.render.filepath = str(PREVIEW)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = {
    "schema_version": 1,
    "name": NAME,
    "weapon_id": 12,
    "weapon_name_ja": "単分子薙刀",
    "weapon_name_en": "Monofilament Naginata",
    "generator": "scripts/art/create_monofilament_naginata.py",
    "validator": "scripts/art/validate_monofilament_naginata.py",
    "generator_blender": bpy.app.version_string,
    "source_blend": BLEND.name,
    "fbx": FBX.name,
    "preview": PREVIEW.name,
    "detail_preview": DETAIL.name,
    "unreal_asset": f"/Game/ArtReview/Weapons/{NAME}.{NAME}",
    "source_parts": len(parts),
    "source_triangles": source_triangles,
    "bounds_m": bounds,
    "length_m": round(bounds["max"][0] - bounds["min"][0], 5),
    "mesh_origin_m": [0, 0, 0],
    "local_forward": "+X toward blade tip; +Z up",
    "rear_grip_center_m": [-.47, 0, 0],
    "front_grip_center_m": [.445, 0, 0],
    "blade_root_m": [.952, 0, .010],
    "blade_tip_m": [1.442, 0, .127],
    "muzzle_center_m": None,
    "muzzle_note": "Not applicable: melee polearm; local +X points to the blade tip.",
    "material_provenance": "Original project-owned Blender Principled BSDF shaders with authored metallic/roughness and procedural micro-roughness/bump; no external image textures.",
    "fbx_material_limit": "Material slots and UVs only; Blender shader nodes do not automatically become UE PBR materials.",
    "external_images": [],
    "license": "Original project-owned geometry and shader design; no third-party or purchased assets.",
    "units": "Blender meters; Unreal FBX import converts to centimeters",
    "scope": "Visual source-art review of Samurai special weapon ID 12 only. No combat-stat, entitlement, NFT, or bond changes. UE material/scale/appearance approval pending.",
    "blend_sha256": digest(BLEND),
    "fbx_sha256": digest(FBX),
    "preview_sha256": digest(PREVIEW),
    "detail_preview_sha256": digest(DETAIL),
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("NAGINATA_SOURCE_READY", len(parts), source_triangles, bounds, PREVIEW)
