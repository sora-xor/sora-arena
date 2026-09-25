"""Import the visual-only Nyaagyu dojo bokken PBR study into the pinned UE.

The candidate lives solely under /Game/Generated/ArtReview/DojoBokkenPBR.
It never replaces the playable /Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.
Run the independent Blender source/FBX validator before invoking this importer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


DESTINATION = "/Game/Generated/ArtReview/DojoBokkenPBR"
MESH_NAME = "SM_Nyaagyu_DojoBokken_PBRStudy"
SLOTS = {
    "M_Bokken_SeasonedWhiteOak": (.90, .86, .80),
    "M_Bokken_HandOiledGrip": (.64, .56, .46),
    "M_Bokken_EndGrain": (.70, .60, .49),
    "M_Bokken_QuietWoodGrain": (.36, .29, .23),
}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Dojo bokken ArtReview")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Weapons/DojoBokkenPBR"
original = root / "Content/SourceArt/Weapons/Original"
record = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
texture_record = json.loads((source / "texture_manifest.json").read_text(encoding="utf-8"))
original_record = json.loads((original / "manifest.json").read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_file(path: Path, expected: str) -> None:
    if not path.is_file() or sha(path) != expected:
        raise RuntimeError(f"Dojo bokken source hash mismatch: {path}")


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(26)
    if (len(header) != 26 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR" or header[24] != 8
            or header[25] != 2):
        raise RuntimeError(f"Dojo bokken texture is not an 8-bit RGB PNG: {path}")
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


if (record["schema_version"] != texture_record["schema_version"]
        or record["schema_version"] != 1
        or record["generator"] != "scripts/art/create_dojo_bokken_pbr_study.py"
        or record["source_parts"] != 16
        or record["source_triangles"] != 8208
        or record["material_slots"] != sorted(SLOTS)
        or record["unreal_asset"] != f"{DESTINATION}/{MESH_NAME}.{MESH_NAME}"
        or "No gameplay promotion" not in record["scope"]):
    raise RuntimeError("Dojo bokken study identity, geometry, or scope changed")
if (original_record["name"] != "SM_Nyaagyu_DojoBokken"
        or original_record["blend_sha256"] != record["base_blend_sha256"]
        or original_record["fbx_sha256"] != record["base_fbx_sha256"]):
    raise RuntimeError("Dojo bokken study no longer derives from the pinned combat source")
for path, expected in (
    (original / original_record["source_blend"], record["base_blend_sha256"]),
    (original / original_record["fbx"], record["base_fbx_sha256"]),
    (source / "texture_manifest.json", record["texture_manifest_sha256"]),
    (source / record["source_blend"], record["blend_sha256"]),
    (source / record["fbx"], record["fbx_sha256"]),
    (source / record["preview"], record["preview_sha256"]),
    (source / texture_record["source"], texture_record["source_sha256"]),
):
    exact_file(path, expected)
if (texture_record["generator"] != "scripts/art/create_dojo_bokken_pbr_textures.py"
        or set(texture_record["maps"]) != {"Albedo", "NormalDX", "ORM"}
        or not texture_record["source_rights"].startswith("Project-generated")
        or not texture_record.get("source_prompt")
        or not texture_record.get("source_output_id")
        or "not measured" not in texture_record["limitations"]):
    raise RuntimeError("Dojo bokken texture provenance or PBR channel set changed")
for role, item in texture_record["maps"].items():
    path = source / item["file"]
    exact_file(path, item["sha256"])
    if item["resolution"] != [2048, 2048] or png_size(path) != (2048, 2048):
        raise RuntimeError(f"Dojo bokken texture resolution changed: {role}")
fbx_bytes = (source / record["fbx"]).read_bytes()
if (not fbx_bytes.startswith(b"Kaydara FBX Binary") or b"/Users/" in fbx_bytes
        or b"UV0" not in fbx_bytes):
    raise RuntimeError("Dojo bokken FBX header, portability, or UV0 declaration changed")
for runtime_file in sorted((root / "Source/SoraArena").rglob("*.cpp")):
    if MESH_NAME in runtime_file.read_text():
        raise RuntimeError(f"Review-only bokken candidate unexpectedly appears in {runtime_file.name}")

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
texture_dir = DESTINATION + "/Textures"
material_dir = DESTINATION + "/Materials"
for path in (DESTINATION, texture_dir, material_dir):
    assets.make_directory(path)


def import_asset(file: Path, folder: str, name: str, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    result = assets.load_asset(folder + "/" + name)
    if not result:
        raise RuntimeError(f"Dojo bokken ArtReview import failed: {file}")
    return result


textures = {}
for role in ("Albedo", "NormalDX", "ORM"):
    file = source / texture_record["maps"][role]["file"]
    name = file.stem
    texture = import_asset(file, texture_dir, name)
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError(f"Dojo bokken {role} did not import as Texture2D")
    texture.set_editor_property("srgb", role == "Albedo")
    if role == "NormalDX":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif role == "ORM":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property("max_texture_size", 2048)
    assets.save_loaded_asset(texture)
    textures[role] = texture


def node(material, expression_type, x, y, **properties):
    expression = lib.create_material_expression(material, expression_type, x, y)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression


def link(source_node, output_pin, target_node, input_pin):
    if not lib.connect_material_expressions(source_node, output_pin, target_node, input_pin):
        raise RuntimeError(f"Dojo bokken PBR node link failed: {output_pin} -> {input_pin}")


def output(expression, pin, material_property):
    if not lib.connect_material_property(expression, pin, material_property):
        raise RuntimeError(f"Dojo bokken PBR output failed: {material_property}")


master_name = "M_DojoBokkenPBR_Master"
master_path = material_dir + "/" + master_name
master = (assets.load_asset(master_path) if assets.does_asset_exist(master_path)
          else tools.create_asset(master_name, material_dir, unreal.Material,
                                  unreal.MaterialFactoryNew()))
for old in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Dojo bokken PBR master retained stale expressions")
albedo = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -400,
              parameter_name="AlbedoMap", texture=textures["Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -50,
              parameter_name="NormalMap", texture=textures["NormalDX"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, 280,
           parameter_name="ORMMap", texture=textures["ORM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -560, -580,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
colored = node(master, unreal.MaterialExpressionMultiply, -250, -320)
link(albedo, "RGB", colored, "A")
link(tint, "RGB", colored, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
output(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
output(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
output(orm, "B", unreal.MaterialProperty.MP_METALLIC)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(name) for name in lib.get_texture_parameter_names(master)} != {
        "AlbedoMap", "NormalMap", "ORMMap"}:
    raise RuntimeError("Dojo bokken PBR master lost a texture parameter")

instances = {}
for slot_name, color in SLOTS.items():
    name = "MI_DojoBokkenPBR_" + slot_name.removeprefix("M_Bokken_")
    path = material_dir + "/" + name
    instance = (assets.load_asset(path) if assets.does_asset_exist(path)
                else tools.create_asset(name, material_dir,
                                        unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew()))
    lib.set_material_instance_parent(instance, master)
    for parameter, role in (("AlbedoMap", "Albedo"),
                            ("NormalMap", "NormalDX"),
                            ("ORMMap", "ORM")):
        lib.set_material_instance_texture_parameter_value(instance, parameter, textures[role])
        actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not actual or actual.get_path_name() != textures[role].get_path_name():
            raise RuntimeError(f"Dojo bokken {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(
        instance, "Tint", unreal.LinearColor(*color, 1))
    actual_tint = lib.get_material_instance_vector_parameter_value(instance, "Tint")
    if any(abs(a - b) > .0001 for a, b in zip((actual_tint.r, actual_tint.g,
                                                 actual_tint.b), color)):
        raise RuntimeError(f"Dojo bokken {name} lost its authored tint")
    assets.save_loaded_asset(instance)
    instances[slot_name] = instance

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
mesh = import_asset(source / record["fbx"], DESTINATION, MESH_NAME, options)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Dojo bokken candidate did not import as StaticMesh")
if mesh.get_num_tex_coords(0) != 1:
    raise RuntimeError("Dojo bokken imported UV0 contract changed")
actual_slots = [str(slot.get_editor_property("material_slot_name"))
                for slot in mesh.get_editor_property("static_materials")]
if len(actual_slots) != 4 or set(actual_slots) != set(SLOTS):
    raise RuntimeError(f"Dojo bokken imported material slots changed: {actual_slots}")
for index, slot_name in enumerate(actual_slots):
    mesh.set_material(index, instances[slot_name])
    if mesh.get_material(index).get_path_name() != instances[slot_name].get_path_name():
        raise RuntimeError(f"Dojo bokken material assignment failed: {slot_name}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Dojo bokken candidate lost its Nanite source")
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh, nanite, True)
if subsystem.get_nanite_settings(mesh).get_editor_property("fallback_percent_triangles") < .999:
    raise RuntimeError("Dojo bokken full conventional fallback was reduced")
if mesh.get_num_triangles(0) != record["source_triangles"]:
    raise RuntimeError("Dojo bokken full fallback triangle count changed")
assets.save_loaded_asset(mesh)
assets.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True)
unreal.log("DOJO_BOKKEN_PBR_ART_REVIEW_READY: 8208 triangles, UV0, four PBR instances, source-only")
