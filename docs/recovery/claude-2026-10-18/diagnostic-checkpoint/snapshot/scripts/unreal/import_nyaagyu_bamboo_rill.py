"""Import the visual-only bamboo/rill subset of the Estate water-court study.

The full timber canopy and basin are deliberately excluded: they would create
false combat cover if placed outside the established campaign collision.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


version = unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.3"):
    raise RuntimeError(f"Bamboo/rill import requires pinned Unreal 5.8.3; got {version}")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuWaterCourt"
record = json.loads((source / "manifest.json").read_text())
dest = "/Game/Generated/Environment/BambooRill"
prop_dest = "/Game/Generated/Environment/Props"
name = "SM_Nyaagyu_BambooRill_4m"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if (record["schema_version"] != 1 or record["subset_name"] != name
        or record["subset_fbx"] != f"Content/SourceArt/Environment/NyaagyuWaterCourt/{name}.fbx"
        or record["source_files_sha256"][record["subset_fbx"]] != sha(root / record["subset_fbx"])
        or record["placement_policy"].startswith("visual-only") is False
        or record["subset_triangles"] < 30_000
        or record["subset_bounds_m"]["z"][1] > 3.6
        or record["subset_bounds_m"]["y"][0] < -.7
        or record["subset_bounds_m"]["y"][1] > 3.2):
    raise RuntimeError("Bamboo/rill source identity, hash, or visual-only envelope changed")
mac_config = (root / "Config/Mac/MacEngine.ini").read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Bamboo/rill conventional Mac fallback policy changed")

expected_slots = {
    "M_Court_Mud", "M_Court_ShallowRainwater", "M_Court_Stone",
    "M_Court_StoneWet", "M_Court_Moss", "M_Court_Bamboo",
    "M_Court_BambooNode", "M_Court_BambooLeaf",
}
if set(record["subset_material_slots"]) != expected_slots:
    raise RuntimeError("Bamboo/rill material zones changed")
deps = record["scan_dependencies"]
if set(deps) != {"AgedCedar", "CarvedStone", "RoofCeramic", "Moss",
                 "CompactedSilt", "BambooCulm", "BambooLeaf"}:
    raise RuntimeError("Bamboo/rill texture dependencies changed")

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
assets.make_directory(dest)
assets.make_directory(dest + "/Textures")
assets.make_directory(prop_dest)

# The three photographic scans are already imported and color-space qualified
# by the ground-dressing pipeline. Verify that exact source bytes are shared.
roadside_source = json.loads((root / "Content/SourceArt/Environment/NyaagyuGroundDressing/manifest.json").read_text())
roadside_bindings = {"CarvedStone": "RiverStone", "Moss": "ForestLitter",
                     "CompactedSilt": "DampSilt"}
textures = {}
for role, roadside_role in roadside_bindings.items():
    dep = deps[role]
    prior = roadside_source["dependencies"][roadside_role]
    if dep["license"] != "CC0-1.0" or prior["license"] != "CC0-1.0":
        raise RuntimeError(f"Bamboo/rill scan license changed: {role}")
    textures[role] = {}
    for channel in ("Albedo", "NormalDX", "ORM"):
        source_map = dep["files"][channel]
        prior_map = prior["files"][channel]
        if (source_map["sha256"] != prior_map["sha256"]
                or sha(root / source_map["path"]) != source_map["sha256"]):
            raise RuntimeError(f"Bamboo/rill scan provenance differs from Roadside: {role}/{channel}")
        texture_name = f"T_Roadside_{roadside_role}_{channel}"
        texture = assets.load_asset(f"/Game/Generated/Environment/Roadside/Textures/{texture_name}")
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Ground-dressing dependency is not imported: {texture_name}")
        textures[role][channel] = texture

for role in ("BambooCulm", "BambooLeaf"):
    dep = deps[role]
    if dep["license"] != "original-project-art" or set(dep["files"]) != {"Albedo", "NormalDX", "ORM"}:
        raise RuntimeError(f"Bamboo/rill original texture manifest changed: {role}")
    textures[role] = {}
    for channel, source_map in dep["files"].items():
        path = (root / source_map["path"]).resolve()
        if (not path.is_relative_to(source / "Textures")
                or sha(path) != source_map["sha256"]):
            raise RuntimeError(f"Bamboo/rill original map changed: {role}/{channel}")
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest + "/Textures"
        task.destination_name = f"T_BambooRill_{role}_{channel}"
        task.automated = True
        task.replace_existing = True
        task.save = True
        asset_tools.import_asset_tasks([task])
        texture = assets.load_asset(task.destination_path + "/" + task.destination_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Bamboo/rill texture import failed: {path}")
        texture.set_editor_property("srgb", channel == "Albedo")
        if channel == "NormalDX":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif channel == "ORM":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(texture)
        textures[role][channel] = texture

pbr = assets.load_asset("/Game/Generated/Environment/Roadside/M_NyaagyuRoadside_OpaquePBR")
if not isinstance(pbr, unreal.Material):
    raise RuntimeError("Bamboo/rill requires the qualified two-sided Roadside PBR master")
if {str(x) for x in lib.get_texture_parameter_names(pbr)} != {"AlbedoMap", "NormalMap", "ORMMap"}:
    raise RuntimeError("Roadside PBR master lost required texture pins")

water_path = dest + "/M_NyaagyuBambooRill_ShallowWater"
water = assets.load_asset(water_path) if assets.does_asset_exist(water_path) else asset_tools.create_asset(
    "M_NyaagyuBambooRill_ShallowWater", dest, unreal.Material, unreal.MaterialFactoryNew())
for old in list(lib.get_material_expressions(water)):
    lib.delete_material_expression(water, old)
if lib.get_num_material_expressions(water):
    raise RuntimeError("Bamboo/rill water shader retained nodes from a prior import")
water.set_editor_property("two_sided", False)
water.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
color = lib.create_material_expression(water, unreal.MaterialExpressionConstant3Vector, -260, -70)
color.set_editor_property("constant", unreal.LinearColor(.035, .067, .065, 1))
rough = lib.create_material_expression(water, unreal.MaterialExpressionConstant, -260, 120)
rough.set_editor_property("r", .18)
if (not lib.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
        or not lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)):
    raise RuntimeError("Bamboo/rill water shader output failed")
lib.recompile_material(water)
assets.save_loaded_asset(water)

slot_roles = {
    "M_Court_Mud": ("CompactedSilt", (.67, .67, .64), -.09),
    "M_Court_Stone": ("CarvedStone", (.73, .75, .73), .02),
    "M_Court_StoneWet": ("CarvedStone", (.43, .48, .47), -.20),
    "M_Court_Moss": ("Moss", (.39, .63, .40), .08),
    "M_Court_Bamboo": ("BambooCulm", (1, 1, 1), .0),
    "M_Court_BambooNode": ("BambooCulm", (.58, .56, .45), .08),
    "M_Court_BambooLeaf": ("BambooLeaf", (1, 1, 1), .0),
}
instances = {"M_Court_ShallowRainwater": water}
for slot, (role, tint, rough_bias) in slot_roles.items():
    instance_name = "MI_NyaagyuBambooRill_" + slot.removeprefix("M_Court_")
    path = dest + "/" + instance_name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        instance_name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, pbr)
    for parameter, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
        expected = textures[role][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Bamboo/rill lost {instance_name}/{parameter}")
    lib.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*tint, 1))
    lib.set_material_instance_scalar_parameter_value(instance, "RoughnessBias", rough_bias)
    assets.save_loaded_asset(instance)
    instances[slot] = instance

task = unreal.AssetImportTask()
task.filename = str(root / record["subset_fbx"])
task.destination_path = prop_dest
task.destination_name = name
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
options.static_mesh_import_data.set_editor_property("build_nanite", True)
task.options = options
asset_tools.import_asset_tasks([task])
mesh = assets.load_asset(prop_dest + "/" + name)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Bamboo/rill static mesh import failed")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if slots != record["subset_material_slots"]:
    raise RuntimeError(f"Bamboo/rill FBX material slots changed: {slots}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Bamboo/rill Nanite data was not built")
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh, nanite, True)
nanite = subsystem.get_nanite_settings(mesh)
if (not nanite.get_editor_property("enabled")
        or nanite.get_editor_property("fallback_percent_triangles") < .999
        or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED
        or subsystem.get_lod_count(mesh) < 1
        or subsystem.get_number_verts(mesh, 0) < 1000):
    raise RuntimeError("Bamboo/rill conventional Mac fallback is missing")
for index, slot in enumerate(slots):
    mesh.set_material(index, instances[slot])
    if mesh.get_material(index).get_path_name() != instances[slot].get_path_name():
        raise RuntimeError(f"Bamboo/rill material binding failed: {slot}")
assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
assets.save_directory(prop_dest, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAGYU_BAMBOO_RILL_READY: {len(slots)} materials, Nanite/full Mac fallback, visual-only source")
