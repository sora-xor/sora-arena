"""Import CC0 pine-sapling variants with explicit PBR and masked needles."""

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaagyu pine import")
root = Path(unreal.Paths.project_dir()).resolve()
art = root / "Content/SourceArt/Environment/PolyHaven/PineSaplingSmall"
record = json.loads((art / "manifest.json").read_text())
foliage = "/Game/Generated/Environment/Foliage"
texture_root = foliage + "/Textures"
if (record.get("schema_version") != 1
        or record.get("asset_id") != "pine_sapling_small"
        or record.get("upstream_page") != "https://polyhaven.com/a/pine_sapling_small"
        or record.get("license") != "CC0-1.0; https://polyhaven.com/license"
        or record.get("generator") != "scripts/art/create_nyaagyu_pine_saplings.py"
        or record.get("material_slots") != ["M_NyaagyuPine_Bark", "M_NyaagyuPine_Needles"]
        or record.get("instances_in_nyaagyu_estate") != 9
        or record.get("gameplay_collision") is not False
        or len(record.get("meshes", [])) != 6
        or len(record.get("upstream_files", [])) != 8
        or len(record.get("texture_files", [])) != 8):
    raise RuntimeError("Nyaagyu pine source identity changed")

for item in record["upstream_files"] + record["texture_files"]:
    file = art / item["path"]
    if (not file.is_file() or file.stat().st_size != item["bytes"]
            or hashlib.sha256(file.read_bytes()).hexdigest() != item["sha256"]):
        raise RuntimeError(f"Pinned CC0 pine file changed: {file}")
for name, hash_key in (("source_blend", "source_blend_sha256"),
                       ("preview", "preview_sha256")):
    file = art / record[name]
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != record[hash_key]:
        raise RuntimeError(f"Nyaagyu pine source review changed: {file}")

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
assets.make_directory(foliage)
assets.make_directory(texture_root)
mesh_tasks = []
for variant in "abc":
    for tier in ("hi", "mac"):
        matches = [item for item in record["meshes"]
                   if item.get("variant") == variant and item.get("tier") == tier]
        if len(matches) != 1:
            raise RuntimeError(f"Missing or duplicate pine {variant}/{tier} tier")
        item = matches[0]
        name = f"SM_NyaagyuPine_{variant.upper()}_{tier.upper()}"
        file = art / item["fbx"]
        if (item["name"] != name or item["fbx"] != name + ".fbx"
                or item["unreal_asset"] != f"{foliage}/{name}.{name}"
                or item["nanite"] != (tier == "hi")
                or item["material_slots"] != record["material_slots"]
                or not file.is_file()
                or hashlib.sha256(file.read_bytes()).hexdigest() != item["fbx_sha256"]):
            raise RuntimeError(f"Nyaagyu pine mesh changed: {name}")
        task = unreal.AssetImportTask()
        task.filename = str(file)
        task.destination_path = foliage
        task.destination_name = name
        task.automated = True
        task.replace_existing = True
        task.save = True
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_materials = False
        options.import_textures = False
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.generate_lightmap_u_vs = False
        options.static_mesh_import_data.auto_generate_collision = False
        options.static_mesh_import_data.set_editor_property("build_nanite", tier == "hi")
        task.options = options
        mesh_tasks.append(task)
tools.import_asset_tasks(mesh_tasks)

