"""Import the source-only scanned-oak bokuto form into pinned-UE ArtReview.

Run the independent Blender source/FBX validator first. This script creates
only /Game/Generated/ArtReview/DojoBokutoForm assets and never replaces the
playable /Game/Generated/Meshes/SM_Nyaagyu_DojoBokken.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import unreal


DESTINATION = "/Game/Generated/ArtReview/DojoBokutoForm"
MESH_NAME = "SM_Nyaagyu_BokutoForm"
SURFACES = {
    "M_Bokuto_PhotographedWhiteOak": ("Oak", (.66, .60, .52), 1.00),
    "M_Bokuto_HandOiledOakGrip": ("Oak", (.50, .42, .33), .83),
    "M_Bokuto_DarkLeatherTsuba": ("Leather", (.27, .20, .15), 1.07),
}

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Bokuto ArtReview")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Weapons/DojoBokutoForm"
leather_source = root / "Content/SourceArt/Weapons/NyaagyuYumi"
record = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
oak_record = json.loads((source / "texture_manifest.json").read_text(encoding="utf-8"))
leather_record = json.loads((leather_source / "manifest.json").read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_file(path: Path, expected: str, within: Path) -> None:
    if not path.resolve().is_relative_to(within.resolve()):
        raise RuntimeError(f"Bokuto source escaped its pinned directory: {path}")
    if not path.is_file() or sha(path) != expected:
        raise RuntimeError(f"Bokuto source hash mismatch: {path}")


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        return (int.from_bytes(data[16:20], "big"),
                int.from_bytes(data[20:24], "big"))
    if not data.startswith(b"\xff\xd8"):
        raise RuntimeError(f"Bokuto texture is not PNG or JPEG: {path}")
    index = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while index + 3 < len(data):
        if data[index] != 0xFF:
            raise RuntimeError(f"Bokuto JPEG marker stream changed: {path}")
        while data[index] == 0xFF:
            index += 1
        marker = data[index]
        index += 1
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            raise RuntimeError(f"Bokuto JPEG segment changed: {path}")
        if marker in sof:
            return (int.from_bytes(data[index + 5:index + 7], "big"),
                    int.from_bytes(data[index + 3:index + 5], "big"))
        index += segment_length
    raise RuntimeError(f"Bokuto JPEG has no size marker: {path}")


expected_materials = Counter({
    "M_Bokuto_HandOiledOakGrip": 1,
    "M_Bokuto_PhotographedWhiteOak": 1,
    "M_Bokuto_DarkLeatherTsuba": 2,
})
if (record["schema_version"] != 1
        or record["name"] != MESH_NAME
        or record["generator"] != "scripts/art/create_dojo_bokuto_form_study.py"
        or record["parts"] != 4 or record["triangles"] != 5332
        or Counter(record["materials"]) != expected_materials
        or record["bounds_m"] != {"min_x": -.242, "max_x": .773}
        or record["dimensions_cm"] != {"total": 101.5, "grip": 24.2, "sori": 1.5}
        or record["proportion_reference"] !=
        "https://www.kendo.or.jp/wp/wp-content/uploads/2023/07/jodo-shiai_regulations.pdf"
        or not record["scope"].startswith("Source-only modern jodo-proportioned")):
    raise RuntimeError("Bokuto form source identity, geometry, or review scope changed")
for file_field, hash_field in (
        ("source_blend", "blend_sha256"), ("fbx", "fbx_sha256"),
        ("preview", "preview_sha256"),
        ("detail_preview", "detail_preview_sha256")):
    exact_file(source / record[file_field], record[hash_field], source)
exact_file(source / "texture_manifest.json",
           record["source_texture_manifest_sha256"], source)
exact_file(leather_source / "manifest.json",
           record["leather_source_manifest_sha256"], leather_source)
if (oak_record["schema_version"] != 1
        or oak_record["asset_id"] != "white_oak_veneer"
        or oak_record["source_url"] != "https://polyhaven.com/a/white_oak_veneer"
        or oak_record["license"] != "CC0-1.0"
        or oak_record["license_url"] != "https://polyhaven.com/license"
        or oak_record["resolution"] != [2048, 2048]
        or set(oak_record["maps"]) != {"Albedo", "NormalDX", "ARM"}
        or leather_record["texture_license"] != "CC0-1.0"
        or "https://polyhaven.com/a/brown_leather" not in
        leather_record["texture_sources"]):
    raise RuntimeError("Bokuto scanned texture rights or channel contract changed")
leather_maps = {item["channel"]: item for item in leather_record["textures"]
                if item["surface"] == "leather"}
if set(leather_maps) != {"Albedo", "NormalDX", "ARM"}:
    raise RuntimeError("Bokuto leather texture channels changed")

texture_files = {}
for surface_name, manifest, folder in (
        ("Oak", oak_record["maps"], source),
        ("Leather", leather_maps, leather_source)):
    for role in ("Albedo", "NormalDX", "ARM"):
        item = manifest[role]
        path = folder / item["file"]
        exact_file(path, item["sha256"], folder)
        if image_dimensions(path) != (2048, 2048):
            raise RuntimeError(f"Bokuto {surface_name} {role} size changed")
        texture_files[surface_name, role] = path

fbx_bytes = (source / record["fbx"]).read_bytes()
if (not fbx_bytes.startswith(b"Kaydara FBX Binary") or b"UV0" not in fbx_bytes
        or b"/Users/" in fbx_bytes):
    raise RuntimeError("Bokuto FBX header, UV0, or portability contract changed")
for runtime_file in sorted((root / "Source/SoraArena").rglob("*.cpp")):
    if MESH_NAME in runtime_file.read_text():
        raise RuntimeError(f"Review-only bokuto appears in {runtime_file.name}")

assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
texture_dir = DESTINATION + "/Textures"
material_dir = DESTINATION + "/Materials"
for directory in (DESTINATION, texture_dir, material_dir):
    assets.make_directory(directory)


def import_asset(path: Path, folder: str, name: str, options=None):
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
    result = assets.load_asset(folder + "/" + name)
    if not result:
        raise RuntimeError(f"Bokuto ArtReview import failed: {path}")
    return result


textures = {}
for surface_name in ("Oak", "Leather"):
    for role in ("Albedo", "NormalDX", "ARM"):
        name = f"T_BokutoForm_{surface_name}_{role}"
        texture = import_asset(texture_files[surface_name, role], texture_dir, name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Bokuto {surface_name} {role} is not Texture2D")
        texture.set_editor_property("srgb", role == "Albedo")
        if role == "NormalDX":
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif role == "ARM":
            texture.set_editor_property(
                "compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(texture)
        textures[surface_name, role] = texture


def node(material, expression_type, x, y, **properties):
    expression = lib.create_material_expression(material, expression_type, x, y)
    for name, value in properties.items():
        expression.set_editor_property(name, value)
    return expression


def link(source_node, output_pin, target_node, input_pin):
    if not lib.connect_material_expressions(source_node, output_pin,
                                            target_node, input_pin):
        raise RuntimeError(f"Bokuto PBR link failed: {output_pin} -> {input_pin}")


def output(expression, pin, material_property):
    if not lib.connect_material_property(expression, pin, material_property):
        raise RuntimeError(f"Bokuto PBR output failed: {material_property}")


master_name = "M_DojoBokutoFormPBR_Master"
master_path = material_dir + "/" + master_name
master = (assets.load_asset(master_path) if assets.does_asset_exist(master_path)
          else tools.create_asset(master_name, material_dir, unreal.Material,
                                  unreal.MaterialFactoryNew()))
for old in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Bokuto master retained stale expressions")
albedo = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -400,
              parameter_name="AlbedoMap", texture=textures["Oak", "Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, -50,
              parameter_name="NormalMap", texture=textures["Oak", "NormalDX"])
arm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -850, 280,
           parameter_name="ARMMap", texture=textures["Oak", "ARM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -560, -580,
            parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
rough_scale = node(master, unreal.MaterialExpressionScalarParameter, -560, 460,
                   parameter_name="RoughnessScale", default_value=1.0)
colored = node(master, unreal.MaterialExpressionMultiply, -250, -320)
roughened = node(master, unreal.MaterialExpressionMultiply, -250, 280)
link(albedo, "RGB", colored, "A")
link(tint, "RGB", colored, "B")
link(arm, "G", roughened, "A")
link(rough_scale, "", roughened, "B")
output(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
output(arm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
output(roughened, "", unreal.MaterialProperty.MP_ROUGHNESS)
output(arm, "B", unreal.MaterialProperty.MP_METALLIC)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(name) for name in lib.get_texture_parameter_names(master)} != {
        "AlbedoMap", "NormalMap", "ARMMap"}:
    raise RuntimeError("Bokuto master lost a texture parameter")

instances = {}
for slot_name, (surface_name, color, roughness_scale) in SURFACES.items():
    name = "MI_DojoBokutoForm_" + slot_name.removeprefix("M_Bokuto_")
    path = material_dir + "/" + name
    instance = (assets.load_asset(path) if assets.does_asset_exist(path)
                else tools.create_asset(name, material_dir,
                                        unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew()))
    lib.set_material_instance_parent(instance, master)
    for parameter, role in (("AlbedoMap", "Albedo"),
                            ("NormalMap", "NormalDX"),
                            ("ARMMap", "ARM")):
        texture = textures[surface_name, role]
        lib.set_material_instance_texture_parameter_value(instance, parameter, texture)
        actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not actual or actual.get_path_name() != texture.get_path_name():
            raise RuntimeError(f"Bokuto {name} lost its {parameter} binding")
    lib.set_material_instance_vector_parameter_value(
        instance, "Tint", unreal.LinearColor(*color, 1))
    actual_tint = lib.get_material_instance_vector_parameter_value(instance, "Tint")
    if any(abs(a - b) > .0001 for a, b in zip(
            (actual_tint.r, actual_tint.g, actual_tint.b), color)):
        raise RuntimeError(f"Bokuto {name} lost its authored tint")
    lib.set_material_instance_scalar_parameter_value(instance, "RoughnessScale",
                                                     roughness_scale)
    if abs(lib.get_material_instance_scalar_parameter_value(
            instance, "RoughnessScale") - roughness_scale) > .0001:
        raise RuntimeError(f"Bokuto {name} lost its roughness scale")
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
    raise RuntimeError("Bokuto review candidate did not import as StaticMesh")
if mesh.get_num_tex_coords(0) != 1:
    raise RuntimeError("Bokuto imported UV0 contract changed")
actual_slots = [str(slot.get_editor_property("material_slot_name"))
                for slot in mesh.get_editor_property("static_materials")]
if len(actual_slots) != 3 or set(actual_slots) != set(SURFACES):
    raise RuntimeError(f"Bokuto imported material slots changed: {actual_slots}")
for index, slot_name in enumerate(actual_slots):
    mesh.set_material(index, instances[slot_name])
    if mesh.get_material(index).get_path_name() != instances[slot_name].get_path_name():
        raise RuntimeError(f"Bokuto material assignment failed: {slot_name}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Bokuto candidate lost its Nanite source")
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh, nanite, True)
if subsystem.get_nanite_settings(mesh).get_editor_property("fallback_percent_triangles") < .999:
    raise RuntimeError("Bokuto full conventional fallback was reduced")
if mesh.get_num_triangles(0) != record["triangles"]:
    raise RuntimeError("Bokuto full fallback triangle count changed")
assets.save_loaded_asset(mesh)
assets.save_directory(DESTINATION, only_if_is_dirty=False, recursive=True)
unreal.log("DOJO_BOKUTO_FORM_ART_REVIEW_READY: 5332 triangles, UV0, three PBR instances, source-only")
