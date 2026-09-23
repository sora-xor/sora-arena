"""Author one editable, non-tiled stone-path hero insert for Nyaagyu Estate.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_hero_path.py

All dimensions are metres. Local +X follows the Estate road, +Y crosses it,
and +Z is up. This is presentation geometry over the existing terrain; the
terrain remains the only authoritative collision. The scan maps are already
licensed and hash-pinned elsewhere in this repository. No paid sources.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuHeroPath"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_HeroStonePath_6m"
BLEND = OUT / "Nyaagyu_HeroStonePath_Source.blend"
FBX = OUT / (NAME + ".fbx")
REVIEW = OUT / "Nyaagyu_HeroStonePath_Blender.png"
OVERHEAD = OUT / "Nyaagyu_HeroStonePath_Overhead_Blender.png"
EYE_REVIEW = OUT / "Nyaagyu_HeroStonePath_EyeHeight_Blender.png"
MANIFEST = OUT / "manifest.json"
ROCK_MANIFEST = ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01/manifest.json"
MUD_MANIFEST = ROOT / "Content/SourceArt/Environment/PolyHaven/manifest.json"
GREY_MANIFEST = ROOT / "Content/SourceArt/Environment/NyaagyuTerrain/manifest.json"
ROCK_DIR = ROCK_MANIFEST.parent
MUD_DIR = MUD_MANIFEST.parent
GREY_DIR = GREY_MANIFEST.parent / "GreyStonePath"
ATLAS_MANIFEST = OUT / "atlas_manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


rock_info = json.loads(ROCK_MANIFEST.read_text())
mud_catalog = json.loads(MUD_MANIFEST.read_text())
grey_catalog = json.loads(GREY_MANIFEST.read_text())
mud_info = next(a for a in mud_catalog["assets"] if a["asset_id"] == "brown_mud_leaves_01")
grey_info = grey_catalog["stone_pathway_scan"]
atlas_info = json.loads(ATLAS_MANIFEST.read_text())
assert rock_info["license"] == mud_info["license"] == grey_info["license"] == "CC0-1.0"
assert atlas_info["source_asset"] == "grey_stone_path" and atlas_info["count"] == 64
assert atlas_info["generator_sha256"] == sha(ROOT / atlas_info["generator"])


def dependency(info, folder: Path, mapping: dict[str, str]) -> dict:
    files = {}
    for entry in info["files"]:
        channel = mapping.get(entry["channel"])
        if not channel:
            continue
        path = folder / entry["file"]
        assert path.is_file() and sha(path) == entry["sha256"], path
        if "bytes" in entry:
            assert path.stat().st_size == entry["bytes"]
        files[channel] = {
            "repo_path": str(path.relative_to(ROOT)),
            "sha256": entry["sha256"],
            "upstream_url": entry.get("url", "https://dl.polyhaven.org/file/ph-assets/Textures/" + path.name),
        }
    assert set(files) == {"Albedo", "NormalDX", "ORM"}
    return {
        "asset_id": info["asset_id"],
        "source_url": info.get("asset_url", info.get("source_url")),
        "license": "CC0-1.0",
        "license_url": "https://polyhaven.com/license",
        "files": files,
    }


DEPENDENCIES = {
    "Mineral": dependency(rock_info, ROCK_DIR, {"Diffuse": "Albedo", "nor_dx": "NormalDX", "arm": "ORM"}),
    "Silt": dependency(mud_info, MUD_DIR, {"Diffuse": "Albedo", "nor_dx": "NormalDX", "arm": "ORM"}),
}
DEPENDENCIES["FaceAtlas"] = {
    "asset_id": "grey_stone_path_derived_stone_interiors",
    "source_url": grey_info["source_url"], "license": "CC0-1.0",
    "license_url": "https://polyhaven.com/license",
    "derivation_manifest": str(ATLAS_MANIFEST.relative_to(ROOT)),
    "files": {
        channel: {"repo_path": str((OUT / atlas_info["outputs"][marker]["file"]).relative_to(ROOT)),
                  "sha256": atlas_info["outputs"][marker]["sha256"],
                  "derived_from": str(GREY_MANIFEST.relative_to(ROOT))}
        for channel, marker in (("Albedo", "Diffuse"), ("NormalDX", "nor_dx"), ("ORM", "arm"))
    },
}
for item in DEPENDENCIES["FaceAtlas"]["files"].values():
    assert sha(ROOT / item["repo_path"]) == item["sha256"]


bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
editable = bpy.data.collections.new("HeroPath_Editable_IndividualStones")
scene.collection.children.link(editable)
studio = bpy.data.collections.new("Blender_Review_Only")
scene.collection.children.link(studio)
rng = random.Random(0x51504A74)


def pbr(name: str, surface: str, tint: tuple[float, float, float], masked: bool = False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*tint, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    paths = DEPENDENCIES[surface]["files"]
    color = nodes.new("ShaderNodeTexImage")
    color.image = bpy.data.images.load(str(ROOT / paths["Albedo"]["repo_path"]), check_existing=True)
    color.name = "Pinned_CC0_Albedo"
    vcol = nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = "StoneMacro"
    mul = nodes.new("ShaderNodeMixRGB")
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    links.new(color.outputs["Color"], mul.inputs[1])
    links.new(vcol.outputs["Color"], mul.inputs[2])
    tintnode = nodes.new("ShaderNodeMixRGB")
    tintnode.blend_type = "MULTIPLY"
    tintnode.inputs[0].default_value = 1.0
    tintnode.inputs[2].default_value = (*tint, 1)
    links.new(mul.outputs["Color"], tintnode.inputs[1])
    links.new(tintnode.outputs["Color"], bsdf.inputs["Base Color"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(ROOT / paths["ORM"]["repo_path"]), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    orm.name = "Pinned_CC0_ORM"
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(orm.outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(ROOT / paths["NormalDX"]["repo_path"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.name = "Pinned_CC0_NormalDX"
    nsep = nodes.new("ShaderNodeSeparateColor")
    links.new(normal.outputs["Color"], nsep.inputs["Color"])
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(nsep.outputs["Green"], inv.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(nsep.outputs["Red"], rgb.inputs["Red"])
    links.new(inv.outputs[0], rgb.inputs["Green"])
    links.new(nsep.outputs["Blue"], rgb.inputs["Blue"])
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = .74 if surface == "Mineral" else .52
    links.new(rgb.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if masked:
        mat.surface_render_method = "DITHERED"
        links.new(vcol.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


MATS = {
    "M_HeroPath_StoneFace": pbr("M_HeroPath_StoneFace", "FaceAtlas", (1.00, 1.02, 1.03)),
    "M_HeroPath_StoneEdge": pbr("M_HeroPath_StoneEdge", "Mineral", (.68, .68, .67)),
    "M_HeroPath_SiltBed": pbr("M_HeroPath_SiltBed", "Silt", (.41, .43, .40), True),
}


def value_noise(x: float, y: float, cell: float) -> float:
    x /= cell
    y /= cell
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    fx = fx * fx * (3 - 2 * fx)
    fy = fy * fy * (3 - 2 * fy)

    def corner(cx, cy):
        h = ((cx * 73856093) ^ (cy * 19349663)) & 0xFFFFFFFF
        h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFF
        return h / 0xFFFFFFFF

    a = corner(ix, iy) * (1 - fx) + corner(ix + 1, iy) * fx
    b = corner(ix, iy + 1) * (1 - fx) + corner(ix + 1, iy + 1) * fx
    return a * (1 - fy) + b * fy


def clip_halfplane(poly: list[tuple[float, float]], nx: float, ny: float, limit: float):
    if not poly:
        return []
    result = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        da = a[0] * nx + a[1] * ny - limit
        db = b[0] * nx + b[1] * ny - limit
        if da <= 0:
            result.append(a)
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            result.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return result


def signed_area(poly):
    return .5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                    - poly[(i + 1) % len(poly)][0] * poly[i][1]
                    for i in range(len(poly)))


def mesh_object(name, verts, faces, face_slots, uvs, rgba, materials):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    editable.objects.link(obj)
    for mat in materials:
        mesh.materials.append(MATS[mat])
    layer = mesh.uv_layers.new(name="UVMap")
    color = mesh.color_attributes.new(name="StoneMacro", type="FLOAT_COLOR", domain="CORNER")
    for face, slot in zip(mesh.polygons, face_slots):
        face.material_index = slot
        face.use_smooth = slot == 0 and "Stone" in name
        for li in face.loop_indices:
            vi = mesh.loops[li].vertex_index
            layer.data[li].uv = uvs[vi]
            color.data[li].color = rgba[vi]
    obj["geometry_source"] = "Original project-owned geometry, not a purchased model"
    return obj


# A random point field produces size variation without the row rhythm of a
# jittered grid. Voronoi cells are then independently fractured, inset, and
# chipped. We retain the seed and cell data for auditability.
seeds = []
attempts = 0
while len(seeds) < 64 and attempts < 20000:
    attempts += 1
    x, y = rng.uniform(-2.72, 2.72), rng.uniform(-1.22, 1.22)
    # The terminal transition intentionally tapers; a perfectly rectangular
    # cutoff would read as a dropped decal on the preexisting terrain.
    tapered = 1.22 - .24 * max(0, (abs(x) - 1.9) / .82)
    if abs(y) > tapered or any((x - sx) ** 2 + (y - sy) ** 2 < .24 ** 2 for sx, sy in seeds):
        continue
    seeds.append((x, y))
assert len(seeds) == 64


stone_stats = []
stone_objects = []
for index, (sx, sy) in enumerate(seeds):
    # Rounded octagon gives the patch a gentle, irregular outline. An empty
    # border remains for the masked silt's 20 cm terrain transition.
    # A superellipse approaches the existing paving gradually at both ends.
    # It is convex, so each half-plane clip remains well-defined.
    cell = []
    for corner in range(32):
        angle = math.tau * corner / 32
        ca, sa = math.cos(angle), math.sin(angle)
        cell.append((2.77 * math.copysign(abs(ca) ** (1/3), ca),
                     1.22 * math.copysign(abs(sa) ** (1/3), sa)))
    for j, (tx, ty) in enumerate(seeds):
        if j == index:
            continue
        nx, ny = tx - sx, ty - sy
        if nx * nx + ny * ny > 1.7 ** 2:
            continue
        limit = .5 * (tx * tx + ty * ty - sx * sx - sy * sy)
        cell = clip_halfplane(cell, nx, ny, limit)
        if len(cell) < 3:
            break
    if len(cell) < 3 or abs(signed_area(cell)) < .018:
        continue
    cx = sum(p[0] for p in cell) / len(cell)
    cy = sum(p[1] for p in cell) / len(cell)
    outer_rho = ((abs(cx) / 2.55) ** 6 + (abs(cy) / 1.12) ** 6) ** (1/6)
    edge_fade = max(0, min(1, (outer_rho - .67) / .37))
    edge_fade = edge_fade * edge_fade * (3 - 2 * edge_fade)
    gap = rng.uniform(.012, .027) + .010 * edge_fade
    inset = []
    for x, y in cell:
        radius = math.hypot(x - cx, y - cy)
        # Almost constant offset; a subtle per-corner deviation breaks exact
        # mirror seams between adjacent Voronoi cells.
        factor = max(.72, 1 - gap * rng.uniform(.84, 1.18) / max(.055, radius))
        inset.append((cx + (x - cx) * factor, cy + (y - cy) * factor))
    fractured = []
    for i, a in enumerate(inset):
        b = inset[(i + 1) % len(inset)]
        length = math.dist(a, b)
        if length < .025:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        # Chipped corners and one unsynchronized edge break; all deviations
        # move toward the cell centroid, never into adjacent stones.
        for t in (.02, .11, .22, .33, .46, .58, .69, .80, .90, .98):
            edge_x, edge_y = a[0] + t * dx, a[1] + t * dy
            chip = rng.uniform(.003, .025) + (.012 if t in (.02, .98) else 0)
            radial = math.hypot(edge_x - cx, edge_y - cy)
            q = max(.0, 1 - chip / max(.05, radial))
            fractured.append((cx + (edge_x - cx) * q, cy + (edge_y - cy) * q))
    if len(fractured) < 10:
        continue
    sides = len(fractured)
    # The perimeter is sunk toward the existing paving. The centre retains a
    # few centimetres of volume for parallax and self-shadowing.
    center_height = .044 + rng.uniform(-.008, .009) - .026 * edge_fade
    thickness = min(rng.uniform(.022, .034), center_height - .008)
    bevel = min(rng.uniform(.006, .013), thickness * .44)
    tone = rng.uniform(.82, 1.12)
    warm = rng.uniform(-.035, .035)
    col = (min(1.25, tone + warm), min(1.25, tone), min(1.25, tone - warm), 1)
    verts = [(cx, cy, center_height + .003)]
    # Top interior ring and chipped bevel. Geometry relief remains a few mm:
    # broader scan-derived detail is carried by the normal map, not spikes.
    for ring in (.48, .78, .94):
        for px, py in fractured:
            x, y = cx + (px - cx) * ring, cy + (py - cy) * ring
            low = .005 * (value_noise(x + index * .07, y - index * .11, .22) - .5)
            low += .004 * (value_noise(x, y, .075) - .5)
            z = center_height + low - (.0035 if ring == 1 else 0)
            verts.append((x, y, z))
    for px, py in fractured:
        verts.append((px, py, center_height - bevel))
    for px, py in fractured:
        verts.append((px, py, center_height - thickness))
    faces, material_faces = [], []
    for j in range(sides):
        faces.append((0, 1 + j, 1 + (j + 1) % sides)); material_faces.append(0)
    for r in range(2):
        a, b = 1 + r * sides, 1 + (r + 1) * sides
        for j in range(sides):
            n = (j + 1) % sides
            faces.append((a + j, b + j, b + n, a + n)); material_faces.append(0)
    a, b, c = 1 + 2 * sides, 1 + 3 * sides, 1 + 4 * sides
    for j in range(sides):
        n = (j + 1) % sides
        faces.append((a + j, b + j, b + n, a + n)); material_faces.append(1)
        faces.append((b + j, c + j, c + n, b + n)); material_faces.append(1)
    atlas_col, atlas_row = index % 8, index // 8
    tile_x = 128 + atlas_col * 480
    tile_y = 128 + atlas_row * 480
    min_x, max_x = min(p[0] for p in fractured), max(p[0] for p in fractured)
    min_y, max_y = min(p[1] for p in fractured), max(p[1] for p in fractured)
    uv = []
    colors = []
    for x, y, z in verts:
        u = (x - min_x) / max(.01, max_x - min_x)
        v = (y - min_y) / max(.01, max_y - min_y)
        uv.append(((tile_x + 8 + 464 * u) / 4096,
                   1 - (tile_y + 8 + 464 * v) / 4096))
        micro = .945 + .11 * value_noise(x + 8, y - 3, .19)
        edge = .78 if z < center_height - .005 else 1.0
        colors.append((col[0] * micro * edge, col[1] * micro * edge,
                       col[2] * micro * edge, 1.0))
    obj = mesh_object(f"Stone_{index:03}", verts, faces, material_faces, uv, colors,
                      ["M_HeroPath_StoneFace", "M_HeroPath_StoneEdge"])
    obj["seed_xy_m"] = [sx, sy]
    obj["nominal_gap_m"] = gap
    obj["stone_top_m"] = center_height
    stone_objects.append(obj)
    stone_stats.append({"part": obj.name, "seed_xy_m": [round(sx, 4), round(sy, 4)],
                        "top_m": round(center_height, 4), "gap_m": round(gap, 4),
                        "area_m2": round(abs(signed_area(fractured)), 4)})
assert 60 <= len(stone_objects) <= 64


# A deliberately shallow, damp silt lens closes the photographed terrain seams
# beneath the new mesh. Its RGB and alpha are vertex-baked and continue into
# UE; the outer ~22 cm fades away instead of forming a rectangular decal edge.
nx, ny = 66, 34
bed_verts = []
bed_uv = []
bed_colors = []
for iy in range(ny + 1):
    y = -1.44 + iy * 2.88 / ny
    for ix in range(nx + 1):
        x = -2.99 + ix * 5.98 / nx
        z = .002 + .0035 * (value_noise(x, y, .34) - .5)
        bed_verts.append((x, y, z))
        bed_uv.append((x / 1.30 + .15, y / 1.30 + .22))
        # Fade the under-bed around the *stone silhouette*, never the grid
        # bounds. This prevents a continuous brown 6 m rectangle.
        rho = ((abs(x) / 2.77) ** 6 + (abs(y) / 1.22) ** 6) ** (1/6)
        alpha = max(0, min(1, (1.055 - rho) / .19))
        alpha = alpha * alpha * (3 - 2 * alpha)
        macro = .78 + .15 * value_noise(x + 12, y - 8, .55)
        bed_colors.append((macro * .89, macro * .92, macro * .90, alpha))
bed_faces = []
for iy in range(ny):
    for ix in range(nx):
        a = iy * (nx + 1) + ix
        b = a + 1
        c = a + nx + 1
        bed_faces.extend(((a, b, c + 1), (a, c + 1, c)))
bed = mesh_object("SiltBed_Feathered", bed_verts, bed_faces, [0] * len(bed_faces),
                  bed_uv, bed_colors, ["M_HeroPath_SiltBed"])
bed["collision"] = "none"


source_meshes = [bed] + stone_objects
triangles = sum(len(face.vertices) - 2 for obj in source_meshes for face in obj.data.polygons)
points = [obj.matrix_world @ v.co for obj in source_meshes for v in obj.data.vertices]
bounds = {"min": [round(min(p[i] for p in points), 4) for i in range(3)],
          "max": [round(max(p[i] for p in points), 4) for i in range(3)]}
assert -3.01 < bounds["min"][0] < -2.95 and 2.95 < bounds["max"][0] < 3.01
assert -1.46 < bounds["min"][1] < -1.40 and 1.40 < bounds["max"][1] < 1.46
assert -.002 <= bounds["min"][2] < .005 and .038 < bounds["max"][2] < .065


# FBX is a single draw-ready mesh; the .blend retains every editable stone.
bpy.ops.object.select_all(action="DESELECT")
for obj in source_meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = bed
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
bpy.ops.object.join()
export = bpy.context.object
export.name = NAME
export_collection = bpy.data.collections.new("Unreal_Export_Only")
scene.collection.children.link(export_collection)
for collection in tuple(export.users_collection):
    collection.objects.unlink(export)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, add_leaf_bones=False,
                         apply_unit_scale=True, axis_forward="-Y", axis_up="Z",
                         path_mode="STRIP")
export.hide_render = True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")


# Review on the existing *paving* scan, so the patch-to-terrain transition is
# visible and the same 1.8 m repeat problem is not hidden by a neutral plane.
bpy.ops.mesh.primitive_plane_add(size=2)
ground = bpy.context.object
ground.name = "Review_existing_GreyStonePath_terrain_only"
for collection in tuple(ground.users_collection):
    collection.objects.unlink(ground)
studio.objects.link(ground)
ground.dimensions = (9, 6, 0)
ground.location.z = -.008
grey_path = {}
for row in grey_info["files"]:
    grey_path[row["channel"]] = str(GREY_DIR / Path(row["file"]).name)
ground_mat = bpy.data.materials.new("Review_Existing_GreyStonePath_CC0")
ground_mat.use_nodes = True
gnodes = ground_mat.node_tree.nodes
glinks = ground_mat.node_tree.links
gbsdf = gnodes.get("Principled BSDF")
gtex = gnodes.new("ShaderNodeTexImage")
gtex.image = bpy.data.images.load(grey_path["Diffuse"])
glinks.new(gtex.outputs["Color"], gbsdf.inputs["Base Color"])
gbsdf.inputs["Roughness"].default_value = .79
ground.data.materials.append(ground_mat)
for loop in ground.data.uv_layers.active.data:
    loop.uv[0] *= 5.0
    loop.uv[1] *= 3.33


def area(name, location, energy, size, color):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    studio.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, .03)) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("Overcast_key", (0.7, -3.0, 5.5), 850, 3.2, (1, .94, .87))
area("Cool_sky_fill", (-3.2, 1.6, 3.2), 410, 3.5, (.70, .83, 1))
world = bpy.data.worlds.new("Nyaagyu_Overcast_HeroPath_Review")
scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.16, .19, .22, 1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .38
cam_data = bpy.data.cameras.new("Review_Camera")
camera = bpy.data.objects.new("Review_Camera", cam_data)
studio.objects.link(camera)
scene.camera = camera
cam_data.type = "ORTHO"
cam_data.ortho_scale = 6.9
camera.location = (3.0, -5.3, 5.1)
camera.rotation_euler = (Vector((0, 0, .01)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.render.filepath = str(REVIEW)
bpy.ops.render.render(write_still=True)
cam_data.ortho_scale = 7.2
camera.location = (0, 0, 9.0)
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(OVERHEAD)
bpy.ops.render.render(write_still=True)
cam_data.type = "PERSP"
cam_data.lens = 30
camera.location = (-5.1, -2.1, 1.67)
camera.rotation_euler = (Vector((.4, .1, .018)) - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(EYE_REVIEW)
bpy.ops.render.render(write_still=True)


# Do not embed copyrighted or machine-specific asset paths in FBX. The Blend
# packs the pinned CC0 images so the editable source remains reviewable.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
slots = sorted(mat.name for mat in export.data.materials)
record = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_nyaagyu_hero_path.py",
    "generator_sha256": sha(ROOT / "scripts/art/create_nyaagyu_hero_path.py"),
    "source_blend": BLEND.name, "blend_sha256": sha(BLEND),
    "fbx": FBX.name, "fbx_sha256": sha(FBX),
    "review": REVIEW.name, "review_sha256": sha(REVIEW),
    "overhead_review": OVERHEAD.name, "overhead_review_sha256": sha(OVERHEAD),
    "eye_height_review": EYE_REVIEW.name, "eye_height_review_sha256": sha(EYE_REVIEW),
    "source_parts": len(source_meshes), "individual_stones": len(stone_objects),
    "source_triangles": triangles, "bounds_m": bounds,
    "stone_area_m2": round(sum(x["area_m2"] for x in stone_stats), 4),
    "nominal_road_length_m": 6.0,
    "orientation": "Local X follows Estate road; local Y crosses road; +Z up",
    "mean_stone_top_m": round(sum(x["top_m"] for x in stone_stats) / len(stone_stats), 4),
    "gap_range_m": [min(x["gap_m"] for x in stone_stats), max(x["gap_m"] for x in stone_stats)],
    "collision": "Presentation only; gameplay collision and deterministic combat stay on Estate terrain",
    "nanite_windows": True,
    "mac_conventional_fallback": {
        "source_fbx": FBX.name, "fallback_percent_triangles": 1.0,
        "fallback_target": "PercentTriangles", "generate_fallback": "Enabled",
        "render_config": "Config/Mac/MacEngine.ini",
    },
    "material_slots": slots,
    "material_sources": {"M_HeroPath_StoneFace": "FaceAtlas", "M_HeroPath_StoneEdge": "Mineral",
                         "M_HeroPath_SiltBed": "Silt"},
    "dependencies": DEPENDENCIES,
    "atlas_manifest_sha256": sha(ATLAS_MANIFEST),
    "review_terrain_scan": {"asset_id": grey_info["asset_id"], "source_url": grey_info["source_url"],
                            "license": "CC0-1.0"},
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "license": "Original project-owned geometry and existing pinned Poly Haven CC0-1.0 PBR scans",
    "limitations": "Blender source review only. The insert has not yet been placed, shader-qualified, or performance-tested in UE 5.8.2. Individual stones are mesh-modeled but not a hand-sculpted AAA photogrammetry reconstruction; collision remains the terrain.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_HERO_PATH_CREATED", len(stone_objects), triangles, bounds, slots)
