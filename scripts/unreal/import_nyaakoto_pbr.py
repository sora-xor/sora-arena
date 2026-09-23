"""Import Nyaakoto's project-owned fur, woven cloth and lacquer PBR maps.

Called after the skeletal FBX import. Runtime material instances are bound by
exact FBX slot identity in ASoraCharacter; the wallet and combat are unaffected.
"""

from pathlib import Path
import hashlib
import json
import struct
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
hero_source = source.parent
hero_record = json.loads((hero_source / "manifest.json").read_text())
eye_maps = hero_record.get("generated_textures", [])
if (hero_record.get("schema_version") != 2 or len(eye_maps) != 1
        or eye_maps[0].get("path") != "EyeStudy/T_Nyaakoto_Iris_Albedo.png"
        or record["material_slots"]["M_Hero_BlueEye"]["tint"] != [1, 1, 1]):
    raise RuntimeError("Nyaakoto painted iris source or material identity changed")
iris_path = (hero_source / eye_maps[0]["path"]).resolve()
if not iris_path.is_relative_to(hero_source.resolve()):
    raise RuntimeError("Nyaakoto iris source escaped the hero art directory")
iris_bytes = iris_path.read_bytes()
if (hashlib.sha256(iris_bytes).hexdigest() != eye_maps[0]["sha256"]
        or iris_bytes[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        or struct.unpack(">II", iris_bytes[16:24]) != (1024, 1024)):
    raise RuntimeError("Nyaakoto painted iris differs from its authored source")

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

iris_name = "T_Nyaakoto_Iris_Albedo"
iris_task = unreal.AssetImportTask()
iris_task.filename = str(iris_path)
iris_task.destination_path = destination + "/Textures"
iris_task.destination_name = iris_name
iris_task.automated = True
iris_task.replace_existing = True
iris_task.save = True
tools.import_asset_tasks([iris_task])
iris_texture = assets.load_asset(destination + "/Textures/" + iris_name)
if not isinstance(iris_texture, unreal.Texture2D):
    raise RuntimeError("Nyaakoto painted iris failed UE import")
iris_texture.set_editor_property("srgb", True)
iris_texture.set_editor_property("max_texture_size", 1024)
assets.save_loaded_asset(iris_texture)


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
master.set_editor_property("used_with_skeletal_mesh", True)
# UE 5.8's bulk helper removes from the array it iterates and can leave half
# the previous graph alive. Old output links then compile disconnected masks.
# Delete a snapshot one expression at a time before rebuilding this generated
# material; neither the source textures nor player data are affected.
for old_expression in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old_expression)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Nyaakoto PBR master retained expressions from its prior import")
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, -580,
            parameter_name="AlbedoMap", texture=textures["neutral"]["Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, -170,
              parameter_name="NormalMap", texture=textures["neutral"]["NormalDX"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 230,
           parameter_name="ORMMap", texture=textures["neutral"]["ORM"])
white_base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, -400,
                  parameter_name="WhiteFurAlbedoMap", texture=textures["fur_white"]["Albedo"])
white_normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 20,
                    parameter_name="WhiteFurNormalMap", texture=textures["fur_white"]["NormalDX"])
white_orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -1100, 430,
                 parameter_name="WhiteFurORMMap", texture=textures["fur_white"]["ORM"])
vertex_color = node(master, unreal.MaterialExpressionVertexColor, -850, 680)
blend_enabled = node(master, unreal.MaterialExpressionScalarParameter, -850, 830,
                     parameter_name="CoatBlendEnabled", default_value=0.0)
coat_factor = node(master, unreal.MaterialExpressionMultiply, -620, 740)
link(vertex_color, "R", coat_factor, "A")
link(blend_enabled, "", coat_factor, "B")
white_tint = node(master, unreal.MaterialExpressionVectorParameter, -830, -620,
                  parameter_name="WhiteFurTint", default_value=unreal.LinearColor(.92, .93, .94, 1))
