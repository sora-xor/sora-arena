"""Model the Nyaagyu dojo's asymmetric rainwater court in metric units.

Run texture generation first, then:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_water_court.py

The exported one-piece mesh is visual-only. The source Blender file retains
individual stones, bamboo culms, leaves, timber joinery, and tiles for editing.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuWaterCourt"
TEX = OUT / "Textures"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_WaterCourt_4m"
SUBSET_NAME = "SM_Nyaagyu_BambooRill_4m"
BLEND = OUT / "Nyaagyu_WaterCourt_Source.blend"
FBX = OUT / f"{NAME}.fbx"
SUBSET_FBX = OUT / f"{SUBSET_NAME}.fbx"
REVIEW = OUT / "Nyaagyu_WaterCourt_EyeHeight_Blender.png"
DETAIL = OUT / "Nyaagyu_WaterCourt_Detail_Blender.png"
SUBSET_REVIEW = OUT / "Nyaagyu_BambooRill_EyeHeight_Blender.png"
MANIFEST = OUT / "manifest.json"
RNG = random.Random(0xB4A6B00)

PH = ROOT / "Content/SourceArt/Environment/PolyHaven"
PH_RECORD = json.loads((PH / "manifest.json").read_text())
ROCK_DIR = ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01"
ROCK_RECORD = json.loads((ROCK_DIR / "manifest.json").read_text())
FOREST_DIR = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing/ScanForestLeaves02"
FOREST_RECORD = json.loads((FOREST_DIR / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan(name: str, manifest: dict, folder: Path) -> dict:
    assert manifest["asset_id"] == name and manifest["license"] == "CC0-1.0"
    files = {}
    for item in manifest["files"]:
        channel = {"Diffuse": "Albedo", "nor_dx": "NormalDX", "arm": "ORM"}[item["channel"]]
        path = folder / item["file"]
        assert sha(path) == item["sha256"], path
        files[channel] = {"path": str(path.relative_to(ROOT)), "sha256": item["sha256"],
                          "url": item["url"]}
    assert set(files) == {"Albedo", "NormalDX", "ORM"}
    return {"asset_id": name, "source_url": manifest["asset_url"],
            "license": manifest["license"], "license_url": manifest["license_url"],
            "authors": manifest["authors"], "files": files}


WOOD_RECORD = next(a for a in PH_RECORD["assets"] if a["asset_id"] == "wood_planks_dirt")
TILE_RECORD = json.loads((PH / "GreyRoofTiles/manifest.json").read_text())
DEPS = {
    "AgedCedar": scan("wood_planks_dirt", WOOD_RECORD, PH),
    "CarvedStone": scan("rock_01", ROCK_RECORD, ROCK_DIR),
    "RoofCeramic": scan("grey_roof_tiles", TILE_RECORD, PH / "GreyRoofTiles"),
    "Moss": scan("forest_leaves_02", FOREST_RECORD, FOREST_DIR),
    "CompactedSilt": scan("brown_mud_leaves_01",
                          next(a for a in PH_RECORD["assets"] if a["asset_id"] == "brown_mud_leaves_01"), PH),
}
for role, prefix in (("BambooCulm", "T_WaterCourt_BambooCulm"),
                     ("BambooLeaf", "T_WaterCourt_BambooLeaf")):
    files = {}
    for channel in ("Albedo", "NormalDX", "ORM"):
        path = TEX / f"{prefix}_{channel}.png"
        assert path.exists(), path
        files[channel] = {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
    DEPS[role] = {"asset_id": f"original_{role.lower()}", "license": "original-project-art",
                  "generator": "scripts/art/create_nyaagyu_water_court_textures.py", "files": files}

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
source = bpy.data.collections.new("WaterCourt_Editable")
scene.collection.children.link(source)
studio = bpy.data.collections.new("Review_Only")
scene.collection.children.link(studio)


def pbr(name: str, role: str, tint=(1, 1, 1), rough_bias=0, two_sided=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = not two_sided
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    files = DEPS[role]["files"]
    image = nodes.new("ShaderNodeTexImage")
    image.name = "Pinned_or_Original_Albedo"
    image.image = bpy.data.images.load(str(ROOT / files["Albedo"]["path"]), check_existing=True)
    image.image.filepath = bpy.path.relpath(str(ROOT / files["Albedo"]["path"]), start=str(OUT))
    mul = nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1
    mul.inputs[2].default_value = (*tint, 1)
    links.new(image.outputs["Color"], mul.inputs[1])
    links.new(mul.outputs["Color"], bsdf.inputs["Base Color"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.name = "Pinned_or_Original_ORM"
    arm.image = bpy.data.images.load(str(ROOT / files["ORM"]["path"]), check_existing=True)
    arm.image.colorspace_settings.name = "Non-Color"
    arm.image.filepath = bpy.path.relpath(str(ROOT / files["ORM"]["path"]), start=str(OUT))
    sep = nodes.new("ShaderNodeSeparateColor")
    sep.mode = "RGB"
    links.new(arm.outputs["Color"], sep.inputs["Color"])
    add = nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.inputs[1].default_value = rough_bias
    links.new(sep.outputs["Green"], add.inputs[0])
    links.new(add.outputs[0], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.name = "Pinned_or_Original_NormalDX"
    normal.image = bpy.data.images.load(str(ROOT / files["NormalDX"]["path"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.image.filepath = bpy.path.relpath(str(ROOT / files["NormalDX"]["path"]), start=str(OUT))
    channel = nodes.new("ShaderNodeSeparateColor")
    channel.mode = "RGB"
    links.new(normal.outputs["Color"], channel.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(channel.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    combine.mode = "RGB"
    links.new(channel.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(channel.outputs["Blue"], combine.inputs["Blue"])
    nm = nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = .66
    links.new(combine.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


MATS = {
    "M_Court_Cedar": pbr("M_Court_Cedar", "AgedCedar", (.66, .57, .46), .07),
    "M_Court_CedarDark": pbr("M_Court_CedarDark", "AgedCedar", (.40, .38, .36), .12),
    "M_Court_Stone": pbr("M_Court_Stone", "CarvedStone", (.73, .75, .73), .02),
    "M_Court_StoneWet": pbr("M_Court_StoneWet", "CarvedStone", (.43, .48, .47), -.2),
    "M_Court_Mud": pbr("M_Court_Mud", "CompactedSilt", (.67, .67, .64), -.09),
    "M_Court_Roof": pbr("M_Court_Roof", "RoofCeramic", (.74, .76, .79), .06),
    "M_Court_Moss": pbr("M_Court_Moss", "Moss", (.39, .63, .40), .08, True),
    "M_Court_Bamboo": pbr("M_Court_Bamboo", "BambooCulm", (1, 1, 1), 0, True),
    "M_Court_BambooNode": pbr("M_Court_BambooNode", "BambooCulm", (.58, .56, .45), .08, True),
    "M_Court_BambooLeaf": pbr("M_Court_BambooLeaf", "BambooLeaf", (1, 1, 1), 0, True),
}
water = bpy.data.materials.new("M_Court_ShallowRainwater")
water.use_nodes = True
water_bsdf = water.node_tree.nodes.get("Principled BSDF")
water_bsdf.inputs["Base Color"].default_value = (.035, .067, .065, 1)
water_bsdf.inputs["Roughness"].default_value = .18
water_bsdf.inputs["Metallic"].default_value = 0
MATS["M_Court_ShallowRainwater"] = water


def mesh_obj(name, vertices, faces, mat, uv_kind="box", uv_scale=1.0,
             uv_override=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    source.objects.link(obj)
    mesh.materials.append(MATS[mat])
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        axis = max(range(3), key=lambda a: abs(poly.normal[a]))
        for li in poly.loop_indices:
            idx = mesh.loops[li].vertex_index
            p = mesh.vertices[idx].co
            if uv_override:
                u, v = uv_override[idx]
            elif uv_kind == "cyl":
                u, v = p.x, p.z
            elif axis == 0:
                u, v = p.y, p.z
            elif axis == 1:
                u, v = p.x, p.z
            else:
                u, v = p.x, p.y
            uv.data[li].uv = (u * uv_scale, v * uv_scale)
    obj["collision_policy"] = "visual_only"
    return obj


def box(name, center, size, mat, bevel=.008, uv_scale=.65):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    source.objects.link(obj)
    obj.data.materials.append(MATS[mat])
    uv = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    for face in obj.data.polygons:
        axis = max(range(3), key=lambda a: abs(face.normal[a]))
        for li in face.loop_indices:
            p = obj.data.vertices[obj.data.loops[li].vertex_index].co + obj.location
            u, v = ((p.y, p.z) if axis == 0 else ((p.x, p.z) if axis == 1 else (p.x, p.y)))
            uv.data[li].uv = (u * uv_scale, v * uv_scale)
    if bevel:
        mod = obj.modifiers.new("Worn_Edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        weighted = obj.modifiers.new("Weighted_Corners", "WEIGHTED_NORMAL")
        bpy.ops.object.modifier_apply(modifier=weighted.name)
    obj["collision_policy"] = "visual_only"
    return obj


def beam(name, a, b, width, depth, mat, bevel=.008):
    mid = (Vector(a) + Vector(b)) / 2
    direction = Vector(b) - Vector(a)
    obj = box(name, mid, (width, depth, direction.length), mat, bevel)
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return obj


def stone(name, center, radius, mat, squish=(1, 1, 1), seed=0):
    local = random.Random(0x5710 + seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=center)
    obj = bpy.context.object
    obj.name = name
    for coll in list(obj.users_collection):
        coll.objects.unlink(obj)
    source.objects.link(obj)
    for v in obj.data.vertices:
        jitter = 1 + local.uniform(-.115, .115)
        v.co.x *= squish[0] * jitter
        v.co.y *= squish[1] * jitter
        v.co.z *= squish[2] * jitter
    obj.data.materials.append(MATS[mat])
    uv = obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            p = obj.data.vertices[obj.data.loops[li].vertex_index].co
            u = math.atan2(p.y, p.x) / (2 * math.pi) + .5
            v = .5 + math.atan2(p.z, math.hypot(p.x, p.y)) / math.pi
            uv.data[li].uv = (u * 1.4, v * 1.4)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj["collision_policy"] = "visual_only"
    return obj


def roof_tile(name, x, y, z, width, run, slope):
    # Open-bottom tapered, shallow clay arc. Every row has a unique chipped lip
    # so the roof reads as fitted ceramic rather than a scan on a flat plane.
    sides = 7
    verts, faces = [], []
    for end in (0, 1, 2, 3):
        yy = y + end * run
        zz = z + end * run * slope
        if end >= 2:
            yy = y + (end - 2) * run
            zz = z + (end - 2) * run * slope - .019
        for k in range(sides):
            u = k / (sides - 1)
            xx = x + (u - .5) * width * (1 - .035 * end)
            crown = .035 * (1 - (2 * u - 1) ** 2)
            chipped = RNG.uniform(-.007, .007) if end == 0 else 0
            verts.append((xx, yy + chipped, zz + crown))
    for k in range(sides - 1):
        faces.append((k, k + 1, sides + k + 1, sides + k))
        faces.append((2 * sides + k, 3 * sides + k,
                      3 * sides + k + 1, 2 * sides + k + 1))
    for row in (0, 1):
        top = row * sides
        bottom = (row + 2) * sides
        for k in range(sides - 1):
            faces.append((top + k, bottom + k, bottom + k + 1, top + k + 1))
    return mesh_obj(name, verts, faces, "M_Court_Roof", uv_scale=1.15)


def hollow_culm(name, x, y, height, radius, lean, phase, variant):
    sides = 12
    count = max(5, round(height / .28))
    verts, faces, uv = [], [], []
    for i in range(count + 1):
        z = height * i / count
        taper = 1 - .4 * (i / count) ** 1.45
        px = x + lean[0] * (i / count) ** 1.38 + .013 * math.sin(z * 2.8 + phase)
        py = y + lean[1] * (i / count) ** 1.38
        for k in range(sides + 1):
            angle = math.tau * k / sides + phase
            r = radius * taper * (1 + .025 * math.sin(z * 15 + phase))
            verts.append((px + math.cos(angle) * r, py + math.sin(angle) * r, z))
            uv.append((k / sides + .003 * variant, z * .65 + phase / math.tau))
    for i in range(count):
        for k in range(sides):
            a = i * (sides + 1) + k
            b = a + sides + 1
            faces.append((a, a + 1, b + 1, b))
    # Hollow open end and visibly darker internal wall.
    top = len(verts)
    px = x + lean[0] + .013 * math.sin(height * 2.8 + phase)
    py = y + lean[1]
    r = radius * .6 * .73
    for k in range(sides + 1):
        angle = math.tau * k / sides + phase
        verts.append((px + math.cos(angle) * r, py + math.sin(angle) * r, height - .018))
        uv.append((k / sides, height * .65))
    last = count * (sides + 1)
    for k in range(sides):
        faces.append((last + k, last + k + 1, top + k + 1, top + k))
    obj = mesh_obj(name, verts, faces, "M_Court_Bamboo", uv_override=uv)
    # Slightly swollen nodes, spaced like living bamboo rather than evenly
    # machine-ribbed conduit.
    for j in range(1, count):
        z = height * j / count
        px = x + lean[0] * (j / count) ** 1.38 + .013 * math.sin(z * 2.8 + phase)
        py = y + lean[1] * (j / count) ** 1.38
        ring = []
        for dz in (-.016, .0, .018):
            ring.extend((px + math.cos(math.tau * k / sides + phase) * radius * (1.03 if dz else 1.13),
                         py + math.sin(math.tau * k / sides + phase) * radius * (1.03 if dz else 1.13),
                         z + dz) for k in range(sides))
        ring_faces = []
        for band in range(2):
            for k in range(sides):
                a = band * sides + k
                b = (band + 1) * sides + k
                ring_faces.append((a, (band * sides + (k + 1) % sides),
                                   ((band + 1) * sides + (k + 1) % sides), b))
        mesh_obj(f"{name}_Node_{j:02}", ring, ring_faces, "M_Court_BambooNode", uv_scale=4)
    return obj


def leaf_blade(name, stem, direction, length, width, palette):
    vector = Vector(direction).normalized()
    right = vector.cross(Vector((.18, .38, 1))).normalized()
    if right.length < .01:
        right = Vector((1, 0, 0))
    right = (right + Vector((0, 0, RNG.uniform(-.75, .75)))).normalized()
    verts, uv, faces = [], [], []
    for i in range(7):
        t = i / 6
        center = Vector(stem) + vector * length * t
        center.z -= .085 * (t ** 2) * (length / .28)
        half = width * (math.sin(math.pi * t) ** .72) / 2
        curl = math.sin(t * math.pi) * .013
        for side in (-1, 1):
            p = center + right * half * side
            p.z += curl * (-1 if side == -1 else 1)
            verts.append(tuple(p))
            uv.append(((palette + (.08 if side == -1 else .92)) / 4, t))
        if i:
            a = (i - 1) * 2
            faces.append((a, a + 1, a + 3, a + 2))
    return mesh_obj(name, verts, faces, "M_Court_BambooLeaf", uv_override=uv)


def moss_patch(name, x, y, sx, sy):
    sides = 14
    verts = [(x, y, .025)]
    for ring, height in ((.55, .033), (1.0, -.004)):
        for k in range(sides):
            a = k * math.tau / sides
            j = RNG.uniform(.86, 1.13)
            verts.append((x + math.cos(a) * sx * ring * j,
                          y + math.sin(a) * sy * ring * j, height))
    faces = [(0, 1 + k, 1 + (k + 1) % sides) for k in range(sides)]
    for k in range(sides):
        nk = (k + 1) % sides
        faces.append((1 + k, 1 + nk, 1 + sides + nk, 1 + sides + k))
    return mesh_obj(name, verts, faces, "M_Court_Moss", uv_scale=2.0)


# Original stone-lined runoff channel. The discontinuous joints and variable
# stone height are deliberate; a strip of identical cubes reads as blockout.
mud_vertices = [(0, .24, .002)]
for ring, z in ((.53, .004), (1.0, -.014)):
    for k in range(64):
        a = math.tau * k / 64
        ripple = 1 + .06 * math.sin(5 * a + .5) + .035 * math.sin(13 * a)
        mud_vertices.append((2.19 * ring * math.cos(a) * ripple,
                             .24 + .58 * ring * math.sin(a) * ripple, z))
mud_faces = [(0, 1 + k, 1 + (k + 1) % 64) for k in range(64)]
for k in range(64):
    nk = (k + 1) % 64
    mud_faces.append((1 + k, 1 + nk, 65 + nk, 65 + k))
mesh_obj("Rill_Irregular_Compacted_Silt", mud_vertices, mud_faces,
         "M_Court_Mud", uv_scale=.77)
water_vertices = []
for i in range(25):
    x = -1.95 + i * 3.9 / 24
    y = .03 * math.sin(i * .81)
    width = .105 + .036 * math.sin(i * .39 + .5)
    water_vertices.extend(((x, y - width, .016), (x, y + width, .016)))
water_faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(24)]
mesh_obj("Narrow_Rainwater_Flow", water_vertices, water_faces,
         "M_Court_ShallowRainwater", uv_scale=.8)
for side in (-1, 1):
    x = -2.08
    i = 0
    while x < 1.98:
        length = RNG.uniform(.20, .43)
        center_x = x + length / 2
        y = side * (.21 + RNG.uniform(-.035, .045))
        stone(f"Rill_Edge_{side:+d}_{i:02}", (center_x, y, .068),
              .16, "M_Court_Stone" if RNG.random() > .28 else "M_Court_StoneWet",
              (length / .31, RNG.uniform(.72, 1.16), RNG.uniform(.38, .71)), seed=130 + i + 30 * side)
        x += length * RNG.uniform(.88, 1.07)
        i += 1
for i in range(13):
    x = -1.9 + i * .32 + RNG.uniform(-.05, .05)
    stone(f"Rill_Bed_{i:02}", (x, RNG.uniform(-.085, .08), -.01),
          RNG.uniform(.11, .22), "M_Court_StoneWet", (1.35, 1.1, .24), seed=700 + i)

# Hand-hewn catch basin: dished annular geometry with no arbitrary smooth
# cylinder wall. Interior side reads as chipped and water-darkened stone.
sides = 44
basin_center = (-.62, 1.23)
rings = [(.0, .105), (.24, .095), (.34, .145), (.42, .34),
         (.51, .37), (.56, .31), (.52, .12), (.38, .018), (.0, .018)]
verts = []
for ri, (rad, z) in enumerate(rings):
    for k in range(sides):
        a = math.tau * k / sides
        asymmetric = 1 + .036 * math.sin(a * 5 + .7) + .025 * math.sin(a * 11 + ri)
        verts.append((basin_center[0] + rad * math.cos(a) * asymmetric,
                      basin_center[1] + rad * math.sin(a) * asymmetric,
                      z + (RNG.random() - .5) * (.008 if ri < 3 else .018)))
faces = []
for ri in range(len(rings) - 1):
    for k in range(sides):
        nk = (k + 1) % sides
        faces.append((ri * sides + k, ri * sides + nk,
                      (ri + 1) * sides + nk, (ri + 1) * sides + k))
mesh_obj("Carved_Catch_Basin", verts, faces, "M_Court_Stone", uv_scale=1.4)
stone("Basin_Interior_Dark_Wet", (basin_center[0], basin_center[1], .085), .28,
      "M_Court_StoneWet", (1, 1, .14), seed=928)

# Weathered timber rain eave and open maintenance rack. No solid backboard:
# the open void keeps the building behind visible in a midground shot.
for i, x in enumerate((-1.82, 1.63)):
    beam(f"Canopy_Post_{i}", (x, 1.63, .06), (x + .016 * i, 1.63, 2.48),
         .135, .13, "M_Court_CedarDark", .012)
    box(f"Post_Stone_Foot_{i}", (x, 1.63, .11), (.31, .29, .22),
        "M_Court_Stone", .03, .7)
beam("Canopy_Front_Beam", (-2.01, .74, 2.30), (1.91, .74, 2.30),
     .10, .105, "M_Court_CedarDark", .008)
beam("Canopy_Back_Beam", (-2.01, 1.68, 2.54), (1.91, 1.68, 2.54),
     .12, .13, "M_Court_CedarDark", .009)
for i, x in enumerate((-1.74, -.91, -.05, .79, 1.58)):
    beam(f"Rafter_{i}", (x, .56, 2.28), (x, 1.86, 2.61),
         .07, .07, "M_Court_Cedar", .005)
for row in range(4):
    y = .58 + row * .31
    z = 2.39 + (y - .58) * .24
    for col in range(14):
        x = -1.95 + col * .285 + (row % 2) * .03
        roof_tile(f"Roof_Clay_{row:02}_{col:02}", x, y, z,
                  .305 + RNG.uniform(-.014, .014), .34, .24)
box("Eave_Drip_Board", (-.04, .53, 2.27), (4.07, .06, .105),
    "M_Court_CedarDark", .008)
for i, x in enumerate((-1.23, -.43, .37, 1.17)):
    # Drying rails and individually bent pegs supply a human-scale rhythm.
    beam(f"Hanging_Peg_{i}", (x, 1.61, 2.22), (x, 1.40, 2.15),
         .029, .026, "M_Court_Cedar", .004)

# A slender hand-cut bamboo feed pipe and supporting fork behind the basin.
hollow_culm("Basin_Feed_Vertical", -1.22, 1.63, 1.52, .025, (0, 0), .32, 0)
beam("Basin_Feed_Spout", (-1.24, 1.63, 1.51), (-.79, 1.23, 1.36),
     .032, .032, "M_Court_Bamboo", .0)
beam("Basin_Feed_Brace", (-1.47, 1.48, .30), (-1.19, 1.63, .86),
     .033, .033, "M_Court_CedarDark", .0)

# Three offset clumps rather than a uniform screen. The central opening keeps
# the basin legible and prevents a curtain of identical leaf cards.
culm_count = 0
leaf_count = 0
for group, (gx, gy, n, height_range) in enumerate([
    (-1.48, 1.96, 11, (1.42, 3.23)),
    (1.76, 1.99, 14, (1.55, 3.45)),
    (.86, 2.16, 7, (1.12, 2.43)),
]):
    for j in range(n):
        x = gx + RNG.uniform(-.29, .29)
        y = gy + RNG.uniform(-.20, .20)
        height = RNG.uniform(*height_range)
        radius = RNG.uniform(.013, .026)
        lean = (RNG.uniform(-.28, .28), RNG.uniform(-.15, .15))
        phase = RNG.random() * math.tau
        hollow_culm(f"Bamboo_{group}_{j:02}", x, y, height, radius,
                    lean, phase, j)
        culm_count += 1
        if j % 4 == 0:
            moss_patch(f"Bamboo_Base_Moss_{group}_{j}", x, y, .18, .13)
        branch_count = RNG.randint(5, 8)
        for bi in range(branch_count):
            t = RNG.uniform(.53, .91)
            root = Vector((x + lean[0] * t ** 1.38,
                           y + lean[1] * t ** 1.38, height * t))
            angle = phase + bi * 2.13 + RNG.uniform(-.4, .4)
            horizontal = Vector((math.cos(angle), math.sin(angle), .26))
            tip = root + horizontal * RNG.uniform(.30, .62)
            beam(f"Bamboo_Twig_{group}_{j}_{bi}", root, tip,
                 .008, .008, "M_Court_BambooNode", .0)
            for li in range(RNG.randint(8, 14)):
                q = (li + .5) / 14
                attach = root.lerp(tip, q)
                sign = 1 if li % 2 == 0 else -1
                direction = (horizontal * .55 + Vector((-.36 * sign * math.sin(angle),
                                                         .36 * sign * math.cos(angle),
                                                         RNG.uniform(-.48, .18))))
                leaf_blade(f"Bamboo_Leaf_{group}_{j}_{bi}_{li}", attach,
                           direction, RNG.uniform(.21, .34), RNG.uniform(.042, .075),
                           RNG.randrange(4))
                leaf_count += 1

for i in range(21):
    x = RNG.uniform(-1.98, 1.96)
    y = RNG.choice([RNG.uniform(-.39, -.12), RNG.uniform(.33, .65),
                    RNG.uniform(1.93, 2.2)])
    moss_patch(f"Rill_Moss_{i:02}", x, y,
               RNG.uniform(.06, .22), RNG.uniform(.05, .15))

# One compact export copy prevents the source's hundreds of editable details
# from becoming hundreds of Unreal components or unrelated FBX mesh identities.
source_objects = [obj for obj in source.objects if obj.type == "MESH"]
source_parts = len(source_objects)
source_triangles = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
                       for obj in source_objects)
bpy.ops.object.select_all(action="DESELECT")
for obj in source_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = source_objects[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
export = bpy.context.object
export.name = NAME
for coll in list(export.users_collection):
    coll.objects.unlink(export)
scene.collection.objects.link(export)
export["purpose"] = "Nanite-ready source mesh with full conventional Mac fallback"
export["collision_policy"] = "visual_only"
assert export.data.uv_layers.get("UVMap")

bpy.ops.object.select_all(action="DESELECT")
export.select_set(True)
bpy.context.view_layer.objects.active = export
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, add_leaf_bones=False,
                         bake_space_transform=False, path_mode="RELATIVE")
export.hide_render = True
export.hide_set(True)

subset_parts = [obj for obj in source_objects
                if obj.name.startswith(("Bamboo_", "Rill_", "Narrow_Rainwater_Flow"))]
subset_names = {obj.name for obj in subset_parts}
subset_triangles = sum(sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
                       for obj in subset_parts)
assert len(subset_parts) > 2000 and subset_triangles > 30000
bpy.ops.object.select_all(action="DESELECT")
for obj in subset_parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = subset_parts[0]
bpy.ops.object.duplicate()
subset_copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = subset_copies[0]
bpy.ops.object.join()
subset = bpy.context.object
subset.name = SUBSET_NAME
for coll in list(subset.users_collection):
    coll.objects.unlink(subset)
scene.collection.objects.link(subset)
subset["collision_policy"] = "visual_only"
subset["admission_scope"] = "off-road foliage and sub-20cm rill only"
assert subset.data.uv_layers.get("UVMap")
bpy.ops.object.select_all(action="DESELECT")
subset.select_set(True)
bpy.context.view_layer.objects.active = subset
bpy.ops.export_scene.fbx(filepath=str(SUBSET_FBX), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         add_leaf_bones=False, bake_space_transform=False,
                         path_mode="RELATIVE")
subset.hide_render = True
subset.hide_set(True)

# Fixed review camera at human eye height, angled from the Estate road. The
# simple background is only a scale/lighting reference; it is not game art.
def review_studio():
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.003))
    plane = bpy.context.object
    plane.name = "REVIEW_ONLY_Ground"
    for coll in list(plane.users_collection):
        coll.objects.unlink(plane)
    studio.objects.link(plane)
    plane.data.materials.append(MATS["M_Court_Mud"])
    for coord in plane.data.uv_layers.active.data:
        coord.uv *= 90
    world = bpy.data.worlds.new("Review_Only_OvercastWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (.37, .45, .54, 1)
    bg.inputs["Strength"].default_value = .62
    scene.world = world
    sun_data = bpy.data.lights.new("Review_Only_BroadCloud", "AREA")
    sun = bpy.data.objects.new("Review_Only_BroadCloud", sun_data)
    studio.objects.link(sun)
    sun.location = (-5, -3.5, 7.5)
    sun_data.energy = 1000
    sun_data.shape = "DISK"
    sun_data.size = 5
    sun.rotation_euler = (Vector((0, .9, 1.0)) - sun.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Estate_Road_Eye_Height")
    camera = bpy.data.objects.new("Estate_Road_Eye_Height", camera_data)
    studio.objects.link(camera)
    scene.camera = camera
    camera.location = (-6.4, -5.9, 1.65)
    target = Vector((0, .94, 1.42))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "PERSP"
    camera_data.lens = 36
    return camera


camera = review_studio()
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.render.filepath = str(REVIEW)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.render.render(write_still=True)
camera.location = (-3.0, -2.8, 1.55)
target = Vector((-.62, 1.1, .9))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 46
scene.render.filepath = str(DETAIL)
bpy.ops.render.render(write_still=True)
camera.location = (-6.4, -5.9, 1.65)
target = Vector((0, .94, 1.42))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 36
# The subset review uses identical light and camera; the excluded canopy and
# basin are not carried into gameplay's visual-only foliage study.
for obj in source_objects:
    if obj.name not in subset_names:
        obj.hide_render = True
scene.render.filepath = str(SUBSET_REVIEW)
bpy.ops.render.render(write_still=True)
for obj in source_objects:
    obj.hide_render = False
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

coords = [export.matrix_world @ v.co for v in export.data.vertices]
bounds = {axis: [round(min(v[i] for v in coords), 4), round(max(v[i] for v in coords), 4)]
          for i, axis in enumerate("xyz")}
material_names = [m.name for m in export.data.materials]
subset_coords = [subset.matrix_world @ v.co for v in subset.data.vertices]
subset_bounds = {axis: [round(min(v[i] for v in subset_coords), 4),
                        round(max(v[i] for v in subset_coords), 4)]
                 for i, axis in enumerate("xyz")}
manifest = {
    "schema_version": 1,
    "name": NAME,
    "identity": "original project-authored visual-only Edo-inspired rainwater court",
    "units": "m",
    "source_blend": str(BLEND.relative_to(ROOT)),
    "export_fbx": str(FBX.relative_to(ROOT)),
    "generator": "scripts/art/create_nyaagyu_water_court.py",
    "texture_generator": "scripts/art/create_nyaagyu_water_court_textures.py",
    "render_eye_height": str(REVIEW.relative_to(ROOT)),
    "render_detail": str(DETAIL.relative_to(ROOT)),
    "subset_fbx": str(SUBSET_FBX.relative_to(ROOT)),
    "subset_render_eye_height": str(SUBSET_REVIEW.relative_to(ROOT)),
    "subset_name": SUBSET_NAME,
    "subset_bounds_m": subset_bounds,
    "subset_source_parts": len(subset_parts),
    "subset_triangles": subset_triangles,
    "subset_material_slots": [m.name for m in subset.data.materials],
    "bounds_m": bounds,
    "source_mesh_parts": source_parts,
    "source_triangles": source_triangles,
    "export_triangles": sum(len(p.vertices) - 2 for p in export.data.polygons),
    "culms": culm_count,
    "leaves": leaf_count,
    "material_slots": material_names,
    "scan_dependencies": DEPS,
    "placement_policy": "visual-only; no new gameplay collision; off central route; fail visual gate if solid canopy creates false cover",
    "historical_scope": "fictional Edo-inspired dojo rainwater court; not a surveyed reconstruction",
    "source_files_sha256": {str(path.relative_to(ROOT)): sha(path)
                            for path in (BLEND, FBX, SUBSET_FBX, REVIEW, DETAIL, SUBSET_REVIEW)},
}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print("WATER_COURT_READY", json.dumps({"bounds_m": bounds,
                                      "source_parts": source_parts,
                                      "tris": source_triangles,
                                      "culms": culm_count,
                                      "leaves": leaf_count}))
