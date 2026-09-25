"""Strict pinned-UE, isolated Fern 02 material/mesh art review import.

Assets are written exclusively under /Game/Generated/ArtReview/Fern02.
Nothing is placed in a map or added to gameplay collision/WorldBuilder.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Fern 02 art review")

root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/PolyHaven/Fern02"
manifest_path = source / "manifest.json"
EXPECTED_MANIFEST_SHA256 = "7aefb46c2c3b8134ae16bf64e4443840ea8617b57acee893ca22485ab07b6239"


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


if sha(manifest_path) != EXPECTED_MANIFEST_SHA256:
    raise RuntimeError("Fern 02 art-review source manifest changed")
record = json.loads(manifest_path.read_text())
if (record["schema_version"] != 1
        or record["asset_id"] != "fern_02"
        or record["upstream_page"] != "https://polyhaven.com/a/fern_02"
        or record["license"] != "CC0-1.0; https://polyhaven.com/license"
        or record["generator"] != "scripts/art/create_nyaagyu_fern_shoulder.py"
        or record["gameplay_collision"] is not False
        or len(record["meshes"]) != 8
        or len(record["upstream_files"]) != 12):
    raise RuntimeError("Fern 02 art-review identity changed")
for item in record["upstream_files"]:
    path = source / item["path"]
    if (not path.is_file() or path.stat().st_size != item["bytes"]
            or sha(path) != item["sha256"]
            or not item["official_url"].startswith("https://dl.polyhaven.org/file/ph-assets/Models/")):
        raise RuntimeError(f"Fern 02 pinned scan changed: {path}")
for key, digest in (("source_blend", "source_blend_sha256"),
                    ("preview", "preview_sha256"),
                    ("mac_fallback_preview", "mac_fallback_preview_sha256")):
    if sha(source / record[key]) != record[digest]:
        raise RuntimeError(f"Fern 02 source review changed: {key}")

mesh_records = {(item["variant"], item["tier"]): item for item in record["meshes"]}
if set(mesh_records) != {(letter, tier) for letter in "abcd" for tier in ("hi", "mac_lod1")}:
    raise RuntimeError("Fern 02 four-variant/full-Mac-LOD set changed")
if (sum(mesh_records[(letter, "hi")]["triangles"] for letter in "abcd") != 6232
        or sum(mesh_records[(letter, "mac_lod1")]["triangles"] for letter in "abcd") != 3301):
    raise RuntimeError("Fern 02 scanned or conventional geometry changed")
for (letter, tier), item in mesh_records.items():
    name = f"SM_NyaagyuFern02_{letter.upper()}_{'HI' if tier == 'hi' else 'MAC_LOD1'}"
    file = source / item["fbx"]
    if (item["fbx"] != name + ".fbx"
            or item["material_slot"] != ("M_NyaagyuFern02_4K" if tier == "hi" else "M_NyaagyuFern02_2K")
            or item["nanite_candidate"] != (tier == "hi")
            or sha(file) != item["fbx_sha256"]):
        raise RuntimeError(f"Fern 02 mesh identity changed: {name}")

mac_config = (root / "Config/Mac/MacEngine.ini").read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Fern 02 Mac conventional render policy changed")

dest = "/Game/Generated/ArtReview/Fern02"
tex_dest = dest + "/Textures"
mesh_dest = dest + "/Meshes"
mat_dest = dest + "/Materials"
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
for folder in (dest, tex_dest, mesh_dest, mat_dest):
    assets.make_directory(folder)


def import_file(file: Path, folder: str, name: str, options=None):
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
    asset = assets.load_asset(f"{folder}/{name}")
    if not asset:
        raise RuntimeError(f"Fern 02 Unreal import failed: {file}")
    return asset


file_by_name = {Path(item["path"]).name: item for item in record["upstream_files"]}
textures = {}
for tier in ("4k", "2k"):
    for role in ("diff", "arm", "nor_dx", "alpha"):
        ext = "png" if role == "alpha" else "jpg"
        file_name = f"fern_02_{role}_{tier}.{ext}"
        item = file_by_name[file_name]
        file = source / item["path"]
        name = f"T_Fern02_{tier.upper()}_{role.upper()}"
        texture = import_file(file, tex_dest, name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Fern 02 texture is not Texture2D: {name}")
        texture.set_editor_property("srgb", role == "diff")
        if role == "nor_dx":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif role in ("arm", "alpha"):
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", 4096 if tier == "4k" else 2048)
        assets.save_loaded_asset(texture)
        textures[(tier, role)] = texture

# One two-sided, masked, scanned-PBR shader. Never infer opacity from the
# glTF's JPEG base color: the official separately pinned alpha is mandatory.
master_name = "M_Fern02_ScannedMasked"
master_path = f"{mat_dest}/{master_name}"
master = (assets.load_asset(master_path) if assets.does_asset_exist(master_path)
          else tools.create_asset(master_name, mat_dest, unreal.Material, unreal.MaterialFactoryNew()))
for expression in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, expression)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Fern 02 material retained stale expressions")
master.set_editor_property("two_sided", True)
master.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
master.set_editor_property("opacity_mask_clip_value", .5)
master.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)


def sample(parameter: str, role: str, y: int):
    node = lib.create_material_expression(master, unreal.MaterialExpressionTextureSampleParameter2D, -650, y)
    node.set_editor_property("parameter_name", parameter)
    node.set_editor_property("texture", textures[("4k", role)])
    return node


albedo = sample("AlbedoMap", "diff", -350)
normal = sample("NormalMap", "nor_dx", -80)
arm = sample("ARMMap", "arm", 210)
alpha = sample("AlphaMap", "alpha", 480)
for node, pin, output in (
    (albedo, "RGB", unreal.MaterialProperty.MP_BASE_COLOR),
    (normal, "RGB", unreal.MaterialProperty.MP_NORMAL),
    (arm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
    (arm, "G", unreal.MaterialProperty.MP_ROUGHNESS),
    (arm, "B", unreal.MaterialProperty.MP_METALLIC),
    (alpha, "R", unreal.MaterialProperty.MP_OPACITY_MASK),
    (albedo, "RGB", unreal.MaterialProperty.MP_SUBSURFACE_COLOR),
):
    if not lib.connect_material_property(node, pin, output):
        raise RuntimeError(f"Fern 02 material output failed: {output}")
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(name) for name in lib.get_texture_parameter_names(master)} != {
        "AlbedoMap", "NormalMap", "ARMMap", "AlphaMap"}:
    raise RuntimeError("Fern 02 material texture pins changed")

instances = {}
for tier in ("4k", "2k"):
    name = f"MI_Fern02_{tier.upper()}"
    path = f"{mat_dest}/{name}"
    instance = (assets.load_asset(path) if assets.does_asset_exist(path)
                else tools.create_asset(name, mat_dest,
                                        unreal.MaterialInstanceConstant,
                                        unreal.MaterialInstanceConstantFactoryNew()))
    lib.set_material_instance_parent(instance, master)
    for parameter, role in (("AlbedoMap", "diff"), ("NormalMap", "nor_dx"),
                            ("ARMMap", "arm"), ("AlphaMap", "alpha")):
        expected = textures[(tier, role)]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        actual = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not actual or actual.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Fern 02 exact texture binding failed: {name}/{parameter}")
    assets.save_loaded_asset(instance)
    instances[tier] = instance

subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for (letter, tier), item in mesh_records.items():
    name = Path(item["fbx"]).stem
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.set_editor_property("build_nanite", tier == "hi")
    mesh = import_file(source / item["fbx"], mesh_dest, name, options)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Fern 02 static mesh is missing: {name}")
    slots = [str(slot.get_editor_property("material_slot_name"))
             for slot in mesh.get_editor_property("static_materials")]
    if slots != [item["material_slot"]]:
        raise RuntimeError(f"Fern 02 FBX material identity changed: {name}: {slots}")
    if subsystem.get_lod_count(mesh) < 1 or subsystem.get_number_verts(mesh, 0) < 150:
        raise RuntimeError(f"Fern 02 FBX geometry failed to build: {name}")
    nanite = subsystem.get_nanite_settings(mesh)
    if bool(nanite.get_editor_property("enabled")) != (tier == "hi"):
        raise RuntimeError(f"Fern 02 Nanite tier mismatch: {name}")
    if tier == "hi":
        nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
        nanite.set_editor_property("fallback_percent_triangles", 1.0)
        nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
        subsystem.set_nanite_settings(mesh, nanite, True)
        nanite = subsystem.get_nanite_settings(mesh)
        if (nanite.get_editor_property("fallback_target") != unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
                or nanite.get_editor_property("fallback_percent_triangles") < .999
                or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED):
            raise RuntimeError(f"Fern 02 full conventional fallback was lost: {name}")
    expected_material = instances["4k" if tier == "hi" else "2k"]
    mesh.set_material(0, expected_material)
    if mesh.get_material(0).get_path_name() != expected_material.get_path_name():
        raise RuntimeError(f"Fern 02 exact material assignment failed: {name}")
    assets.save_loaded_asset(mesh)

assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
unreal.log("NYAAGYU_FERN02_ART_REVIEW_READY: four 4K masked/Nanite scans; four 2K conventional Mac LOD1 variants; no WorldBuilder placement")
