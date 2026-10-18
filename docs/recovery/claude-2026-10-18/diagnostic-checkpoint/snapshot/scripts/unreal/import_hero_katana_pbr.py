"""Import and bind Nyaakoto's UV-authored first-person katana materials.

Called after the original FBX import.  No combat, entitlement, or wallet rule
depends on these purely visual material instances.
"""

import hashlib
import json
from pathlib import Path

import unreal


if not unreal.SystemLibrary.get_engine_version().startswith("5.8.3"):
    raise RuntimeError("Hero katana PBR import requires the pinned Unreal Engine 5.8.3")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Weapons/HeroKatana/PBR"
record = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
if (record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_hero_katana_pbr_textures.py"
        or len(record["material_slots"]) != 12):
    raise RuntimeError("Hero katana material manifest identity is incomplete")

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
destination = "/Game/Generated/Weapons/HeroKatana"
assets.make_directory(destination)
assets.make_directory(destination + "/Textures")
textures = {}
for group in record["maps"]:
    name = group["name"]
    if {entry["channel"] for entry in group["maps"]} != {"Albedo", "NormalDX", "ORM"}:
        raise RuntimeError(f"Hero katana surface lacks a PBR channel: {name}")
    textures[name] = {}
    for entry in group["maps"]:
        file = source / entry["file"]
        if hashlib.sha256(file.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Hero katana PBR map differs from its source: {file}")
        asset_name = file.stem
        task = unreal.AssetImportTask()
        task.filename = str(file)
        task.destination_path = destination + "/Textures"
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = True
        task.save = True
        tools.import_asset_tasks([task])
        texture = assets.load_asset(destination + "/Textures/" + asset_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Hero katana texture failed import: {asset_name}")
        texture.set_editor_property("srgb", entry["channel"] == "Albedo")
        if entry["channel"] == "NormalDX":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif entry["channel"] == "ORM":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", group["resolution"][0])
        assets.save_loaded_asset(texture)
        textures[name][entry["channel"]] = texture


def node(material, expression_type, x, y, **properties):
    expression = lib.create_material_expression(material, expression_type, x, y)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression


def link(a, output, b, pin):
    if not lib.connect_material_expressions(a, output, b, pin):
        raise RuntimeError(f"Hero katana material connection failed: {output} -> {pin}")


def output(expression, name, destination_property):
    if not lib.connect_material_property(expression, name, destination_property):
        raise RuntimeError(f"Hero katana material output failed: {destination_property}")


master_name = "M_HeroKatana_PBR"
master_path = destination + "/" + master_name
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    master_name, destination, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(master)
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -400,
            parameter_name="AlbedoMap", texture=textures["neutral"]["Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, -50,
              parameter_name="NormalMap", texture=textures["neutral"]["NormalDX"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -900, 260,
           parameter_name="ORMMap", texture=textures["neutral"]["ORM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -560, -550,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
rough_scale = node(master, unreal.MaterialExpressionScalarParameter, -560, 570,
                   parameter_name="RoughnessScale", default_value=1.0)
metal_scale = node(master, unreal.MaterialExpressionScalarParameter, -560, 760,
                   parameter_name="MetallicScale", default_value=1.0)
colored = node(master, unreal.MaterialExpressionMultiply, -240, -340)
link(base, "RGB", colored, "A")
link(tint, "RGB", colored, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
ao = node(master, unreal.MaterialExpressionComponentMask, -560, 100,
          r=True, g=False, b=False, a=False)
rough = node(master, unreal.MaterialExpressionComponentMask, -560, 340,
             r=False, g=True, b=False, a=False)
metal = node(master, unreal.MaterialExpressionComponentMask, -560, 690,
             r=False, g=False, b=True, a=False)
for mask in (ao, rough, metal):
    link(orm, "RGB", mask, "")
output(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
rough_mul = node(master, unreal.MaterialExpressionMultiply, -230, 410)
link(rough, "", rough_mul, "A")
link(rough_scale, "", rough_mul, "B")
output(rough_mul, "", unreal.MaterialProperty.MP_ROUGHNESS)
metal_mul = node(master, unreal.MaterialExpressionMultiply, -230, 690)
link(metal, "", metal_mul, "A")
link(metal_scale, "", metal_mul, "B")
output(metal_mul, "", unreal.MaterialProperty.MP_METALLIC)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(name) for name in lib.get_texture_parameter_names(master)} != {"AlbedoMap", "NormalMap", "ORMMap"}:
    raise RuntimeError("Hero katana master lost a required PBR parameter")

instances = {}
for slot_name, specification in record["material_slots"].items():
    if not slot_name.startswith("M_HK_") or specification["surface"] not in textures:
        raise RuntimeError(f"Hero katana material slot is invalid: {slot_name}")
    name = "MI_HK_" + slot_name.removeprefix("M_HK_")
    path = destination + "/" + name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, destination, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for parameter, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
        expected = textures[specification["surface"]][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not actual or actual.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Hero katana {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(
        instance, "Tint", unreal.LinearColor(*specification["tint"], 1))
    lib.set_material_instance_scalar_parameter_value(
        instance, "RoughnessScale", specification["roughness_scale"])
    lib.set_material_instance_scalar_parameter_value(
        instance, "MetallicScale", specification["metallic_scale"])
    assets.save_loaded_asset(instance)
    instances[slot_name] = instance

bound = set()
for mesh_name, expected_count in (("SM_Nyaagyu_HeroKatana", 9),
                                  ("SM_Nyaagyu_HeroSaya", 4)):
    mesh_path = "/Game/Generated/Meshes/" + mesh_name
    mesh = assets.load_asset(mesh_path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Hero sword or saya mesh is absent: {mesh_name}")
    slots = mesh.get_editor_property("static_materials")
    if len(slots) != expected_count:
        raise RuntimeError(f"{mesh_name} FBX material count changed: {len(slots)}")
    local = set()
    for index, slot in enumerate(slots):
        name = str(slot.get_editor_property("material_slot_name"))
        if name not in instances or name in local:
            raise RuntimeError(f"Unexpected or duplicate {mesh_name} FBX slot: {name}")
        mesh.set_material(index, instances[name])
        local.add(name)
    bound.update(local)
    assets.save_loaded_asset(mesh)
if bound != set(instances):
    raise RuntimeError("Hero katana/saya FBX omitted an authored material")
assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log(f"HERO_KATANA_PBR_READY: {len(textures)} texture sets, {len(instances)} bound materials")
