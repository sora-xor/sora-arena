"""Import Nyaakoto's project-owned fur, woven cloth and lacquer PBR maps.

Called after the skeletal FBX import. Runtime material instances are bound by
exact FBX slot identity in ASoraCharacter; the wallet and combat are unaffected.
"""

from pathlib import Path
import hashlib
import json
import unreal

if not unreal.SystemLibrary.get_engine_version().startswith("5.8.2"):
    raise RuntimeError("Nyaakoto PBR import requires the pinned Unreal Engine 5.8.2")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Characters/Hero/PBR"
record = json.loads((source / "manifest.json").read_text())
if (record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_nyaakoto_pbr_textures.py"
        or len(record["material_slots"]) != 23):
    raise RuntimeError("Nyaakoto PBR manifest identity is incomplete")

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
destination = "/Game/Generated/Characters/Nyaakoto"
assets.make_directory(destination)
assets.make_directory(destination + "/Textures")
textures = {}
for material_set in record["maps"]:
    name = material_set["name"]
    textures[name] = {}
    if {item["channel"] for item in material_set["maps"]} != {"Albedo", "NormalDX", "ORM"}:
        raise RuntimeError(f"Nyaakoto material {name} lacks PBR maps")
    for item in material_set["maps"]:
        path = source / item["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise RuntimeError(f"Nyaakoto PBR map differs from its source hash: {path}")
        asset_name = path.stem
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = destination + "/Textures"
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = True
        task.save = True
        tools.import_asset_tasks([task])
        texture = assets.load_asset(destination + "/Textures/" + asset_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Nyaakoto map failed UE import: {asset_name}")
        texture.set_editor_property("srgb", item["channel"] == "Albedo")
        if item["channel"] == "NormalDX":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif item["channel"] == "ORM":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", material_set["resolution"][0])
        assets.save_loaded_asset(texture)
        textures[name][item["channel"]] = texture


def node(material, expression_class, x, y, **properties):
    expression = lib.create_material_expression(material, expression_class, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(left, output, right, pin):
    if not lib.connect_material_expressions(left, output, right, pin):
        raise RuntimeError(f"Nyaakoto material connection failed: {output} -> {pin}")


def output(expression, output_name, material_property):
    if not lib.connect_material_property(expression, output_name, material_property):
        raise RuntimeError(f"Nyaakoto material output failed: {material_property}")


master_name = "M_Nyaakoto_PBR"
master_path = destination + "/" + master_name
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    master_name, destination, unreal.Material, unreal.MaterialFactoryNew())
lib.delete_all_material_expressions(master)
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -380,
            parameter_name="AlbedoMap", texture=textures["neutral"]["Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -50,
              parameter_name="NormalMap", texture=textures["neutral"]["NormalDX"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, 260,
           parameter_name="ORMMap", texture=textures["neutral"]["ORM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -480, -550,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
roughness_scale = node(master, unreal.MaterialExpressionScalarParameter, -470, 560,
                       parameter_name="RoughnessScale", default_value=1.0)
metallic_scale = node(master, unreal.MaterialExpressionScalarParameter, -470, 760,
                      parameter_name="MetallicScale", default_value=0.0)
colored = node(master, unreal.MaterialExpressionMultiply, -180, -350)
link(base, "RGB", colored, "A")
link(tint, "RGB", colored, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
ao = node(master, unreal.MaterialExpressionComponentMask, -470, 130, r=True, g=False, b=False, a=False)
roughness = node(master, unreal.MaterialExpressionComponentMask, -470, 360, r=False, g=True, b=False, a=False)
metallic = node(master, unreal.MaterialExpressionComponentMask, -470, 690, r=False, g=False, b=True, a=False)
for mask in (ao, roughness, metallic):
    link(orm, "RGB", mask, "")
output(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
roughness_mul = node(master, unreal.MaterialExpressionMultiply, -120, 420)
link(roughness, "", roughness_mul, "A")
link(roughness_scale, "", roughness_mul, "B")
output(roughness_mul, "", unreal.MaterialProperty.MP_ROUGHNESS)
metallic_mul = node(master, unreal.MaterialExpressionMultiply, -120, 700)
link(metallic, "", metallic_mul, "A")
link(metallic_scale, "", metallic_mul, "B")
output(metallic_mul, "", unreal.MaterialProperty.MP_METALLIC)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(item) for item in lib.get_texture_parameter_names(master)} != {"AlbedoMap", "NormalMap", "ORMMap"}:
    raise RuntimeError("Nyaakoto PBR master lost a required texture parameter")

for slot_name, surface in record["material_slots"].items():
    if not slot_name.startswith("M_Hero_") or surface["surface"] not in textures:
        raise RuntimeError(f"Nyaakoto material slot is invalid: {slot_name}")
    name = "MI_Nyaakoto_" + slot_name.removeprefix("M_Hero_")
    path = destination + "/" + name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name, destination, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for parameter, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
        expected = textures[surface["surface"]][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Nyaakoto {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(
        instance, "Tint", unreal.LinearColor(*surface["tint"], 1))
    lib.set_material_instance_scalar_parameter_value(instance, "RoughnessScale", surface["roughness_scale"])
    lib.set_material_instance_scalar_parameter_value(instance, "MetallicScale", surface["metallic_scale"])
    assets.save_loaded_asset(instance)

assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAKOTO_PBR_READY: {len(textures)} texture sets, {len(record['material_slots'])} material instances")
