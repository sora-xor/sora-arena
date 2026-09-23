"""Import source-only integrated Estate road candidates in pinned UE 5.8.2.

This does not place assets in gameplay. A visual review and exact-engine cook
must pass before any release WorldBuilder change. The eight HI central tiles
are Nanite candidates; independent MAC meshes are conventional fallbacks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.2"):
    raise RuntimeError(f"Integrated Roji import requires pinned UE 5.8.2; got {version}")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuIntegratedRoji"
record = json.loads((source / "manifest.json").read_text())
dest = "/Game/Generated/Environment/IntegratedRoji"
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if (record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_nyaagyu_integrated_roji.py"
        or record["generator_sha256"] != sha(root / record["generator"])
        or record["source_blend_sha256"] != sha(source / record["source_blend"])
        or record["nominal_stone_count"] < 300
        or record["old_repeating_scan_removed"] is not True
        or record["road_extent_m"] != [64, 5.24]
        or len(record["tile_records"]) != 16
        or not record["collision"].startswith("Unchanged flat Estate box")):
    raise RuntimeError("Integrated Roji source identity or collision policy changed")
for key in ("base_terrain", "stone_scan", "soil_scan", "gravel_scan"):
    item = root / record[key + "_manifest"]
    if sha(item) != record[key + "_manifest_sha256"]:
        raise RuntimeError("Roji source manifest changed: " + str(item))

slots = ["M_Roji_EstateSoil", "M_Roji_MineralBed",
         "M_Roji_IndividualStone", "M_Roji_EdgeMineral"]
for tile in record["tile_records"]:
    tier, x, y = tile["tier"], *tile["index"]
    expected = f"SM_NyaagyuIntegratedRoji_{tier.upper()}_X{x}_Y{y}"
    if (tier not in ("hi", "mac") or x not in range(4) or y not in (1, 2)
            or tile["name"] != expected or tile["fbx"] != expected + ".fbx"
            or tile["slots"] != slots
            or tile["placement_center_cm"] != [-2400 + 1600 * x, -1950 + 1300 * y, 0]
            or sha(source / tile["fbx"]) != tile["fbx_sha256"]):
        raise RuntimeError("Roji tile identity changed: " + expected)

assets.make_directory(dest)
assets.make_directory(dest + "/Textures")
scan_sources = {}
for role, key in (("gravel", "gravel_scan"), ("stone", "stone_scan")):
    manifest_path = root / record[key + "_manifest"]
    scan = json.loads(manifest_path.read_text())
    if scan["license"] != "CC0-1.0" or not scan.get("source_url", scan.get("asset_url", "")).startswith("https://polyhaven.com/a/"):
        raise RuntimeError("Roji source scan license or URL changed: " + role)
    scan_sources[role] = {}
    for f in scan["files"]:
        channel = f["channel"]
        if channel not in ("Diffuse", "nor_dx", "arm"):
            continue
        path = manifest_path.parent / f["file"]
        if not path.is_file() or sha(path) != f["sha256"]:
            raise RuntimeError("Roji pinned PBR map missing: " + str(path))
        scan_sources[role][channel] = path
    if set(scan_sources[role]) != {"Diffuse", "nor_dx", "arm"}:
        raise RuntimeError("Roji source PBR triplet incomplete: " + role)

textures = {}
for role in scan_sources:
    textures[role] = {}
    for channel, path in scan_sources[role].items():
        name = f"T_Roji_{role.title()}_{channel}"
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest + "/Textures"
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        tools.import_asset_tasks([task])
        tex = assets.load_asset(task.destination_path + "/" + name)
        if not isinstance(tex, unreal.Texture2D):
            raise RuntimeError("Roji PBR map import failed: " + name)
        tex.set_editor_property("srgb", channel == "Diffuse")
        if channel == "nor_dx":
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            tex.set_editor_property("flip_green_channel", False)
        elif channel == "arm":
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(tex)
        textures[role][channel] = tex


def node(material, cls, x, y, **props):
    n = lib.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def link(a, out, b, pin):
    if not lib.connect_material_expressions(a, out, b, pin):
        raise RuntimeError(f"Roji material connection failed: {out}->{pin}")


def output(a, out, prop):
    if not lib.connect_material_property(a, out, prop):
        raise RuntimeError(f"Roji material output failed: {prop}")


master_name = "M_NyaagyuIntegratedRoji_PBR"
master = assets.load_asset(dest + "/" + master_name) if assets.does_asset_exist(dest + "/" + master_name) else tools.create_asset(
    master_name, dest, unreal.Material, unreal.MaterialFactoryNew())
for old in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Roji master retained old expressions")
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1000, -350,
            parameter_name="AlbedoMap", texture=textures["stone"]["Diffuse"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1000, -60,
              parameter_name="NormalMap", texture=textures["stone"]["nor_dx"])
arm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 250,
           parameter_name="ARMMap", texture=textures["stone"]["arm"])
vertex = node(master, unreal.MaterialExpressionVertexColor, -700, -550)
tint = node(master, unreal.MaterialExpressionVectorParameter, -700, -330,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
colored = node(master, unreal.MaterialExpressionMultiply, -350, -330)
link(base, "RGB", colored, "A")
link(vertex, "", colored, "B")
tinted = node(master, unreal.MaterialExpressionMultiply, -80, -330)
link(colored, "", tinted, "A")
link(tint, "RGB", tinted, "B")
output(tinted, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
for channel, prop, y, mask in (
        ("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 70, (True, False, False)),
        ("G", unreal.MaterialProperty.MP_ROUGHNESS, 250, (False, True, False)),
        ("B", unreal.MaterialProperty.MP_METALLIC, 430, (False, False, True))):
    part = node(master, unreal.MaterialExpressionComponentMask, -400, y,
                r=mask[0], g=mask[1], b=mask[2], a=False)
    link(arm, "RGB", part, "")
    output(part, "", prop)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(p) for p in lib.get_texture_parameter_names(master)} != {"AlbedoMap", "NormalMap", "ARMMap"}:
    raise RuntimeError("Roji master texture parameters incomplete")

settings = {
    "MineralBed": ("gravel", (.69, .71, .70)),
    "IndividualStone": ("stone", (.95, .94, .91)),
    "EdgeMineral": ("stone", (.66, .68, .67)),
}
for role, (surface, color) in settings.items():
    name = "MI_NyaagyuIntegratedRoji_" + role
    instance = assets.load_asset(dest + "/" + name) if assets.does_asset_exist(dest + "/" + name) else tools.create_asset(
        name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for parameter, channel in (("AlbedoMap", "Diffuse"),
                               ("NormalMap", "nor_dx"), ("ARMMap", "arm")):
        tex = textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, tex)
        actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if actual is None or actual.get_path_name() != tex.get_path_name():
            raise RuntimeError("Roji material map did not bind: " + name + "/" + parameter)
    lib.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*color, 1))
    assets.save_loaded_asset(instance)

tasks = []
for tile in record["tile_records"]:
    task = unreal.AssetImportTask()
    task.filename = str(source / tile["fbx"])
    task.destination_path = dest
    task.destination_name = tile["name"]
    task.automated = True
    task.replace_existing = True
    task.save = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_materials = True
    opts.import_textures = False
    opts.import_as_skeletal = False
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    opts.static_mesh_import_data.combine_meshes = True
    opts.static_mesh_import_data.generate_lightmap_u_vs = False
    opts.static_mesh_import_data.auto_generate_collision = False
    opts.static_mesh_import_data.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    opts.static_mesh_import_data.set_editor_property("build_nanite", tile["tier"] == "hi")
    task.options = opts
    tasks.append(task)
tools.import_asset_tasks(tasks)
for tile in record["tile_records"]:
    path = dest + "/" + tile["name"]
    mesh = assets.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("Roji source mesh did not import: " + path)
    names = [str(s.material_slot_name) for s in mesh.get_editor_property("static_materials")]
    if len(names) != 4 or not all(a in b for a, b in zip(slots, names)):
        raise RuntimeError("Roji mesh material slots changed: " + path + " " + repr(names))
    if bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")) != (tile["tier"] == "hi"):
        raise RuntimeError("Roji Nanite tier changed: " + path)
    assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
unreal.log("NYAAGYU_INTEGRATED_ROJI_IMPORTED: source-only 64 m road candidate; no gameplay placement or collision")
