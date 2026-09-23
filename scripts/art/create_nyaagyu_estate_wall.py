"""Create the original, visual-only Nyaagyu Estate perimeter-wall module.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_estate_wall.py
Meters, local Y is the 4 m repeat axis. The pivot matches the center of the
existing 100 x 400 x 540 cm collision section; the C++ wall stays authoritative.
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
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_EstateWall_4m"
BLEND = OUT / "Nyaagyu_EstateWall.blend"
FBX = OUT / f"{NAME}.fbx"
BEFORE = OUT / "Nyaagyu_WallProxy_Before_Blender.png"
AFTER = OUT / "Nyaagyu_EstateWall_Blender.png"
MANIFEST = OUT / "manifest.json"
PH = ROOT / "Content/SourceArt/Environment/PolyHaven"
GLOBAL = json.loads((PH / "manifest.json").read_text())
PLASTER = json.loads((PH / "WhitePlaster02/manifest.json").read_text())
ROOF = json.loads((PH / "GreyRoofTiles/manifest.json").read_text())
ROCK = json.loads((OUT / "ScanRock01/manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_record(asset_id, upstream, base_dir):
    assert upstream["asset_id"] == asset_id and upstream["license"] == "CC0-1.0"
    files = {}
    for entry in upstream["files"]:
        kind = {"Diffuse": "Albedo", "nor_dx": "NormalDX", "arm": "ORM"}[entry["channel"]]
        path = base_dir / entry["file"]
        assert sha(path) == entry["sha256"], (asset_id, kind)
        files[kind] = {
            "repo_path": str(path.relative_to(ROOT)), "sha256": entry["sha256"],
            "upstream_url": entry["url"],
        }
    assert set(files) == {"Albedo", "NormalDX", "ORM"}
    return {"asset_id": asset_id, "source_url": upstream["asset_url"],
            "license": upstream["license"], "license_url": upstream["license_url"],
            "authors": upstream["authors"], "files": files}


by_id = {item["asset_id"]: item for item in GLOBAL["assets"]}
DEPENDENCIES = {
    "Stone": dependency_record("rock_01", ROCK, OUT / "ScanRock01"),
    "Plaster": dependency_record("white_plaster_02", PLASTER, PH / "WhitePlaster02"),
    "Timber": dependency_record("wood_planks_dirt", by_id["wood_planks_dirt"], PH),
    "Kawara": dependency_record("grey_roof_tiles", ROOF, PH / "GreyRoofTiles"),
}

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
parts = bpy.data.collections.new("NyaagyuEstateWall_Editable")
scene.collection.children.link(parts)
studio = bpy.data.collections.new("Blender_Review_Only")
scene.collection.children.link(studio)
rng = random.Random(0x51A7E)


def move(obj, name, collection=parts):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    obj["provenance"] = "Original project-authored Estate wall geometry"
    return obj


def pbr_material(name, source, tint, roughness_bias=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    files = DEPENDENCIES[source]["files"]
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = bpy.data.images.load(str(ROOT / files["Albedo"]["repo_path"]), check_existing=True)
    albedo.name = "Pinned_CC0_Albedo"
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1
    mix.inputs[2].default_value = (*tint, 1)
    links.new(albedo.outputs["Color"], mix.inputs[1])
    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(ROOT / files["ORM"]["repo_path"]), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    orm.name = "Pinned_CC0_ORM"
    split = nodes.new("ShaderNodeSeparateColor")
    split.mode = "RGB"
    links.new(orm.outputs["Color"], split.inputs["Color"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "ADD"
    rough.inputs[1].default_value = roughness_bias
    links.new(split.outputs["Green"], rough.inputs[0])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(ROOT / files["NormalDX"]["repo_path"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.name = "Pinned_CC0_NormalDX"
    separate = nodes.new("ShaderNodeSeparateColor")
    separate.mode = "RGB"
    links.new(normal.outputs["Color"], separate.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(separate.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    combine.mode = "RGB"
    links.new(separate.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(separate.outputs["Blue"], combine.inputs["Blue"])
    bump = nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = .65
    links.new(combine.outputs["Color"], bump.inputs["Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return material


SLOTS = {
    "M_Wall_CharredTimber": {"source": "Timber", "tint": [.16, .16, .16], "roughness_bias": .08},
    "M_Wall_EarthenScar": {"source": "Plaster", "tint": [.58, .38, .24], "roughness_bias": .08},
    "M_Wall_Kawara": {"source": "Kawara", "tint": [.48, .50, .53], "roughness_bias": .05},
    "M_Wall_LimePlaster": {"source": "Plaster", "tint": [.91, .85, .73], "roughness_bias": .02},
    "M_Wall_StoneDark": {"source": "Stone", "tint": [.68, .70, .68], "roughness_bias": .07},
    "M_Wall_StoneFoundation": {"source": "Stone", "tint": [.90, .91, .88], "roughness_bias": .05},
}
MATS = {name: pbr_material(name, **definition) for name, definition in SLOTS.items()}


def box(name, loc, dims, material, bevel=0.0, collection=parts):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = move(bpy.context.object, name, collection)
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("Hand_worn_arris", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.data.materials.clear()
        obj.data.materials.append(material)
    return obj


def mesh_obj(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    parts.objects.link(obj)
    obj.data.materials.append(material)
    obj["provenance"] = "Original project-authored Estate wall geometry"
    return obj


# A recessed body ensures real geometric shadow gaps between individually cut
# stones. Outer faces are stepped and slightly battered, but stay within the
# existing one-meter-wide collision proxy.
box("Stone_core", (0, 0, -2.08), (.64, 3.96, 1.22), MATS["M_Wall_StoneDark"])
for side in (-1, 1):
    for course in range(4):
        z0 = -2.69 + course * .305
        z1 = min(-1.48, z0 + .291)
        count = 7 if course % 2 == 0 else 8
        step = 3.94 / count
        boundaries = [-1.97]
        boundaries += [-1.97+i*step+rng.uniform(-.075,.075) for i in range(1,count)]
        boundaries += [1.97]
        for i in range(count):
            y0 = boundaries[i] + .009
            y1 = boundaries[i+1] - .009
            if y1 - y0 < .10:
                continue
            j = rng.uniform(-.016, .016)
            zlo, zhi = z0 + rng.uniform(0, .007), z1 - rng.uniform(0, .008)
            inner = side * .30
            outer = side * (.452 - course * .021 + j)
            y0top = y0 + rng.uniform(-.017, .017)
            y1top = y1 + rng.uniform(-.017, .017)
            zlot = zlo + rng.uniform(-.007, .007)
            zlor = zlo + rng.uniform(-.007, .007)
            zhit = zhi + rng.uniform(-.009, .009)
            zhir = zhi + rng.uniform(-.009, .009)
            points = [
                (inner, y0 + .008, zlo), (inner, y1 - .008, zlo),
                (inner, y1 - .008, zhi), (inner, y0 + .008, zhi),
                (outer, y0, zlot), (outer, y1, zlor),
                (outer, y1top, zhir), (outer, y0top, zhit),
            ]
            faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                     (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
            obj = mesh_obj(f"Stone_{'front' if side>0 else 'back'}_{course:02}_{i:02}",
                           points, faces,
                           MATS["M_Wall_StoneDark" if (i + 3 * course) % 7 == 0 else "M_Wall_StoneFoundation"])
            bevel = obj.modifiers.new("Weathered_stone_edge", "BEVEL")
            bevel.width = .009 + .003 * ((i + course) % 3)
            bevel.segments = 2
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=bevel.name)

# Plaster is inset within the structural timber. A warm earthen underlayer is
# exposed only in sparse, irregular chips at the low splash zone.
box("Earthen_core", (0, 0, .42), (.64, 3.91, 3.82), MATS["M_Wall_EarthenScar"])
for side in (-1, 1):
    x = side * .335
    for panel in range(2):
        mid_y = -1.0 if panel == 0 else 1.0
        box(f"Plaster_{side}_{panel}", (x, mid_y, .41),
            (.020, 1.82, 3.76), MATS["M_Wall_LimePlaster"], .004)
    # End posts are half-width so adjacent four-meter modules complete them.
    for i, y in enumerate((-1.971, 0, 1.971)):
        box(f"Timber_post_{side}_{i}", (side * .386, y, .41),
            (.148, .056 if i in (0,2) else .112, 3.92),
            MATS["M_Wall_CharredTimber"], .008)
    for label, z in (("sill", -1.49), ("upper", 2.34)):
        box(f"Timber_{label}_{side}", (side * .384, 0, z),
            (.135, 3.98, .105), MATS["M_Wall_CharredTimber"], .006)
    for i in range(12):
        y = rng.uniform(-1.82, 1.82)
        z = rng.uniform(-1.38, -.68)
        width, height = rng.uniform(.035, .11), rng.uniform(.018, .055)
        xscar = side * .348
        vertices = [(xscar, y-width/2, z), (xscar, y-width*.18, z-height*.22),
                    (xscar, y+width*.43, z-height*.1), (xscar, y+width/2, z+height*.47),
                    (xscar, y-width*.28, z+height*.52)]
        mesh_obj(f"Plaster_chip_{side}_{i:02}", vertices, [(0, 1, 2, 3, 4)],
                 MATS["M_Wall_EarthenScar"])

# A low, pitched tile cap is separate geometry. Its overlapping clay units,
# transverse seams, and rounded ridge are visible even from the approach.
box("Tile_subroof", (0, 0, 2.37), (.80, 3.98, .085), MATS["M_Wall_CharredTimber"], .004)
tile_count = 20
for side in (-1, 1):
    for i in range(tile_count):
        y0 = -1.994 + i * .199
        y1 = min(1.994, y0 + .218)
        verts = []
        for y in (y0, y1):
            for k in range(7):
                u = k / 6
                x = side * (.035 + .445*u)
                z = 2.665 - .235*u + .014*math.sin(u*math.pi) + .004*((i%3)-1)
                verts.append((x, y, z))
        for y in (y0, y1):
            for k in range(7):
                u = k / 6
                x = side * (.035 + .445*u)
                z = 2.636 - .235*u + .014*math.sin(u*math.pi) + .004*((i%3)-1)
                verts.append((x, y, z))
        faces = []
        for k in range(6):
            faces.append((k, k+1, 8+k, 7+k))
            faces.append((14+k, 21+k, 22+k, 15+k))
        faces += [(0, 7, 21, 14), (6, 20, 27, 13)]
        for k in range(6):
            faces.append((k, 14+k, 15+k, k+1))
            faces.append((7+k, 8+k, 22+k, 21+k))
        mesh_obj(f"Kawara_{side}_{i:02}", verts, faces, MATS["M_Wall_Kawara"])
for i in range(tile_count):
    y = -1.89 + i*.199
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=.075, depth=.205, location=(0,y,2.615))
    ridge = move(bpy.context.object, f"Ridge_cap_{i:02}")
    ridge.rotation_euler.x = math.pi/2
    ridge.data.materials.append(MATS["M_Wall_Kawara"])
for y, label in ((-1.965, "A"), (1.965, "B")):
    mesh_obj(f"Tile_cap_earthen_gable_{label}",
             [(-.46,y,2.345),(.46,y,2.345),(.46,y,2.42),
              (0,y,2.64),(-.46,y,2.42)],
             [(0,1,2,3,4)], MATS["M_Wall_EarthenScar"])
    box(f"End_fascia_{label}", (0, y, 2.38), (.95, .042, .075),
        MATS["M_Wall_CharredTimber"], .004)

# World-metric box projection makes grain/stone scale consistent between
# separately edited pieces and survives ordinary FBX static-mesh import.
for obj in parts.objects:
    if obj.type != "MESH":
        continue
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
    for poly in obj.data.polygons:
        axis = max(range(3), key=lambda n: abs(poly.normal[n]))
        for li in poly.loop_indices:
            p = obj.matrix_world @ obj.data.vertices[obj.data.loops[li].vertex_index].co
            if axis == 0:
                u, v = p.y, p.z
            elif axis == 1:
                u, v = p.x, p.z
            else:
                u, v = p.y, p.x
            scale = .27 if obj.name.startswith(("Kawara_", "Ridge_cap_")) else 1.15
            uv.data[li].uv = (u*scale, v*scale)

source_meshes = sorted((obj for obj in parts.objects if obj.type == "MESH"), key=lambda obj: obj.name)
triangles = sum(len(poly.vertices)-2 for obj in source_meshes for poly in obj.data.polygons)
points = [obj.matrix_world @ vertex.co for obj in source_meshes for vertex in obj.data.vertices]
bounds = {"min": [round(min(p[i] for p in points), 4) for i in range(3)],
          "max": [round(max(p[i] for p in points), 4) for i in range(3)]}
assert bounds["min"][0] >= -.5 and bounds["max"][0] <= .5
assert bounds["min"][1] >= -2 and bounds["max"][1] <= 2
assert bounds["min"][2] >= -2.7 and bounds["max"][2] <= 2.7

bpy.ops.object.select_all(action="DESELECT")
for obj in source_meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = source_meshes[0]
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
bpy.ops.object.join()
export = bpy.context.object
export.name = NAME
export_collection = bpy.data.collections.new("Unreal_Export_Only")
scene.collection.children.link(export_collection)
for old in tuple(export.users_collection):
    old.objects.unlink(export)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, add_leaf_bones=False,
                         apply_unit_scale=True, axis_forward="-Y", axis_up="Z",
                         path_mode="STRIP")
export.hide_render = True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")

def review_material(name, color):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*color, 1)
    material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .85
    return material


ground = box("Review_ground", (0, 0, -2.735), (200,200,.04),
             review_material("Review_ground_grey", (.21,.23,.22)), 0, studio)
proxy_mat = review_material("Review_original_grey_stone_block", (.2,.23,.23))
proxy = box("Review_original_collision_wall", (0,0,0), (1,4,5.4), proxy_mat, 0, studio)


def area(name, location, energy, size, color):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    studio.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0,0,0))-obj.location).to_track_quat("-Z","Y").to_euler()


area("Warm_overcast_key", (3.5,-4.0,5.4), 1800, 5.0, (1,.91,.77))
area("Cool_sky_rim", (-3.2,2.7,4.0), 1100, 4.0, (.66,.81,1))
world = bpy.data.worlds.new("Estate_wall_cloudlight_review")
scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.13,.15,.18,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .47
camera_data = bpy.data.cameras.new("Review_camera")
camera = bpy.data.objects.new("Review_camera", camera_data)
studio.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 7.8
camera.location = (6.0,-8.4,2.8)
camera.rotation_euler = (Vector((0,0,0))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.engine = "CYCLES"
scene.cycles.samples = 36
scene.render.resolution_x = 1500
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
for obj in source_meshes:
    obj.hide_render = True
scene.render.filepath = str(BEFORE)
bpy.ops.render.render(write_still=True)
for obj in source_meshes:
    obj.hide_render = False
proxy.hide_render = True
scene.render.filepath = str(AFTER)
bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

slots = sorted(material.name for material in export.data.materials)
record = {
    "schema_version": 1, "name": NAME,
    "generator": "scripts/art/create_nyaagyu_estate_wall.py",
    "generator_sha256": sha(ROOT / "scripts/art/create_nyaagyu_estate_wall.py"),
    "source_blend": BLEND.name, "blend_sha256": sha(BLEND),
    "fbx": FBX.name, "fbx_sha256": sha(FBX),
    "review_before": BEFORE.name, "review_before_sha256": sha(BEFORE),
    "review_after": AFTER.name, "review_after_sha256": sha(AFTER),
    "source_parts": len(source_meshes), "source_triangles": triangles,
    "bounds_m": bounds, "module_length_m": 4.0,
    "collision_envelope_m": [1.0,4.0,5.4],
    "collision": "Visual-only module; existing C++ 100 cm perimeter-wall cubes remain gameplay collision",
    "nanite_windows": True,
    "mac_conventional_fallback": {"source_fbx": FBX.name,
                                  "fallback_percent_triangles": 1.0,
                                  "fallback_target": "PercentTriangles",
                                  "generate_fallback": "Enabled",
                                  "render_config": "Config/Mac/MacEngine.ini"},
    "material_slots": slots, "slot_definitions": SLOTS,
    "scan_manifest_sha256": sha(OUT / "ScanRock01/manifest.json"),
    "dependencies": DEPENDENCIES,
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "license": "Original project-owned geometry, existing and locally pinned Poly Haven CC0 scans; no paid assets",
    "reference_notes": [
        {"url": "https://whc.unesco.org/en/list/661",
         "use": "UNESCO describes Himeji's early seventeenth-century stone walls, wood construction, and white-plastered earthen walls; broad material vocabulary only"},
        {"url": "https://www.himejicastle.jp/en/guide/history/",
         "use": "Himeji Castle's primary visitor site documents layered plaster and fired clay roof tiles; no measurements copied"},
        {"url": "https://kyoto.travel/en/travel-inspiration/kyoto-craftmanship-small-production-crafts/",
         "use": "Kyoto's tourism office describes Kyoto kawara ceramics; Estate tile cap is fictional"},
    ],
    "limitations": "Fictional Nyaagyu Estate fortification, not a surveyed Edo building. CC0 scans are physically plausible surfaces but roof scan has Western overlaps and is used only as micro-surface on original curved clay geometry. In-engine lighting, seam tiling, Nanite build, and Mac render cost remain unqualified.",
}
MANIFEST.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_WALL_CREATED", len(source_meshes), triangles, bounds, slots)