textures = {}
for item in record["texture_files"]:
    file = art / item["path"]
    channel = file.stem.removeprefix("pine_sapling_small_").removesuffix("_2k")
    name = "T_NyaagyuPine_" + channel
    task = unreal.AssetImportTask()
    task.filename = str(file)
    task.destination_path = texture_root
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    texture = assets.load_asset(f"{texture_root}/{name}")
    if not isinstance(texture, unreal.Texture2D) or channel in textures:
        raise RuntimeError(f"Nyaagyu pine texture import failed: {name}")
    texture.set_editor_property("srgb", channel.endswith("diff"))
    if channel.endswith("nor_dx"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif channel.endswith("arm") or channel.endswith("mask"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    assets.save_loaded_asset(texture)
    textures[channel] = texture
if set(textures) != {"bark_diff", "bark_arm", "bark_nor_dx",
                     "twig_diff", "twig_arm", "twig_nor_dx",
                     "twig_alpha", "twig_mask"}:
    raise RuntimeError("Nyaagyu pine PBR channel set changed")

material_lib = unreal.MaterialEditingLibrary
materials = {}
for role, prefix in (("Bark", "bark"), ("Needles", "twig")):
    name = "M_NyaagyuPine_" + role
    path = f"{foliage}/{name}"
    material = (assets.load_asset(path) if assets.does_asset_exist(path)
                else tools.create_asset(name, foliage, unreal.Material, unreal.MaterialFactoryNew()))
    for old_expression in list(material_lib.get_material_expressions(material)):
        material_lib.delete_material_expression(material, old_expression)
    if material_lib.get_num_material_expressions(material):
        raise RuntimeError(f"Pine material {name} retained expressions from its prior import")
    material.set_editor_property("two_sided", role == "Needles")
    if role == "Needles":
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    for parameter, channel, property_name, y in (
        ("AlbedoMap", prefix + "_diff", unreal.MaterialProperty.MP_BASE_COLOR, -250),
        ("NormalMap", prefix + "_nor_dx", unreal.MaterialProperty.MP_NORMAL, 0)):
        expression = material_lib.create_material_expression(
            material, unreal.MaterialExpressionTextureSampleParameter2D, -600, y)
        expression.set_editor_property("parameter_name", parameter)
        expression.set_editor_property("texture", textures[channel])
        if not material_lib.connect_material_property(expression, "RGB", property_name):
            raise RuntimeError(f"Could not bind pine {role} {parameter}")
    arm = material_lib.create_material_expression(
        material, unreal.MaterialExpressionTextureSampleParameter2D, -600, 250)
    arm.set_editor_property("parameter_name", "ARMMap")
    arm.set_editor_property("texture", textures[prefix + "_arm"])
    for channel, property_name in (("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                                   ("G", unreal.MaterialProperty.MP_ROUGHNESS),
                                   ("B", unreal.MaterialProperty.MP_METALLIC)):
        if not material_lib.connect_material_property(arm, channel, property_name):
            raise RuntimeError(f"Could not bind pine {role} ARM {channel}")
    if role == "Needles":
        mask = material_lib.create_material_expression(
            material, unreal.MaterialExpressionTextureSampleParameter2D, -600, 500)
        mask.set_editor_property("parameter_name", "NeedleMask")
        mask.set_editor_property("texture", textures["twig_mask"])
        if not material_lib.connect_material_property(mask, "R", unreal.MaterialProperty.MP_OPACITY_MASK):
            raise RuntimeError("Could not bind pine needle cutout mask")
    material_lib.layout_material_expressions(material)
    material_lib.recompile_material(material)
    assets.save_loaded_asset(material)
    materials[name] = material

for item in record["meshes"]:
    name = item["name"]
    mesh = assets.load_asset(f"{foliage}/{name}")
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Nyaagyu pine mesh import missing: {name}")
    slots = [str(slot.get_editor_property("material_slot_name"))
             for slot in mesh.get_editor_property("static_materials")]
    if sorted(slots) != record["material_slots"]:
        raise RuntimeError(f"Nyaagyu pine PBR material zones lost: {name}: {slots}")
    for index, slot in enumerate(slots):
        mesh.set_material(index, materials[slot])
    if bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled")) != item["nanite"]:
        raise RuntimeError(f"Nyaagyu pine Nanite tier mismatch: {name}")
    assets.save_loaded_asset(mesh)

unreal.log("NYAAGYU_PINE_IMPORT_READY: 6 CC0 mesh tiers, 8 textures, 2 PBR materials")
