"""Author an integrated, non-periodic 64 m Estate stone/gravel road study.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_integrated_roji.py

The eight central terrain tiles in each rendering tier are rebuilt from the
unchanged Estate source grid. Its former repeated stone-scan faces become an
irregularly exposed, darker mineral/silt bed. Original individual stone faces
are shallow-set into that same terrain export. There is no paved overlay on
the old photographed road, no new collision, and no effect on the combat map.
This source-only candidate does not replace the release terrain assets.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuIntegratedRoji"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "Content/SourceArt/Environment/NyaagyuTerrain"
ROCK = ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01"
SOIL = ROOT / "Content/SourceArt/Environment/PolyHaven/brown_mud_leaves_01"
GRAVEL = OUT / "GravelGround01"
SOURCE_BLEND = OUT / "Nyaagyu_IntegratedRoji_Source.blend"
PREVIEW = OUT / "Nyaagyu_IntegratedRoji_EyeHeight_Blender.png"
OVERHEAD = OUT / "Nyaagyu_IntegratedRoji_Overhead_Blender.png"
MANIFEST = OUT / "manifest.json"
RNG = random.Random(0x72_6f_6a_69_2026)
TIERS = {"hi": (128, 104), "mac": (32, 26)}
SLOT_NAMES = ["M_Roji_EstateSoil", "M_Roji_MineralBed",
              "M_Roji_IndividualStone", "M_Roji_EdgeMineral"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


base_manifest = json.loads((BASE / "manifest.json").read_text())
rock_manifest = json.loads((ROCK / "manifest.json").read_text())
soil_catalog = json.loads((SOIL.parent / "manifest.json").read_text())
soil_manifest = next(a for a in soil_catalog["assets"] if a["asset_id"] == "brown_mud_leaves_01")
gravel_manifest = json.loads((GRAVEL / "manifest.json").read_text())
assert base_manifest["source_blend_sha256"] == sha(BASE / base_manifest["source_blend"])
assert rock_manifest["license"] == soil_manifest["license"] == gravel_manifest["license"] == "CC0-1.0"
assert rock_manifest["source_dimensions_mm"] == [1500, 1500]


def scan_files(info: dict, folder: Path) -> dict:
    result = {}
    for item in info["files"]:
        if item["channel"] not in ("Diffuse", "nor_dx", "arm"):
            continue
        path = folder / item["file"]
        assert path.is_file() and sha(path) == item["sha256"]
        result[item["channel"]] = path
    assert set(result) == {"Diffuse", "nor_dx", "arm"}
    return result


rock_maps = scan_files(rock_manifest, ROCK)
soil_maps = scan_files(soil_manifest, SOIL.parent)
gravel_maps = scan_files(gravel_manifest, GRAVEL)


def pbr_material(name: str, files: dict, tint: tuple[float, float, float],
                 roughness_factor: float = 1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*tint, 1.0)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.name = "Pinned_CC0_Albedo"
    albedo.image = bpy.data.images.load(str(files["Diffuse"]), check_existing=True)
    packed = nodes.new("ShaderNodeTexImage")
    packed.name = "Pinned_CC0_ARM"
    packed.image = bpy.data.images.load(str(files["arm"]), check_existing=True)
    packed.image.colorspace_settings.name = "Non-Color"
    normal = nodes.new("ShaderNodeTexImage")
    normal.name = "Pinned_CC0_NormalDX"
    normal.image = bpy.data.images.load(str(files["nor_dx"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"
    for tex in (albedo, packed, normal):
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
    color = nodes.new("ShaderNodeVertexColor")
    color.layer_name = "RojiPatina"
    modulate = nodes.new("ShaderNodeMixRGB")
    modulate.blend_type = "MULTIPLY"
    modulate.inputs[0].default_value = 1.0
    links.new(albedo.outputs["Color"], modulate.inputs[1])
    links.new(color.outputs["Color"], modulate.inputs[2])
    tintnode = nodes.new("ShaderNodeMixRGB")
    tintnode.blend_type = "MULTIPLY"
    tintnode.inputs[0].default_value = 1.0
    tintnode.inputs[2].default_value = (*tint, 1.0)
    links.new(modulate.outputs["Color"], tintnode.inputs[1])
    links.new(tintnode.outputs["Color"], bsdf.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(packed.outputs["Color"], split.inputs["Color"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "MULTIPLY"
    rough.inputs[1].default_value = roughness_factor
    links.new(split.outputs["Green"], rough.inputs[0])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    # Poly Haven's DirectX map must invert green for Blender's normal node.
    nsplit = nodes.new("ShaderNodeSeparateColor")
    links.new(normal.outputs["Color"], nsplit.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    links.new(nsplit.outputs["Green"], invert.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(nsplit.outputs["Red"], rgb.inputs["Red"])
    links.new(invert.outputs[0], rgb.inputs["Green"])
    links.new(nsplit.outputs["Blue"], rgb.inputs["Blue"])
    nm = nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = .80
    links.new(rgb.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
hi_collection = bpy.data.collections.new("Roji_HI_EditableTerrainAndStone")
mac_collection = bpy.data.collections.new("Roji_MAC_EditableTerrainAndStone")
scene.collection.children.link(hi_collection)
scene.collection.children.link(mac_collection)
mac_collection.hide_render = True
materials = [
    pbr_material(SLOT_NAMES[0], soil_maps, (.93, .96, .94)),
    pbr_material(SLOT_NAMES[1], gravel_maps, (.69, .71, .70), 1.0),
    pbr_material(SLOT_NAMES[2], rock_maps, (.95, .94, .91)),
    pbr_material(SLOT_NAMES[3], rock_maps, (.66, .68, .67)),
]
export_materials = [bpy.data.materials.new(name + "_FBX") for name in SLOT_NAMES]
for mat in export_materials:
    mat.diffuse_color = (.42, .42, .42, 1)

source_names = [f"SourceTerrain_{tier}_X{x}_Y{y}"
                for tier in TIERS for y in (1, 2) for x in range(4)]
with bpy.data.libraries.load(str(BASE / base_manifest["source_blend"]), link=False) as (src, dst):
    assert set(source_names).issubset(set(src.objects))
    dst.objects = source_names
source_tiles = {obj.name: obj for obj in dst.objects}
assert len(source_tiles) == 16


def smoothstep(a: float, b: float, value: float) -> float:
    t = max(0.0, min(1.0, (value - a) / (b - a)))
    return t * t * (3 - 2 * t)


def noise(x: float, y: float, cell: float) -> float:
    fx, fy = x / cell, y / cell
    ix, iy = math.floor(fx), math.floor(fy)
    tx, ty = smoothstep(0, 1, fx - ix), smoothstep(0, 1, fy - iy)
    def corner(a, b):
        h = ((a * 73856093) ^ (b * 19349663)) & 0xffffffff
        h ^= h >> 13
        return (h * 1274126177 & 0xffffffff) / 0xffffffff
    return ((1 - tx) * (1 - ty) * corner(ix, iy)
            + tx * (1 - ty) * corner(ix + 1, iy)
            + (1 - tx) * ty * corner(ix, iy + 1)
            + tx * ty * corner(ix + 1, iy + 1))


def clip_halfplane(poly, nx, ny, limit):
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da, db = a[0] * nx + a[1] * ny - limit, b[0] * nx + b[1] * ny - limit
        if da <= 0:
            out.append(a)
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def area(poly):
    return .5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                    - poly[(i + 1) % len(poly)][0] * poly[i][1]
                    for i in range(len(poly)))


# A global blue-noise-like point field, rather than a row lattice or repeating
# module, sets unique cell silhouettes across the 64 m route. Near the edge
# the density falls away into the original irregular soil/road transition.
points = []
point_bins = defaultdict(list)
min_spacing, target = .37, 1060
attempts = 0
while len(points) < target and attempts < 90000:
    attempts += 1
    x, y = RNG.uniform(-31.90, 31.90), RNG.uniform(-2.62, 2.62)
    if RNG.random() < .48 * smoothstep(2.13, 2.62, abs(y)):
        continue
    bx, by = math.floor(x / min_spacing), math.floor(y / min_spacing)
    if any((x - qx) ** 2 + (y - qy) ** 2 < min_spacing ** 2
           for ax in range(bx - 1, bx + 2) for ay in range(by - 1, by + 2)
           for qx, qy in point_bins[(ax, ay)]):
        continue
    points.append((x, y))
    point_bins[(bx, by)].append((x, y))
assert len(points) >= 950, (len(points), attempts)


def tile_index(x, y):
    ix = max(0, min(3, int(math.floor((x + 32) / 16))))
    iy = 1 if y < 0 else 2
    return ix, iy


def terrain_height(tier: str, x: float, y: float) -> float:
    ix, iy = tile_index(x, y)
    cx, cy = -24 + 16 * ix, -19.5 + 13 * iy
    nx, ny = TIERS[tier]
    gx = max(0.0, min(nx - 1e-8, (x - cx + 8) * nx / 16))
    gy = max(0.0, min(ny - 1e-8, (y - cy + 6.5) * ny / 13))
    vx, vy = int(gx), int(gy)
    tx, ty = gx - vx, gy - vy
    mesh = source_tiles[f"SourceTerrain_{tier}_X{ix}_Y{iy}"].data
    def z(a, b):
        return mesh.vertices[b * (nx + 1) + a].co.z
    return ((1 - tx) * (1 - ty) * z(vx, vy)
            + tx * (1 - ty) * z(vx + 1, vy)
            + (1 - tx) * ty * z(vx, vy + 1)
            + tx * ty * z(vx + 1, vy + 1))


cells = []
for idx, (sx, sy) in enumerate(points):
    # Sparse laid stones in broad bands of compacted gravel are much closer to
    # this Estate route than a wall-to-wall European-looking cobble polygon.
    # The low-frequency decision makes gravel-only breathing room at entrance
    # scale while each stone identity remains globally non-repeating.
    cluster = noise(sx + 12.7, sy - 5.4, 5.6)
    keep = .36 + .35 * cluster - .13 * smoothstep(1.8, 2.6, abs(sy))
    if RNG.random() > keep:
        continue
    cell = [(sx - 1.05, sy - 1.05), (sx + 1.05, sy - 1.05),
            (sx + 1.05, sy + 1.05), (sx - 1.05, sy + 1.05)]
    bx, by = math.floor(sx / min_spacing), math.floor(sy / min_spacing)
    neighbors = [q for ax in range(bx - 6, bx + 7)
                 for ay in range(by - 6, by + 7)
                 for q in point_bins[(ax, ay)] if q != (sx, sy)]
    for tx, ty in neighbors:
        nx, ny = tx - sx, ty - sy
        if nx * nx + ny * ny > 1.8 ** 2:
            continue
        boundary = .5 * (tx * tx + ty * ty - sx * sx - sy * sy)
        cell = clip_halfplane(cell, nx, ny, boundary)
        if len(cell) < 3:
            break
    if len(cell) < 3 or abs(area(cell)) < .035:
        continue
    cx = sum(p[0] for p in cell) / len(cell)
    cy = sum(p[1] for p in cell) / len(cell)
    gap = RNG.uniform(.010, .024) + .009 * smoothstep(2.0, 2.65, abs(cy))
    stone_footprint = RNG.uniform(.63, .83)
    inset = []
    for x, y in cell:
        distance = max(.05, math.hypot(x - cx, y - cy))
        factor = stone_footprint * max(.78, 1 - gap * RNG.uniform(.85, 1.20) / distance)
        inset.append((cx + (x - cx) * factor, cy + (y - cy) * factor))
    # One convexity-preserving corner cut, still inside each Voronoi allotment,
    # turns exact tessellation corners into weathered, blunt stone silhouettes.
    rounded = []
    for j, a in enumerate(inset):
        b = inset[(j + 1) % len(inset)]
        rounded.extend(((.83 * a[0] + .17 * b[0], .83 * a[1] + .17 * b[1]),
                        (.17 * a[0] + .83 * b[0], .17 * a[1] + .83 * b[1])))
    inset = rounded
    outline = []
    for j, a in enumerate(inset):
        b = inset[(j + 1) % len(inset)]
        subdivisions = max(1, round(math.dist(a, b) / .16))
        for k in range(subdivisions):
            t = k / subdivisions
            px, py = a[0] * (1 - t) + b[0] * t, a[1] * (1 - t) + b[1] * t
            chip = RNG.uniform(.0004, .004) + (.004 if k == 0 else 0)
            radial = max(.08, math.hypot(px - cx, py - cy))
            outline.append((cx + (px - cx) * (1 - chip / radial),
                            cy + (py - cy) * (1 - chip / radial)))
    if len(outline) < 4:
        continue
    cells.append({"id": idx, "seed": (sx, sy), "centroid": (cx, cy),
                  "outline": outline, "area": abs(area(outline)),
                  "gap": gap, "tone": RNG.uniform(.82, 1.09),
                  "warm": RNG.uniform(-.025, .025),
                  "offset": (RNG.random(), RNG.random()),
                  "crown": RNG.uniform(.003, .007)})
assert 300 <= len(cells) <= 800, len(cells)


def stone_faces(cell, tier, center):
    """Return one shallow embedded stone with explicit crown, bevel, and side."""
    cx, cy = cell["centroid"]
    outline = cell["outline"]
    if tier == "mac":
        outline = outline[::2] if len(outline) >= 10 else outline
    count = len(outline)
    if area(outline) < 0:
        outline = list(reversed(outline))
    bed_center = terrain_height(tier, cx, cy)
    top_offset = .006 + .005 * (1 - smoothstep(2.2, 2.65, abs(cy)))
    crown = cell["crown"] if tier == "hi" else cell["crown"] * .65
    verts = [(cx - center[0], cy - center[1], bed_center + top_offset + crown)]
    rings = (.70, .95, 1.0) if tier == "hi" else (.88, 1.0)
    for r in rings:
        for px, py in outline:
            x, y = cx + r * (px - cx), cy + r * (py - cy)
            z = terrain_height(tier, x, y) + top_offset + crown * (1 - r * r)
            if r == 1.0:
                z -= .004
            verts.append((x - center[0], y - center[1], z))
    for px, py in outline:
        bed_z = terrain_height(tier, px, py)
        verts.append((px - center[0], py - center[1], bed_z - .0005))
    faces, slots = [], []
    ring_starts = [1 + n * count for n in range(len(rings))]
    for j in range(count):
        faces.append((0, ring_starts[0] + j, ring_starts[0] + (j + 1) % count))
        slots.append(2)
    for ring in range(len(rings) - 1):
        a, b = ring_starts[ring], ring_starts[ring + 1]
        for j in range(count):
            n = (j + 1) % count
            faces.append((a + j, b + j, b + n, a + n))
            slots.append(2 if ring < len(rings) - 2 else 3)
    a, b = ring_starts[-1], 1 + len(rings) * count
    for j in range(count):
        n = (j + 1) % count
        faces.append((a + j, b + j, b + n, a + n))
        slots.append(3)
    u0, v0 = cell["offset"]
    uv, color = [], []
    tone, warm = cell["tone"], cell["warm"]
    for lx, ly, z in verts:
        x, y = lx + center[0], ly + center[1]
        # Let the sampler wrap beyond 1.0. Taking modulo independently at
        # vertices would interpolate across a false 0/1 seam within a stone.
        uv.append((x / 1.5 + u0, y / 1.5 + v0))
        tiny = .94 + .11 * noise(x + 19, y - 4, .18)
        damp = .09 * (noise(x + 8, y - 11, 1.75) - .5)
        shade = tone * tiny * (1 - damp)
        color.append((shade * (1 + warm), shade, shade * (1 - warm), .0))
    return verts, faces, slots, uv, color


def original_tile_data(obj, tier, ix, iy):
    mesh = obj.data
    verts = [tuple(v.co) for v in mesh.vertices]
    faces = [tuple(p.vertices) for p in mesh.polygons]
    slots = [0 if p.material_index == 0 else 1 for p in mesh.polygons]
    face_uvs = []
    face_colors = []
    old_uv = mesh.uv_layers.active
    old_color = mesh.color_attributes.get("EstateMacroTint")
    assert old_uv and old_color
    center = (-24 + 16 * ix, -19.5 + 13 * iy)
    for p in mesh.polygons:
        one_uv = []
        one_color = []
        for li in p.loop_indices:
            vi = mesh.loops[li].vertex_index
            x, y = mesh.vertices[vi].co.x + center[0], mesh.vertices[vi].co.y + center[1]
            # Soil stays at 1.3 m; the new photographed gravel bed is 3.0 m.
            scale = 1.30 if p.material_index == 0 else 3.0
            one_uv.append((x / scale, y / scale))
            c = tuple(old_color.data[li].color)
            one_color.append(c if p.material_index == 0 else (
                .87 + .09 * noise(x + 9, y - 3, 1.6),
                .86 + .08 * noise(x - 1, y + 8, 1.3),
                .84 + .09 * noise(x + 4, y + 1, 2.1),
                .22 + .28 * noise(x, y, 2.0)))
        face_uvs.append(one_uv)
        face_colors.append(one_color)
    return verts, faces, slots, face_uvs, face_colors


def make_tile(tier, ix, iy):
    source = source_tiles[f"SourceTerrain_{tier}_X{ix}_Y{iy}"]
    center = (-24 + 16 * ix, -19.5 + 13 * iy)
    verts, faces, slots, face_uvs, face_colors = original_tile_data(source, tier, ix, iy)
    assigned = [cell for cell in cells if tile_index(*cell["centroid"]) == (ix, iy)]
    count_triangles = 0
    for cell in assigned:
        sv, sf, sm, su, sc = stone_faces(cell, tier, center)
        start = len(verts)
        verts.extend(sv)
        faces.extend(tuple(start + i for i in face) for face in sf)
        slots.extend(sm)
        face_uvs.extend([[su[i] for i in f] for f in sf])
        face_colors.extend([[sc[i] for i in f] for f in sf])
        count_triangles += sum(len(face) - 2 for face in sf)
    name = f"SM_NyaagyuIntegratedRoji_{tier.upper()}_X{ix}_Y{iy}"
    mesh = bpy.data.meshes.new(name + "_EditableMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    (hi_collection if tier == "hi" else mac_collection).objects.link(obj)
    obj.location = (*center, 0)
    obj["source_tile"] = source.name
    obj["stone_count"] = len(assigned)
    obj["presentation_only"] = True
    for mat in materials:
        mesh.materials.append(mat)
    layer = mesh.uv_layers.new(name="UV0")
    patina = mesh.color_attributes.new(name="RojiPatina", type="FLOAT_COLOR", domain="CORNER")
    mesh.color_attributes.active_color = patina
    for p, slot, one_uv, one_color in zip(mesh.polygons, slots, face_uvs, face_colors):
        p.material_index = slot
        p.use_smooth = slot == 0  # stones retain hard believable contact edges
        assert len(p.loop_indices) == len(one_uv) == len(one_color)
        for li, this_uv, this_color in zip(p.loop_indices, one_uv, one_color):
            layer.data[li].uv = this_uv
            patina.data[li].color = this_color
    # Export without machine-specific image paths, preserving slot indices.
    for slot, mat in enumerate(export_materials):
        mesh.materials[slot] = mat
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    export = bpy.context.object.copy()
    export.data = obj.data.copy()
    scene.collection.objects.link(export)
    export.name = name + "_FBXTemporary"
    export.location = (0, 0, 0)
    # Same source->UE orientation correction used by the original terrain.
    saved = {}
    exp_uv = export.data.uv_layers.active
    exp_color = export.data.color_attributes["RojiPatina"]
    for p in export.data.polygons:
        for li in p.loop_indices:
            vi = export.data.loops[li].vertex_index
            saved[(p.index, vi)] = (exp_uv.data[li].uv.copy(),
                                     tuple(exp_color.data[li].color))
    for v in export.data.vertices:
        v.co.y = -v.co.y
    for p in export.data.polygons:
        p.flip()
    for p in export.data.polygons:
        for li in p.loop_indices:
            vi = export.data.loops[li].vertex_index
            exp_uv.data[li].uv = saved[(p.index, vi)][0]
            exp_color.data[li].color = saved[(p.index, vi)][1]
    export.data.update()
    bpy.ops.object.select_all(action="DESELECT")
    export.select_set(True)
    bpy.context.view_layer.objects.active = export
    fbx = OUT / (name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True,
                             object_types={"MESH"}, apply_unit_scale=True,
                             global_scale=1.0, axis_forward="-Y", axis_up="Z",
                             bake_anim=False, path_mode="STRIP",
                             colors_type="LINEAR", prioritize_active_color=True)
    bpy.data.objects.remove(export, do_unlink=True)
    for slot, mat in enumerate(materials):
        mesh.materials[slot] = mat
    return {"name": name, "fbx": fbx.name, "fbx_sha256": sha(fbx),
            "tier": tier, "index": [ix, iy],
            "placement_center_cm": [round(center[0] * 100), round(center[1] * 100), 0],
            "base_quads": TIERS[tier][0] * TIERS[tier][1],
            "stone_count": len(assigned), "stone_triangles": count_triangles,
            "total_triangles": sum(len(p.vertices) - 2 for p in mesh.polygons),
            "local_bounds_m": [
                [round(min(v.co[i] for v in mesh.vertices), 4) for i in range(3)],
                [round(max(v.co[i] for v in mesh.vertices), 4) for i in range(3)]],
            "slots": SLOT_NAMES}


records = [make_tile(tier, x, y) for tier in TIERS for y in (1, 2) for x in range(4)]
assert sum(r["stone_count"] for r in records if r["tier"] == "hi") == len(cells)
assert sum(r["stone_count"] for r in records if r["tier"] == "mac") == len(cells)

# Render an actual 1.55 m eye-height assessment down the approach and one
# oblique overhead frame. They are source-art reviews, not UE game captures.
world = bpy.data.worlds.new("Roji_OvercastReview")
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.69, .72, .76, 1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .65
scene.world = world
light_data = bpy.data.lights.new("Overcast_soft_sun", "SUN")
light_data.energy = 1.5
light_data.angle = .16
light = bpy.data.objects.new("Overcast_soft_sun", light_data)
scene.collection.objects.link(light)
light.rotation_euler = (.50, -.40, -.31)
cam_data = bpy.data.cameras.new("Roji_ReviewCamera")
cam = bpy.data.objects.new("Roji_ReviewCamera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
cam_data.type = "PERSP"
cam_data.lens = 31
cam.location = (-25, -.6, 1.55)
cam.rotation_euler = (Vector((-12, -.2, .01)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)
cam_data.type = "ORTHO"
cam_data.ortho_scale = 24
cam.location = (-16, -13, 22)
cam.rotation_euler = (Vector((-16, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(OVERHEAD)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source == "FILE":
        image.filepath = bpy.path.relpath(image.filepath, start=str(OUT))
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_BLEND))

manifest = {
    "schema_version": 1,
    "generator": "scripts/art/create_nyaagyu_integrated_roji.py",
    "generator_sha256": sha(ROOT / "scripts/art/create_nyaagyu_integrated_roji.py"),
    "source_blend": SOURCE_BLEND.name, "source_blend_sha256": sha(SOURCE_BLEND),
    "eye_height_review": PREVIEW.name, "eye_height_sha256": sha(PREVIEW),
    "overhead_review": OVERHEAD.name, "overhead_sha256": sha(OVERHEAD),
    "base_terrain_manifest": str((BASE / "manifest.json").relative_to(ROOT)),
    "base_terrain_manifest_sha256": sha(BASE / "manifest.json"),
    "stone_scan_manifest": str((ROCK / "manifest.json").relative_to(ROOT)),
    "stone_scan_manifest_sha256": sha(ROCK / "manifest.json"),
    "soil_scan_manifest": str((SOIL.parent / "manifest.json").relative_to(ROOT)),
    "soil_scan_manifest_sha256": sha(SOIL.parent / "manifest.json"),
    "gravel_scan_manifest": str((GRAVEL / "manifest.json").relative_to(ROOT)),
    "gravel_scan_manifest_sha256": sha(GRAVEL / "manifest.json"),
    "license": "Original geometry and patina; reused Poly Haven Rock 01, Brown Mud Leaves 01, and Gravel Ground 01 PBR scans are CC0-1.0",
    "license_url": "https://polyhaven.com/license",
    "road_extent_m": [64, 5.24], "nominal_stone_count": len(cells),
    "road_stone_area_m2": round(sum(c["area"] for c in cells), 4),
    "tile_records": records,
    "collision": "Unchanged flat Estate box and deterministic kernel; candidate FBXs are visual only",
    "old_repeating_scan_removed": True,
    "integration": "Replaces the repeated road material inside each existing central terrain tile with mineral/silt bed; stone shells belong to the same exported tile; peripheral tiles remain unchanged",
    "limitations": "Source-only art candidate. It has not yet passed exact UE 5.8.2 import, an isolated packaged camera A/B, Windows Nanite, Mac fallback performance, or independent historical review. Procedural masonry and two scan sources alone do not meet AAA photoreal art quality.",
}
MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
print("NYAAGYU_INTEGRATED_ROJI_CREATED", len(cells), len(records),
      sum(r["total_triangles"] for r in records if r["tier"] == "hi"))
