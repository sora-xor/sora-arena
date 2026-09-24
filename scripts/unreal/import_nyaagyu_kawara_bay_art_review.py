"""Stage the source-only kawara bay as two isolated UE 5.8 ArtReview meshes.

Use preflight_kawara_bay_art_review.py --run, which gates version, disk space
and source hashes. This script never creates or modifies a playable level.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import unreal


def require(condition, message):
    if not condition:
        raise RuntimeError("SORA_KAWARA_ART_REVIEW_REJECTED: " + message)


root = Path(unreal.Paths.project_dir()).resolve()
expected_version = os.environ.get("SORA_KAWARA_ART_REVIEW_ENGINE")
actual_version = unreal.SystemLibrary.get_engine_version()
require(expected_version in ("5.8.2", "5.8.3") and
        actual_version.startswith(expected_version),
        f"Expected gated UE 5.8.2/diagnostic 5.8.3, got {actual_version}")
require(expected_version != "5.8.3" or (root / ".git").is_file(),
        "UE 5.8.3 diagnostics require a separate Git worktree")
preflight_path = root / "scripts/unreal/preflight_kawara_bay_art_review.py"
spec = importlib.util.spec_from_file_location("sora_kawara_preflight", preflight_path)
require(spec is not None and spec.loader is not None, "Could not load roof preflight")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)
preflight.check_source(root)
has_ibushi = preflight.check_optional_ibushi(root)

source = root / preflight.SOURCE_REL
manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
texture_manifest = json.loads((source / "texture_manifest.json").read_text(encoding="utf-8"))
destination = "/Game/Generated/ArtReview/KawaraBay"
tex_dest, mat_dest, mesh_dest = (destination + "/" + section for section in
                                 ("Textures", "Materials", "Meshes"))
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
for folder in (destination, tex_dest, mat_dest, mesh_dest):
    require(assets.make_directory(folder) or assets.does_directory_exist(folder),
            "Could not create isolated ArtReview package: " + folder)


def import_file(path, folder, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    loaded = assets.load_asset(folder + "/" + name)
    require(loaded is not None, f"Failed import: {path}")
    return loaded


texture_sources = {
    "Albedo": source / texture_manifest["files"]["Albedo"]["file"],
    "NormalDX": source / texture_manifest["files"]["NormalDX"]["file"],
    "ORM": source / texture_manifest["files"]["ORM"]["file"],
    "ImageGenColor": source / manifest["generated_albedo"]["file"],
    "SoraLogo": root / "Content/SourceArt/UI/SORA_Resistance_Logo.png",
}
if has_ibushi:
    ibushi_record = json.loads((source / "ibushi_texture_manifest.json").read_text(encoding="utf-8"))
    for role, item in ibushi_record["files"].items():
        texture_sources["Ibushi" + role] = source / item["file"]
textures = {}
for role, path in texture_sources.items():
    name = "T_KawaraBay_" + role
    texture = import_file(path, tex_dest, name)
    require(isinstance(texture, unreal.Texture2D), f"Not Texture2D: {name}")
    texture.set_editor_property("srgb", role in ("Albedo", "ImageGenColor",
                                                 "IbushiAlbedo", "SoraLogo"))
    if role in ("NormalDX", "IbushiNormalDX"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif role in ("ORM", "IbushiORM"):
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    require(assets.save_loaded_asset(texture), f"Could not save texture: {name}")
    textures[role] = texture


def material_asset(name):
    path = mat_dest + "/" + name
    material = (assets.load_asset(path) if assets.does_asset_exist(path)
                else tools.create_asset(name, mat_dest, unreal.Material, unreal.MaterialFactoryNew()))
    require(isinstance(material, unreal.Material), f"Material unavailable: {name}")
    for old in list(lib.get_material_expressions(material)):
        lib.delete_material_expression(material, old)
    require(lib.get_num_material_expressions(material) == 0,
            f"Stale nodes remained in {name}")
    return material


def expression(material, cls, x, y, **properties):
    node = lib.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        node.set_editor_property(key, value)
    return node


def output(node, pin, prop):
    require(lib.connect_material_property(node, pin, prop),
            f"Could not bind material output {prop}")


ceramic = material_asset("M_KawaraBay_SourcePBR")
ceramic.set_editor_property("two_sided", False)
ceramic.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
samples = {}
for role, y in (("Albedo", -280), ("NormalDX", 0), ("ORM", 280)):
    sample = expression(ceramic, unreal.MaterialExpressionTextureSampleParameter2D,
                        -600, y, parameter_name=role + "Map", texture=textures[role])
    samples[role] = sample
output(samples["Albedo"], "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
output(samples["NormalDX"], "RGB", unreal.MaterialProperty.MP_NORMAL)
output(samples["ORM"], "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
output(samples["ORM"], "G", unreal.MaterialProperty.MP_ROUGHNESS)
output(samples["ORM"], "B", unreal.MaterialProperty.MP_METALLIC)
lib.layout_material_expressions(ceramic)
lib.recompile_material(ceramic)
require(assets.save_loaded_asset(ceramic), "Could not save source PBR material")
require({str(x) for x in lib.get_texture_parameter_names(ceramic)} ==
        {"AlbedoMap", "NormalDXMap", "ORMMap"}, "Ceramic PBR graph changed")


def instance(name, parent):
    path = mat_dest + "/" + name
    obj = (assets.load_asset(path) if assets.does_asset_exist(path)
           else tools.create_asset(name, mat_dest, unreal.MaterialInstanceConstant,
                                   unreal.MaterialInstanceConstantFactoryNew()))
    require(isinstance(obj, unreal.MaterialInstanceConstant),
            f"Material instance unavailable: {name}")
    lib.set_material_instance_parent(obj, parent)
    return obj


ceramic_variants = {}
variant_roles = {
    "OriginalAtlas": ("Albedo", "NormalDX", "ORM"),
    "ImageGenColorOnly": ("ImageGenColor", "NormalDX", "ORM"),
}
if has_ibushi:
    variant_roles["IbushiCoherentPBR"] = ("IbushiAlbedo", "IbushiNormalDX", "IbushiORM")
for variant, roles in variant_roles.items():
    item = instance("MI_KawaraBay_" + variant, ceramic)
    for parameter, role in zip(("AlbedoMap", "NormalDXMap", "ORMMap"), roles):
        target = textures[role]
        lib.set_material_instance_texture_parameter_value(item, parameter, target)
        bound = lib.get_material_instance_texture_parameter_value(item, parameter)
        require(bound is not None and bound.get_path_name() == target.get_path_name(),
                f"Texture binding failed: {variant}/{parameter}")
    require(assets.save_loaded_asset(item), f"Could not save {variant}")
    ceramic_variants[variant] = item

flat = material_asset("M_KawaraBay_FlatPBR")
for cls, name, default, y, prop, pin in (
        (unreal.MaterialExpressionVectorParameter, "BaseColor",
         unreal.LinearColor(1, 1, 1, 1), -250, unreal.MaterialProperty.MP_BASE_COLOR, "RGB"),
        (unreal.MaterialExpressionScalarParameter, "Roughness", .8, 0,
         unreal.MaterialProperty.MP_ROUGHNESS, ""),
        (unreal.MaterialExpressionScalarParameter, "Metallic", 0, 250,
         unreal.MaterialProperty.MP_METALLIC, "")):
    node = expression(flat, cls, -400, y, parameter_name=name, default_value=default)
    output(node, pin, prop)
lib.recompile_material(flat)
require(assets.save_loaded_asset(flat), "Could not save flat PBR material")

slot_materials = {}
for slot, label, rgb, roughness, metallic in (
        ("M_Kawara_CharredCedarSupport", "CharredCedar", (.075, .058, .046), .8, 0),
        ("M_Kawara_ExposedClayEdge", "ClayEdge", (.21, .22, .22), .78, 0),
        ("M_Kawara_WeatheredBrassInlay", "BrassInlay", (.24, .18, .085), .43, .7)):
    item = instance("MI_KawaraBay_" + label, flat)
    lib.set_material_instance_vector_parameter_value(item, "BaseColor",
                                                     unreal.LinearColor(*rgb, 1))
    lib.set_material_instance_scalar_parameter_value(item, "Roughness", roughness)
    lib.set_material_instance_scalar_parameter_value(item, "Metallic", metallic)
    require(assets.save_loaded_asset(item), f"Could not save {label}")
    slot_materials[slot] = item

logo_material = material_asset("M_KawaraBay_SoraLogo_Masked")
logo_material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
logo_material.set_editor_property("two_sided", True)
logo_sample = expression(logo_material, unreal.MaterialExpressionTextureSampleParameter2D,
                         -500, -200, parameter_name="SoraLogoMap", texture=textures["SoraLogo"])
output(logo_sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
output(logo_sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
logo_roughness = expression(logo_material, unreal.MaterialExpressionConstant,
                            -500, 100, r=.46)
output(logo_roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
lib.recompile_material(logo_material)
require(assets.save_loaded_asset(logo_material), "Could not save SORA logo material")
slot_materials["M_Kawara_SORA_Kamon_UserRaster"] = logo_material

options = unreal.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.generate_lightmap_u_vs = False
options.static_mesh_import_data.auto_generate_collision = False
options.static_mesh_import_data.set_editor_property("build_nanite", True)
mesh_name = "SM_Nyaagyu_KawaraBay_SourcePBR"
mesh = import_file(source / "SM_Nyaagyu_KawaraBay.fbx", mesh_dest, mesh_name, options)
require(isinstance(mesh, unreal.StaticMesh), "Roof FBX did not import as a StaticMesh")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
expected_slots = set(slot_materials) | {"M_Kawara_FiredCeramic_OriginalAtlas"}
require(len(slots) == len(expected_slots) and set(slots) == expected_slots,
        f"Roof source material slots changed: {slots}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
require(subsystem.get_lod_count(mesh) >= 1 and
        subsystem.get_number_verts(mesh, 0) > 5000 and
        mesh.get_num_triangles(0) > 20000,
        "Roof conventional mesh LOD0 did not preserve the modeled roof")
nanite = subsystem.get_nanite_settings(mesh)
require(nanite.get_editor_property("enabled"), "Roof Nanite source data did not build")
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh, nanite, True)
nanite = subsystem.get_nanite_settings(mesh)
require(nanite.get_editor_property("enabled") and
        nanite.get_editor_property("fallback_target") == unreal.NaniteFallbackTarget.PERCENT_TRIANGLES and
        nanite.get_editor_property("fallback_percent_triangles") >= .999 and
        nanite.get_editor_property("generate_fallback") == unreal.NaniteGenerateFallback.ENABLED,
        "Roof full conventional Mac fallback changed")
for index, slot in enumerate(slots):
    target = (ceramic_variants["OriginalAtlas"] if slot ==
              "M_Kawara_FiredCeramic_OriginalAtlas" else slot_materials[slot])
    mesh.set_material(index, target)
    require(mesh.get_material(index).get_path_name() == target.get_path_name(),
            f"Roof material binding failed: {slot}")
require(assets.save_loaded_asset(mesh), "Could not save roof SourcePBR mesh")

ceramic_index = slots.index("M_Kawara_FiredCeramic_OriginalAtlas")
for variant_name in variant_roles:
    if variant_name == "OriginalAtlas":
        continue
    variant_path = mesh_dest + "/SM_Nyaagyu_KawaraBay_" + variant_name
    if assets.does_asset_exist(variant_path):
        require(assets.delete_asset(variant_path), "Could not replace ArtReview variant")
    variant = assets.duplicate_asset(mesh_dest + "/" + mesh_name, variant_path)
    require(isinstance(variant, unreal.StaticMesh), "Could not duplicate roof ArtReview mesh")
    variant.set_material(ceramic_index, ceramic_variants[variant_name])
    require(variant.get_material(ceramic_index).get_path_name() ==
            ceramic_variants[variant_name].get_path_name(),
            f"{variant_name} material binding failed")
    require(assets.save_loaded_asset(variant), f"Could not save {variant_name} roof variant")
require(assets.save_directory(destination, only_if_is_dirty=False, recursive=True),
        "Could not save isolated roof ArtReview package")
unreal.log(f"SORA_KAWARA_ART_REVIEW_IMPORT_OK: {len(variant_roles)} source-only mesh variants, 55 modeled tiles, "
           "Nanite/full Mac fallback, no actor placement; Lit/Lumen appearance unverified")
