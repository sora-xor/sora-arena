"""Import the separate UV/PBR horse study into the pinned UE 5.8.2 editor.

Run after opening the project in UE 5.8.2:
  UnrealEditor-Cmd SoraArena.uproject -ExecutePythonScript=scripts/unreal/import_nyaagyu_horse_pbr.py

This never replaces the original horse review mesh or changes its geometry.
Only four exact existing horse/tack slots receive PBR instances.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.2"):
    raise RuntimeError(f"Nyaagyu horse PBR import requires Unreal Engine 5.8.2; got {version}")

root = Path(unreal.Paths.project_dir()).resolve()
horse = root / "Content/SourceArt/Horses/Nyaagyu"
source = horse / "PBR"
base = json.loads((horse / "manifest.json").read_text())
maps = json.loads((source / "manifest.json").read_text())
variant = json.loads((source / "variant_manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if (maps["schema_version"] != 1 or variant["schema_version"] != 1
        or maps["base_horse_blend_sha256"] != base["blend_sha256"]
        or maps["base_horse_fbx_sha256"] != base["fbx_sha256"]
        or variant["base_blend_sha256"] != base["blend_sha256"]
        or variant["base_fbx_sha256"] != base["fbx_sha256"]
        or variant["pbr_manifest_sha256"] != sha(source / "manifest.json")
        or variant["sora_logo_sha256"] != base["insignia_sha256"]
        or sha(source / variant["fbx"]) != variant["fbx_sha256"]):
    raise RuntimeError("Nyaagyu horse PBR source, base geometry, or SORA identity changed")
for original, digest in ((base["source_blend"], base["blend_sha256"]),
                         (base["fbx"], base["fbx_sha256"])):
    if sha(horse / original) != digest:
        raise RuntimeError(f"Original Nyaagyu horse source changed: {original}")
if set(maps["material_slots"]) != {
        "M_Horse_SealBrownCoat", "M_Horse_DarkPoints",
        "M_Tack_DarkLeather", "M_Tack_BlackenedIron"}:
    raise RuntimeError("Nyaagyu PBR material slot contract changed")
if len(variant["material_slots"]) != 17 or len(variant["exact_sora_kamon_objects"]) != 8:
    raise RuntimeError("Nyaagyu horse material or kamon contract changed")

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
destination = "/Game/ArtReview/Horses/NyaagyuPBR"
assets.make_directory(destination)
assets.make_directory(destination + "/Textures")

textures = {}
for material_set in maps["maps"]:
    name = material_set["name"]
    if (material_set["resolution"] != [2048, 2048]
            or {item["channel"] for item in material_set["maps"]} != {"Albedo", "NormalDX", "ORM"}):
        raise RuntimeError(f"Nyaagyu horse PBR map set is incomplete: {name}")
    textures[name] = {}
    for entry in material_set["maps"]:
        path = (source / entry["file"]).resolve()
        if path.parent != source.resolve() or sha(path) != entry["sha256"]:
            raise RuntimeError(f"Nyaagyu horse map differs from its source hash: {path}")
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = destination + "/Textures"
        task.destination_name = path.stem
        task.automated = True
        task.replace_existing = True
        task.save = True
        tools.import_asset_tasks([task])
        texture = assets.load_asset(destination + "/Textures/" + path.stem)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Nyaagyu horse map failed UE import: {path.name}")
        texture.set_editor_property("srgb", entry["channel"] == "Albedo")
        if entry["channel"] == "NormalDX":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif entry["channel"] == "ORM":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(texture)
        textures[name][entry["channel"]] = texture


def node(material, cls, x, y, **properties):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(left, output, right, pin):
    if not lib.connect_material_expressions(left, output, right, pin):
        raise RuntimeError(f"Nyaagyu horse material connection failed: {output} -> {pin}")


def output(expression, output_name, property_name):
    if not lib.connect_material_property(expression, output_name, property_name):
        raise RuntimeError(f"Nyaagyu horse material output failed: {property_name}")


master_name = "M_NyaagyuHorse_PBR"
master_path = destination + "/" + master_name
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    master_name, destination, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(master)
base_map = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -320,
                parameter_name="AlbedoMap", texture=textures["horse_coat"]["Albedo"])
normal_map = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -30,
                  parameter_name="NormalMap", texture=textures["horse_coat"]["NormalDX"])
orm_map = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, 270,
               parameter_name="ORMMap", texture=textures["horse_coat"]["ORM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -560, -520,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
colored = node(master, unreal.MaterialExpressionMultiply, -220, -320)
link(base_map, "RGB", colored, "A")
link(tint, "RGB", colored, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal_map, "RGB", unreal.MaterialProperty.MP_NORMAL)
for channel, property_name, y, mask_bits in (
        ("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 40, (True, False, False)),
        ("G", unreal.MaterialProperty.MP_ROUGHNESS, 220, (False, True, False)),
        ("B", unreal.MaterialProperty.MP_METALLIC, 400, (False, False, True))):
    mask = node(master, unreal.MaterialExpressionComponentMask, -470, y,
                r=mask_bits[0], g=mask_bits[1], b=mask_bits[2], a=False)
    link(orm_map, "RGB", mask, "")
    output(mask, "", property_name)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(item) for item in lib.get_texture_parameter_names(master)} != {"AlbedoMap", "NormalMap", "ORMMap"}:
    raise RuntimeError("Nyaagyu horse PBR master lost its map parameters")

instances = {}
for slot, definition in maps["material_slots"].items():
    surface = definition["surface"]
    if surface not in textures or len(definition["tint"]) != 3:
        raise RuntimeError(f"Nyaagyu horse PBR slot configuration is invalid: {slot}")
    name = "MI_NyaagyuHorse_" + slot.removeprefix("M_Horse_").removeprefix("M_Tack_")
    path = destination + "/" + name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, destination, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for parameter, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
        expected = textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Nyaagyu horse {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*definition["tint"], 1))
    assets.save_loaded_asset(instance)
    instances[slot] = instance

task = unreal.AssetImportTask()
task.filename = str(source / variant["fbx"])
task.destination_path = destination
task.destination_name = "SM_Nyaagyu_HorseAndTack_PBR"
task.automated = True
task.replace_existing = True
task.save = True
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_materials = True
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.generate_lightmap_u_vs = False
options.static_mesh_import_data.auto_generate_collision = False
task.options = options
tools.import_asset_tasks([task])
mesh = assets.load_asset(destination + "/SM_Nyaagyu_HorseAndTack_PBR")
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Nyaagyu PBR horse mesh failed UE import")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if sorted(slots) != variant["material_slots"]:
    raise RuntimeError(f"Nyaagyu PBR horse FBX slot identities changed: {slots}")
for index, slot in enumerate(slots):
    if slot in instances:
        mesh.set_material(index, instances[slot])
        if mesh.get_material(index).get_path_name() != instances[slot].get_path_name():
            raise RuntimeError(f"Nyaagyu PBR horse lost its {slot} binding")
assets.save_loaded_asset(mesh)
assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAGYU_HORSE_PBR_READY: {len(textures)} map sets, {len(instances)} exact-bound slots, {len(slots)} mesh slots")
