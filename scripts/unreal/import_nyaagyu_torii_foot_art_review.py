"""Import the pinned gate-foot study only into the UE 5.8.2 ArtReview area.

This script does not place an actor, alter the Estate map, or modify gameplay
collision. The two local stone sockets are evaluated in an isolated package.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


engine = unreal.SystemLibrary.get_engine_version()
if not engine.startswith("5.8.2"):
    raise RuntimeError(f"Torii-foot ArtReview requires pinned UE 5.8.2; got {engine}")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuToriiFootStudy"
manifest_path = source / "manifest.json"
EXPECTED_MANIFEST_SHA256 = "e62a2dfeb5f6f89a3b9ee2d494de97aeeb69cf735204c3fb9199dcd38d0ace9b"
EXPECTED_GENERATOR_SHA256 = "8c6e72011d2ab7787121c1ca6e28c38c362a1f67f9bb7def3be50f4a5f4509ae"
EXPECTED_BLEND_SHA256 = "ce978d350b05e45589ecac3c079fb8a436db88128013d7ccf98ea07d6c567e0b"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


if sha(manifest_path) != EXPECTED_MANIFEST_SHA256:
    raise RuntimeError("Torii-foot manifest changed")
record = json.loads(manifest_path.read_text(encoding="utf-8"))
if (record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_nyaagyu_torii_foot_study.py"
        or sha(root / record["generator"]) != EXPECTED_GENERATOR_SHA256
        or record["source_blend"] != "Nyaagyu_ToriiFoot_Study.blend"
        or sha(source / record["source_blend"]) != EXPECTED_BLEND_SHA256
        or record["fbx"] != "SM_Nyaagyu_ToriiFoot_Study.fbx"
        or sha(source / record["fbx"]) != record["fbx_sha256"]
        or record["editable_parts"] != 26
        or record["source_triangles"] != 9688
        or record["material_slots"] != ["M_ToriiFoot_MossyRock_CC0"]
        or record["scan_asset"] != "https://polyhaven.com/a/mossy_rock"
        or record["scan_license"] != "CC0"
        or record["placement"] != "local gate origin: centers x=+-2.35 m, y=0; no gameplay collision"):
    raise RuntimeError("Torii-foot mesh, material, source, or placement identity changed")
files = record["scan_files"]
expected_names = {
    "diffuse": "mossy_rock_diff_2k.jpg",
    "normal_dx": "mossy_rock_nor_dx_2k.png",
    "arm": "mossy_rock_arm_2k.png",
    "displacement": "mossy_rock_disp_2k.png",
}
if set(files) != set(expected_names):
    raise RuntimeError("Torii-foot scan PBR channels changed")
for channel, expected in expected_names.items():
    entry = files[channel]
    if entry["file"] != expected or sha(source / "MossyRock" / expected) != entry["sha256"]:
        raise RuntimeError(f"Torii-foot pinned CC0 scan changed: {channel}")
mac_config = (root / "Config/Mac/MacEngine.ini").read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Torii-foot conventional Mac fallback policy changed")

destination = "/Game/Generated/ArtReview/ToriiFoot"
tex_dest = destination + "/Textures"
mat_dest = destination + "/Materials"
mesh_dest = destination + "/Meshes"
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
for folder in (destination, tex_dest, mat_dest, mesh_dest):
    assets.make_directory(folder)


def imported(path: Path, folder: str, name: str, options=None):
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
    asset = assets.load_asset(f"{folder}/{name}")
    if asset is None:
        raise RuntimeError(f"Torii-foot import failed: {path}")
    return asset


textures = {}
for channel, name in (("diffuse", "T_ToriiFoot_MossyRock_Albedo"),
                      ("normal_dx", "T_ToriiFoot_MossyRock_NormalDX"),
                      ("arm", "T_ToriiFoot_MossyRock_ARM")):
    texture = imported(source / "MossyRock" / files[channel]["file"], tex_dest, name)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError(f"Torii-foot scan import was not Texture2D: {channel}")
    texture.set_editor_property("srgb", channel == "diffuse")
    if channel == "normal_dx":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif channel == "arm":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    assets.save_loaded_asset(texture)
    textures[channel] = texture

name = "M_ToriiFoot_ScannedPBR"
path = f"{mat_dest}/{name}"
material = (assets.load_asset(path) if assets.does_asset_exist(path)
            else tools.create_asset(name, mat_dest, unreal.Material, unreal.MaterialFactoryNew()))
for expression in list(lib.get_material_expressions(material)):
    lib.delete_material_expression(material, expression)
if lib.get_num_material_expressions(material):
    raise RuntimeError("Torii-foot material retained stale nodes")
material.set_editor_property("two_sided", False)
material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)


def sample(parameter: str, channel: str, y: int):
    node = lib.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -550, y)
    node.set_editor_property("parameter_name", parameter)
    node.set_editor_property("texture", textures[channel])
    return node


albedo = sample("AlbedoMap", "diffuse", -300)
normal = sample("NormalMap", "normal_dx", -40)
arm = sample("ARMMap", "arm", 220)
for node, pin, prop in (
    (albedo, "RGB", unreal.MaterialProperty.MP_BASE_COLOR),
    (normal, "RGB", unreal.MaterialProperty.MP_NORMAL),
    (arm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
    (arm, "G", unreal.MaterialProperty.MP_ROUGHNESS),
    (arm, "B", unreal.MaterialProperty.MP_METALLIC),
):
    if not lib.connect_material_property(node, pin, prop):
        raise RuntimeError(f"Torii-foot scanned PBR graph failed: {prop}")
lib.layout_material_expressions(material)
lib.recompile_material(material)
assets.save_loaded_asset(material)
if {str(x) for x in lib.get_texture_parameter_names(material)} != {"AlbedoMap", "NormalMap", "ARMMap"}:
    raise RuntimeError("Torii-foot material PBR pins changed")

instance_name = "MI_ToriiFoot_MossyRock_CC0"
path = f"{mat_dest}/{instance_name}"
instance = (assets.load_asset(path) if assets.does_asset_exist(path)
            else tools.create_asset(instance_name, mat_dest, unreal.MaterialInstanceConstant,
                                    unreal.MaterialInstanceConstantFactoryNew()))
lib.set_material_instance_parent(instance, material)
for parameter, channel in (("AlbedoMap", "diffuse"), ("NormalMap", "normal_dx"), ("ARMMap", "arm")):
    expected = textures[channel]
    lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
    actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
    if actual is None or actual.get_path_name() != expected.get_path_name():
        raise RuntimeError(f"Torii-foot exact scan binding failed: {parameter}")
assets.save_loaded_asset(instance)

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
mesh_name = "SM_Nyaagyu_ToriiFoot_Study"
mesh = imported(source / record["fbx"], mesh_dest, mesh_name, options)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Torii-foot FBX did not import as StaticMesh")
slots = [str(slot.get_editor_property("material_slot_name")) for slot in mesh.get_editor_property("static_materials")]
if slots != record["material_slots"]:
    raise RuntimeError(f"Torii-foot FBX material slot changed: {slots}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if subsystem.get_lod_count(mesh) < 1 or subsystem.get_number_verts(mesh, 0) < 4000:
    raise RuntimeError("Torii-foot mesh did not build enough review geometry")
nanite = subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Torii-foot Nanite source data not built")
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh, nanite, True)
nanite = subsystem.get_nanite_settings(mesh)
if (nanite.get_editor_property("fallback_percent_triangles") < .999
        or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED):
    raise RuntimeError("Torii-foot Mac conventional fallback changed")
mesh.set_material(0, instance)
if mesh.get_material(0).get_path_name() != instance.get_path_name():
    raise RuntimeError("Torii-foot scan material was not bound to the mesh")
assets.save_loaded_asset(mesh)
assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log("NYAAGYU_TORII_FOOT_ART_REVIEW_READY: pinned CC0 scan, complete PBR, Nanite source, full Mac fallback; no WorldBuilder placement")
