"""Standalone pinned-UE import of the visual-only Estate perimeter wall.

Run: UnrealEditor-Cmd SoraArena.uproject \
  -ExecutePythonScript=scripts/unreal/import_nyaagyu_estate_wall.py

The C++ wall primitives remain collision; this imported mesh is presentation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Estate wall import")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuEstateWall"
record = json.loads((source / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


name = "SM_Nyaagyu_EstateWall_4m"
prop_path = "/Game/Generated/Environment/Props"
dest = "/Game/Generated/Environment/EstateWall"
expected_slots = {
    "M_Wall_CharredTimber", "M_Wall_EarthenScar", "M_Wall_Kawara",
    "M_Wall_LimePlaster", "M_Wall_StoneDark", "M_Wall_StoneFoundation",
}
if (record["schema_version"] != 1 or record["name"] != name
        or record["generator"] != "scripts/art/create_nyaagyu_estate_wall.py"
        or record["generator_sha256"] != sha(root / record["generator"])
        or record["unreal_asset"] != f"{prop_path}/{name}.{name}"
        or record["module_length_m"] != 4.0
        or record["collision_envelope_m"] != [1.0,4.0,5.4]
        or not record["collision"].startswith("Visual-only")
        or record["nanite_windows"] is not True
        or record["mac_conventional_fallback"] != {
            "source_fbx": name + ".fbx", "fallback_percent_triangles": 1.0,
            "fallback_target": "PercentTriangles", "generate_fallback": "Enabled",
            "render_config": "Config/Mac/MacEngine.ini"}
        or set(record["material_slots"]) != expected_slots
        or set(record["slot_definitions"]) != expected_slots
        or record["scan_manifest_sha256"] != sha(source / "ScanRock01/manifest.json")
        or sha(source / record["fbx"]) != record["fbx_sha256"]):
    raise RuntimeError("Estate wall identity, export, or collision policy changed")
mac_config = (root / record["mac_conventional_fallback"]["render_config"]).read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Estate wall Mac conventional fallback policy changed")
bounds = record["bounds_m"]
if (bounds["min"][0] < -.5 or bounds["max"][0] > .5
        or bounds["min"][1] < -2 or bounds["max"][1] > 2
        or bounds["min"][2] < -2.7 or bounds["max"][2] > 2.7):
    raise RuntimeError("Estate wall visual escaped its existing collision envelope")
if set(record["dependencies"]) != {"Stone", "Plaster", "Timber", "Kawara"}:
    raise RuntimeError("Estate wall texture dependency set changed")

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
assets.make_directory(dest)
assets.make_directory(dest + "/Textures")
assets.make_directory(prop_path)
textures = {}
for surface, dependency in record["dependencies"].items():
    if (dependency["license"] != "CC0-1.0"
            or not dependency["source_url"].startswith("https://polyhaven.com/a/")
            or set(dependency["files"]) != {"Albedo", "NormalDX", "ORM"}):
        raise RuntimeError(f"Estate wall scan provenance changed: {surface}")
    textures[surface] = {}
    for channel, file in dependency["files"].items():
        path = (root / file["repo_path"]).resolve()
        ph = (root / "Content/SourceArt/Environment/PolyHaven").resolve()
        rock_scan = (source / "ScanRock01").resolve()
        if not (path.is_relative_to(ph) or path.is_relative_to(rock_scan)) or sha(path) != file["sha256"]:
            raise RuntimeError(f"Estate wall source texture changed: {path}")
        if not file["upstream_url"].startswith("https://dl.polyhaven.org/"):
            raise RuntimeError(f"Estate wall texture origin is unpinned: {path}")
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest + "/Textures"
        task.destination_name = "T_EstateWall_" + surface + "_" + channel
        task.automated = True
        task.replace_existing = True
        task.save = True
        asset_tools.import_asset_tasks([task])
        texture = assets.load_asset(task.destination_path + "/" + task.destination_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Estate wall texture import failed: {path}")
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
        raise RuntimeError(f"Estate wall material link failed: {out}->{pin}")


def output(expression, out, prop):
    if not lib.connect_material_property(expression, out, prop):
        raise RuntimeError(f"Estate wall material output failed: {prop}")


master_name = "M_NyaagyuEstateWall_PBR"
master_path = dest + "/" + master_name
master = assets.load_asset(master_path) if assets.does_asset_exist(master_path) else asset_tools.create_asset(
    master_name, dest, unreal.Material, unreal.MaterialFactoryNew())
for old_expression in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old_expression)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Estate wall material retained expressions from its prior import")
base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, -370,
            parameter_name="AlbedoMap", texture=textures["Stone"]["Albedo"])
normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, -80,
              parameter_name="NormalMap", texture=textures["Stone"]["NormalDX"])
orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, 220,
           parameter_name="ORMMap", texture=textures["Stone"]["ORM"])
tint = node(master, unreal.MaterialExpressionVectorParameter, -620, -540,
            parameter_name="Tint", default_value=unreal.LinearColor(1,1,1,1))
rough_bias = node(master, unreal.MaterialExpressionScalarParameter, -590, 365,
                  parameter_name="RoughnessBias", default_value=0)
mult = node(master, unreal.MaterialExpressionMultiply, -290, -350)
link(base, "RGB", mult, "A")
link(tint, "RGB", mult, "B")
output(mult, "", unreal.MaterialProperty.MP_BASE_COLOR)
output(normal, "RGB", unreal.MaterialProperty.MP_NORMAL)
for axis, prop, y, flags in (
        ("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, 45, (True,False,False)),
        ("G", unreal.MaterialProperty.MP_ROUGHNESS, 230, (False,True,False)),
        ("B", unreal.MaterialProperty.MP_METALLIC, 450, (False,False,True))):
    mask = node(master, unreal.MaterialExpressionComponentMask, -550, y,
                r=flags[0], g=flags[1], b=flags[2], a=False)
    link(orm, "RGB", mask, "")
    if axis == "G":
        rough_add = node(master, unreal.MaterialExpressionAdd, -300, y)
        link(mask, "", rough_add, "A")
        link(rough_bias, "", rough_add, "B")
        output(rough_add, "", prop)
    else:
        output(mask, "", prop)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(x) for x in lib.get_texture_parameter_names(master)} != {"AlbedoMap","NormalMap","ORMMap"}:
    raise RuntimeError("Estate wall master PBR parameters disappeared")

instances = {}
for slot, definition in record["slot_definitions"].items():
    surface = definition["source"]
    if surface not in textures or len(definition["tint"]) != 3:
        raise RuntimeError(f"Estate wall slot definition changed: {slot}")
    instance_name = "MI_NyaagyuEstateWall_" + slot.removeprefix("M_Wall_")
    path = dest + "/" + instance_name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        instance_name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, master)
    for parameter, channel in (("AlbedoMap","Albedo"),("NormalMap","NormalDX"),("ORMMap","ORM")):
        expected = textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Estate wall {instance_name} lost {parameter}")
    lib.set_material_instance_vector_parameter_value(instance, "Tint", unreal.LinearColor(*definition["tint"],1))
    lib.set_material_instance_scalar_parameter_value(instance, "RoughnessBias", definition["roughness_bias"])
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
options.static_mesh_import_data.set_editor_property("build_nanite", True)
task.options = options
asset_tools.import_asset_tasks([task])
mesh = assets.load_asset(prop_path + "/" + name)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Estate wall static mesh import failed")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if sorted(slots) != record["material_slots"]:
    raise RuntimeError(f"Estate wall FBX material slots changed: {slots}")
static_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = static_subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Estate wall Windows Nanite data was not built")
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
static_subsystem.set_nanite_settings(mesh, nanite, True)
nanite = static_subsystem.get_nanite_settings(mesh)
if (not nanite.get_editor_property("enabled")
        or nanite.get_editor_property("fallback_percent_triangles") < .999
        or nanite.get_editor_property("fallback_target") != unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
        or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED):
    raise RuntimeError("Estate wall conventional Mac fallback is missing")
if static_subsystem.get_lod_count(mesh) < 1 or static_subsystem.get_number_verts(mesh, 0) < 1000:
    raise RuntimeError("Estate wall conventional fallback LOD0 is missing")
for index, slot in enumerate(slots):
    mesh.set_material(index, instances[slot])
    if mesh.get_material(index).get_path_name() != instances[slot].get_path_name():
        raise RuntimeError(f"Estate wall lost exact material binding for {slot}")
assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
assets.save_directory(prop_path, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAGYU_ESTATE_WALL_READY: 4 m visual module, {len(instances)} material slots, Nanite + full conventional fallback; existing C++ collision unchanged")
