"""Bind the original lacquer texture set to the authored Estate torii.

Run after ``import_original_assets.py`` and ``import_environment_palette.py``.
The gate uses the palette's world-aligned PBR master; this script verifies its
three independently authored maps before changing the imported material slot.
"""

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Torii PBR import")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/ToriiLacquer"
record = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
destination = "/Game/Generated/Environment"
instance_name = "MI_Nyaagyu_ToriiLacquer"
if (record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_torii_lacquer_pbr.py"
        or record["material_slot"] != "M_Env_VermilionLacquer"
        or record["unreal_instance"] != f"{destination}/{instance_name}.{instance_name}"
        or record["tile_size_cm"] != 120.0
        or set(record["maps"]) != {"Albedo", "NormalDX", "ORM"}):
    raise RuntimeError("Torii lacquer source identity is incomplete")

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
assets.make_directory(destination + "/Textures")
textures = {}
for channel in ("Albedo", "NormalDX", "ORM"):
    entry = record["maps"][channel]
    file = source / entry["file"]
    if (entry["resolution"] != [2048, 2048]
            or not file.is_file()
            or hashlib.sha256(file.read_bytes()).hexdigest() != entry["sha256"]):
        raise RuntimeError(f"Torii lacquer {channel} source is absent or changed")
    name = file.stem
    task = unreal.AssetImportTask()
    task.filename = str(file)
    task.destination_path = destination + "/Textures"
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    texture = assets.load_asset(f"{destination}/Textures/{name}")
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError(f"Torii lacquer {channel} failed texture import")
    texture.set_editor_property("srgb", channel == "Albedo")
    if channel == "NormalDX":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif channel == "ORM":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    assets.save_loaded_asset(texture)
    textures[channel] = texture

master = assets.load_asset(destination + "/M_Nyaagyu_PBR")
if not isinstance(master, unreal.Material):
    raise RuntimeError("Import the Estate PBR palette before the lacquer")
path = destination + "/" + instance_name
instance = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
    instance_name, destination, unreal.MaterialInstanceConstant,
    unreal.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(instance, master)
for parameter, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ARMMap", "ORM")):
    expected = textures[channel]
    lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
    actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
    if actual is None or actual.get_path_name() != expected.get_path_name():
        raise RuntimeError(f"Torii lacquer lost its {parameter} binding")
scale = record["tile_size_cm"]
lib.set_material_instance_vector_parameter_value(instance, "TileSize", unreal.LinearColor(scale, scale, scale, 1))
assets.save_loaded_asset(instance)

mesh = assets.load_asset("/Game/Generated/Environment/Props/SM_Nyaagyu_ToriiGate")
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("The source-authored torii mesh was not imported")
slots = mesh.get_editor_property("static_materials")
matches = [index for index, slot in enumerate(slots)
           if str(slot.get_editor_property("material_slot_name")) == record["material_slot"]]
if len(matches) != 1:
    raise RuntimeError(f"Torii lacquer slot identity changed: {matches}")
mesh.set_material(matches[0], instance)
assets.save_loaded_asset(mesh)
assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log("NYAAGYU_TORII_LACQUER_READY: 2K original albedo/DirectX normal/ORM bound to Estate torii")