white_colored = node(master, unreal.MaterialExpressionMultiply, -620, -450)
link(white_base, "RGB", white_colored, "A")
link(white_tint, "RGB", white_colored, "B")
albedo_blend = node(master, unreal.MaterialExpressionLinearInterpolate, -400, -500)
link(base, "RGB", albedo_blend, "A")
link(white_colored, "", albedo_blend, "B")
link(coat_factor, "", albedo_blend, "Alpha")
normal_blend = node(master, unreal.MaterialExpressionLinearInterpolate, -400, -120)
link(normal, "RGB", normal_blend, "A")
link(white_normal, "RGB", normal_blend, "B")
link(coat_factor, "", normal_blend, "Alpha")
normal_unit = node(master, unreal.MaterialExpressionNormalize, -180, -100)
link(normal_blend, "", normal_unit, "")
tint = node(master, unreal.MaterialExpressionVectorParameter, -180, -620,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
roughness_scale = node(master, unreal.MaterialExpressionScalarParameter, -180, 560,
                       parameter_name="RoughnessScale", default_value=1.0)
metallic_scale = node(master, unreal.MaterialExpressionScalarParameter, -180, 760,
                      parameter_name="MetallicScale", default_value=0.0)
colored = node(master, unreal.MaterialExpressionMultiply, 40, -400)
link(albedo_blend, "", colored, "A")
link(tint, "RGB", colored, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal_unit, "", unreal.MaterialProperty.MP_NORMAL)
orm_masks = []


def blend_orm_channel(channel, y):
    flags = dict(r=channel == "r", g=channel == "g", b=channel == "b", a=False)
    grey = node(master, unreal.MaterialExpressionComponentMask, -650, y, **flags)
    white = node(master, unreal.MaterialExpressionComponentMask, -650, y + 95, **flags)
    link(orm, "RGB", grey, "")
    link(white_orm, "RGB", white, "")
    orm_masks.extend((grey, white))
    blended = node(master, unreal.MaterialExpressionLinearInterpolate, -350, y)
    link(grey, "", blended, "A")
    link(white, "", blended, "B")
    link(coat_factor, "", blended, "Alpha")
    return blended

ao = blend_orm_channel("r", 130)
roughness = blend_orm_channel("g", 370)
metallic = blend_orm_channel("b", 700)
output(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
roughness_mul = node(master, unreal.MaterialExpressionMultiply, -120, 420)
link(roughness, "", roughness_mul, "A")
link(roughness_scale, "", roughness_mul, "B")
output(roughness_mul, "", unreal.MaterialProperty.MP_ROUGHNESS)
metallic_mul = node(master, unreal.MaterialExpressionMultiply, -120, 700)
link(metallic, "", metallic_mul, "A")
link(metallic_scale, "", metallic_mul, "B")
output(metallic_mul, "", unreal.MaterialProperty.MP_METALLIC)
if any(not lib.get_inputs_for_material_expression(master, mask)[0] for mask in orm_masks):
    raise RuntimeError("Nyaakoto PBR ORM mask lost its source connection")
if lib.get_num_material_expressions(master) != 29:
    raise RuntimeError("Nyaakoto PBR master retained an unexpected expression")
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
required_texture_parameters = {
    "AlbedoMap", "NormalMap", "ORMMap", "WhiteFurAlbedoMap", "WhiteFurNormalMap", "WhiteFurORMMap",
}
if {str(item) for item in lib.get_texture_parameter_names(master)} != required_texture_parameters:
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
        expected = (iris_texture if slot_name == "M_Hero_BlueEye" and parameter == "AlbedoMap"
                    else textures[surface["surface"]][channel])
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Nyaakoto {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(
        instance, "Tint", unreal.LinearColor(*surface["tint"], 1))
    lib.set_material_instance_scalar_parameter_value(instance, "RoughnessScale", surface["roughness_scale"])
    lib.set_material_instance_scalar_parameter_value(instance, "MetallicScale", surface["metallic_scale"])
    enable_blend = float(slot_name == "M_Hero_GreyTabbyFur")
    lib.set_material_instance_scalar_parameter_value(instance, "CoatBlendEnabled", enable_blend)
    if abs(lib.get_material_instance_scalar_parameter_value(instance, "CoatBlendEnabled") - enable_blend) > 1e-6:
        raise RuntimeError(f"Nyaakoto {name} lost its coat-mask selector")
    if enable_blend:
        for parameter, channel in (("WhiteFurAlbedoMap", "Albedo"),
                                   ("WhiteFurNormalMap", "NormalDX"),
                                   ("WhiteFurORMMap", "ORM")):
            expected = textures["fur_white"][channel]
            lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
            bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
            if not bound or bound.get_path_name() != expected.get_path_name():
                raise RuntimeError(f"Nyaakoto {name} lost its {parameter} binding")
        white_tint_value = record["material_slots"]["M_Hero_WhiteFur"]["tint"]
        lib.set_material_instance_vector_parameter_value(
            instance, "WhiteFurTint", unreal.LinearColor(*white_tint_value, 1))
    assets.save_loaded_asset(instance)

assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAKOTO_PBR_READY: {len(textures)} texture sets, {len(record['material_slots'])} material instances")
