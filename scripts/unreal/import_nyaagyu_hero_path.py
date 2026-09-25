"""Standalone pinned-UE import of the six-metre Estate hero path insert.

Run from the pinned editor:
  UnrealEditor-Cmd SoraArena.uproject \
    -ExecutePythonScript=scripts/unreal/import_nyaagyu_hero_path.py

The existing mesh terrain keeps gameplay collision. This import creates only
visual geometry, scanned PBR materials, and a full conventional Mac fallback.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaagyu hero path")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuHeroPath"
record = json.loads((source / "manifest.json").read_text())
name = "SM_Nyaagyu_HeroStonePath_6m"
prop_path = "/Game/Generated/Environment/Props"
dest = "/Game/Generated/Environment/HeroPath"
expected_slots = {"M_HeroPath_StoneFace", "M_HeroPath_StoneEdge", "M_HeroPath_SiltBed"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if (record["schema_version"] != 1 or record["name"] != name
        or record["generator"] != "scripts/art/create_nyaagyu_hero_path.py"
        or record["generator_sha256"] != sha(root / record["generator"])
        or record["unreal_asset"] != f"{prop_path}/{name}.{name}"
        or record["nominal_road_length_m"] != 6.0
        or record["individual_stones"] < 60
        or record["source_triangles"] < 20000
        or record["source_parts"] != record["individual_stones"] + 1
        or set(record["material_slots"]) != expected_slots
        or record["material_sources"] != {
            "M_HeroPath_StoneFace": "FaceAtlas", "M_HeroPath_StoneEdge": "Mineral",
            "M_HeroPath_SiltBed": "Silt"}
        or not record["collision"].startswith("Presentation only")
        or record["nanite_windows"] is not True
        or record["mac_conventional_fallback"] != {
            "source_fbx": name + ".fbx", "fallback_percent_triangles": 1.0,
            "fallback_target": "PercentTriangles", "generate_fallback": "Enabled",
            "render_config": "Config/Mac/MacEngine.ini"}
        or sha(source / record["fbx"]) != record["fbx_sha256"]):
    raise RuntimeError("Hero path identity, geometry, or collision policy changed")
mac_config = (root / "Config/Mac/MacEngine.ini").read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Hero path Mac conventional fallback is not configured")
bounds = record["bounds_m"]
if (bounds["min"][0] < -3.01 or bounds["max"][0] > 3.01
        or bounds["min"][1] < -1.46 or bounds["max"][1] > 1.46
        or bounds["min"][2] < -.002 or bounds["max"][2] > .065):
    raise RuntimeError("Hero path escaped its 6 m by 2.9 m visual envelope")
if set(record["dependencies"]) != {"FaceAtlas", "Mineral", "Silt"}:
    raise RuntimeError("Hero path scan dependency set changed")
atlas_manifest_path = source / "atlas_manifest.json"
if record["atlas_manifest_sha256"] != sha(atlas_manifest_path):
    raise RuntimeError("Hero path derived texture atlas changed")
atlas_manifest = json.loads(atlas_manifest_path.read_text())
if (atlas_manifest["source_asset"] != "grey_stone_path"
        or atlas_manifest["source_license"] != "CC0-1.0"
        or atlas_manifest["count"] != record["individual_stones"]
        or atlas_manifest["generator_sha256"] != sha(root / atlas_manifest["generator"])):
    raise RuntimeError("Hero path atlas origin or generator changed")
for item in atlas_manifest["source_files"].values():
    path = (root / item["repo_path"]).resolve()
    if (not path.is_relative_to(root / "Content/SourceArt/Environment/NyaagyuTerrain/GreyStonePath")
            or sha(path) != item["sha256"]):
        raise RuntimeError("Hero path atlas lost its pinned source scan")

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
assets.make_directory(dest)
assets.make_directory(dest + "/Textures")
assets.make_directory(prop_path)
textures = {}
allowed_sources = (
    (root / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01").resolve(),
    (root / "Content/SourceArt/Environment/PolyHaven").resolve(),
    source.resolve(),
)
for surface, dependency in record["dependencies"].items():
    if (dependency["license"] != "CC0-1.0"
            or not dependency["source_url"].startswith("https://polyhaven.com/a/")
            or set(dependency["files"]) != {"Albedo", "NormalDX", "ORM"}):
        raise RuntimeError(f"Hero path scan provenance changed: {surface}")
    textures[surface] = {}
    for channel, item in dependency["files"].items():
        path = (root / item["repo_path"]).resolve()
        derived = surface == "FaceAtlas"
        origin_ok = (item.get("derived_from") == "Content/SourceArt/Environment/NyaagyuTerrain/manifest.json"
                     and path.is_relative_to(source.resolve())
                     and atlas_manifest["outputs"][{"Albedo":"Diffuse", "NormalDX":"nor_dx", "ORM":"arm"}[channel]]["sha256"] == item["sha256"]) if derived else item.get("upstream_url", "").startswith("https://dl.polyhaven.org/")
        if (not any(path.is_relative_to(folder) for folder in allowed_sources)
                or not origin_ok or sha(path) != item["sha256"]):
            raise RuntimeError(f"Hero path source texture changed: {path}")
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest + "/Textures"
        task.destination_name = "T_HeroPath_" + surface + "_" + channel
        task.automated = True
        task.replace_existing = True
        task.save = True
        asset_tools.import_asset_tasks([task])
        texture = assets.load_asset(task.destination_path + "/" + task.destination_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Hero path texture import failed: {path}")
        texture.set_editor_property("srgb", channel == "Albedo")
        if channel == "NormalDX":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        elif channel == "ORM":
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(texture)
        textures[surface][channel] = texture


def node(material, cls, x, y, **properties):
    expression = lib.create_material_expression(material, cls, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(left, out, right, pin):
    if not lib.connect_material_expressions(left, out, right, pin):
        raise RuntimeError(f"Hero path material link failed: {out}->{pin}")


def output(expression, out, prop):
    if not lib.connect_material_property(expression, out, prop):
        raise RuntimeError(f"Hero path material output failed: {prop}")


def master(name, feathered):
    path = dest + "/" + name
    material = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        name, dest, unreal.Material, unreal.MaterialFactoryNew())
    for old_expression in list(lib.get_material_expressions(material)):
        lib.delete_material_expression(material, old_expression)
    if lib.get_num_material_expressions(material):
        raise RuntimeError(f"Hero path material {name} retained expressions from its prior import")
    material.set_editor_property("two_sided", feathered)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if feathered else unreal.BlendMode.BLEND_OPAQUE)
    base = node(material, unreal.MaterialExpressionTextureSampleParameter2D, -1000, -350,
                parameter_name="AlbedoMap", texture=textures["Mineral"]["Albedo"])
    normal = node(material, unreal.MaterialExpressionTextureSampleParameter2D, -1000, -60,
                  parameter_name="NormalMap", texture=textures["Mineral"]["NormalDX"])
    orm = node(material, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 250,
               parameter_name="ORMMap", texture=textures["Mineral"]["ORM"])
    vertex = node(material, unreal.MaterialExpressionVertexColor, -670, -610)
    tint = node(material, unreal.MaterialExpressionVectorParameter, -670, -430,
                parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    mul_v = node(material, unreal.MaterialExpressionMultiply, -360, -350)
    link(base, "RGB", mul_v, "A")
    link(vertex, "RGB", mul_v, "B")
    mul_t = node(material, unreal.MaterialExpressionMultiply, -120, -350)
    link(mul_v, "", mul_t, "A")
    link(tint, "RGB", mul_t, "B")
    output(mul_t, "", unreal.MaterialProperty.MP_BASE_COLOR)
    output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
    for axis, prop, y, flags in (
            ("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 80, (True, False, False)),
            ("G", unreal.MaterialProperty.MP_ROUGHNESS, 265, (False, True, False)),
            ("B", unreal.MaterialProperty.MP_METALLIC, 445, (False, False, True))):
        mask = node(material, unreal.MaterialExpressionComponentMask, -570, y,
                    r=flags[0], g=flags[1], b=flags[2], a=False)
        link(orm, "RGB", mask, "")
        output(mask, "", prop)
    if feathered:
        # The VertexColor expression exposes a distinct A output. Do not feed
        # its default RGB through a ComponentMask(A): Metal shader compilation
        # rejects that graph and substitutes the checkerboard material.
        output(vertex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.layout_material_expressions(material)
    lib.recompile_material(material)
    assets.save_loaded_asset(material)
    if {str(x) for x in lib.get_texture_parameter_names(material)} != {"AlbedoMap", "NormalMap", "ORMMap"}:
        raise RuntimeError(f"Hero path PBR parameters disappeared: {name}")
    return material


masters = {"opaque": master("M_NyaagyuHeroPath_OpaquePBR", False),
           "feathered": master("M_NyaagyuHeroPath_FeatheredPBR", True)}
instances = {}
settings = {
    "M_HeroPath_StoneFace": ("FaceAtlas", (1.00, 1.02, 1.03), "opaque"),
    "M_HeroPath_StoneEdge": ("Mineral", (.68, .68, .67), "opaque"),
    "M_HeroPath_SiltBed": ("Silt", (.41, .43, .40), "feathered"),
}
for slot, (surface, color, kind) in settings.items():
    instance_name = "MI_NyaagyuHeroPath_" + slot.removeprefix("M_HeroPath_")
    path = dest + "/" + instance_name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        instance_name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, masters[kind])
    for param, channel in (("AlbedoMap", "Albedo"), ("NormalMap", "NormalDX"), ("ORMMap", "ORM")):
        expected = textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance, param, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, param)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Hero path {instance_name} lost {param}")
    lib.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*color, 1))
    assets.save_loaded_asset(instance)
    instances[slot] = instance

task = unreal.AssetImportTask()
task.filename = str(source / record["fbx"])
task.destination_path = prop_path
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
options.static_mesh_import_data.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
options.static_mesh_import_data.set_editor_property("build_nanite", True)
task.options = options
asset_tools.import_asset_tasks([task])
mesh = assets.load_asset(prop_path + "/" + name)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Hero path static mesh import failed")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if set(slots) != expected_slots or len(slots) != 3:
    raise RuntimeError(f"Hero path FBX material slots changed: {slots}")
static_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = static_subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Hero path Windows Nanite data was not built")
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
static_subsystem.set_nanite_settings(mesh, nanite, True)
nanite = static_subsystem.get_nanite_settings(mesh)
if (not nanite.get_editor_property("enabled")
        or nanite.get_editor_property("fallback_percent_triangles") < .999
        or nanite.get_editor_property("fallback_target") != unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
        or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED):
    raise RuntimeError("Hero path conventional Mac fallback is missing")
if static_subsystem.get_lod_count(mesh) < 1 or static_subsystem.get_number_verts(mesh, 0) < 20000:
    raise RuntimeError("Hero path source LOD0 is unexpectedly sparse")
for index, slot in enumerate(slots):
    mesh.set_material(index, instances[slot])
    if mesh.get_material(index).get_path_name() != instances[slot].get_path_name():
        raise RuntimeError(f"Hero path lost PBR material binding for {slot}")
assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
assets.save_directory(prop_path, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAGYU_HERO_PATH_READY: {record['individual_stones']} modeled stones, "
           "CC0 scanned PBR, Nanite + full conventional fallback; terrain collision unchanged")
