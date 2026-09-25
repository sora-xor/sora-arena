"""Standalone pinned-UE import of visual-only Estate ground dressing.

Run: UnrealEditor-Cmd SoraArena.uproject \
  -ExecutePythonScript=scripts/unreal/import_nyaagyu_ground_dressing.py

The flat terrain remains the only gameplay collision; this mesh is presentation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Roadside import")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuGroundDressing"
record = json.loads((source / "manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


name = "SM_Nyaagyu_RoadsideLeafSilt_4m"
prop_path = "/Game/Generated/Environment/Props"
dest = "/Game/Generated/Environment/Roadside"
expected_slots = {
    "M_Ground_DampSilt", "M_Ground_LeafUmber", "M_Ground_LeafOchre",
    "M_Ground_Moss", "M_Ground_RiverStone", "M_Ground_WetStone",
}
if (record["schema_version"] != 1 or record["name"] != name
        or record["generator"] != "scripts/art/create_nyaagyu_ground_dressing.py"
        or record["generator_sha256"] != sha(root / record["generator"])
        or record["unreal_asset"] != f"{prop_path}/{name}.{name}"
        or record["nominal_road_length_m"] != 4.0
        or record["orientation"] != "Local X follows Estate road; +Y points outward from road center; +Z up"
        or not record["collision"].startswith("Visual only")
        or record["nanite_windows"] is not True
        or record["mac_conventional_fallback"] != {
            "source_fbx": name + ".fbx", "fallback_percent_triangles": 1.0,
            "fallback_target": "PercentTriangles", "generate_fallback": "Enabled",
            "render_config": "Config/Mac/MacEngine.ini"}
        or set(record["material_slots"]) != expected_slots
        or set(record["slot_definitions"]) != expected_slots
        or record["new_scan_manifest_sha256"] != sha(source / "ScanForestLeaves02/manifest.json")
        or sha(source / record["fbx"]) != record["fbx_sha256"]):
    raise RuntimeError("Roadside identity, export, or collision policy changed")
mac_config = (root / record["mac_conventional_fallback"]["render_config"]).read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Roadside Mac conventional fallback policy changed")
bounds = record["bounds_m"]
if (bounds["min"][0] < -2.2 or bounds["max"][0] > 2.2
        or bounds["min"][1] < -1.3 or bounds["max"][1] > 1.3
        or bounds["min"][2] < -.02 or bounds["max"][2] > .2):
    raise RuntimeError("Roadside visual escaped its low surface envelope")
if set(record["dependencies"]) != {"DampSilt", "ForestLitter", "RiverStone"}:
    raise RuntimeError("Roadside texture dependency set changed")

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
        raise RuntimeError(f"Roadside scan provenance changed: {surface}")
    textures[surface] = {}
    for channel, file in dependency["files"].items():
        path = (root / file["repo_path"]).resolve()
        ph = (root / "Content/SourceArt/Environment/PolyHaven").resolve()
        rock_scan = (root / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01").resolve()
        forest_scan = (source / "ScanForestLeaves02").resolve()
        if not (path.is_relative_to(ph) or path.is_relative_to(rock_scan) or path.is_relative_to(forest_scan)) or sha(path) != file["sha256"]:
            raise RuntimeError(f"Roadside source texture changed: {path}")
        if not file["upstream_url"].startswith("https://dl.polyhaven.org/"):
            raise RuntimeError(f"Roadside texture origin is unpinned: {path}")
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest + "/Textures"
        task.destination_name = "T_Roadside_" + surface + "_" + channel
        task.automated = True
        task.replace_existing = True
        task.save = True
        asset_tools.import_asset_tasks([task])
        texture = assets.load_asset(task.destination_path + "/" + task.destination_name)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Roadside texture import failed: {path}")
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
        raise RuntimeError(f"Roadside material link failed: {out}->{pin}")


def output(expression, out, prop):
    if not lib.connect_material_property(expression, out, prop):
        raise RuntimeError(f"Roadside material output failed: {prop}")


def make_master(name, feathered):
    path = dest + "/" + name
    master = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        name, dest, unreal.Material, unreal.MaterialFactoryNew())
    for old_expression in list(lib.get_material_expressions(master)):
        lib.delete_material_expression(master, old_expression)
    if lib.get_num_material_expressions(master):
        raise RuntimeError(f"Ground dressing material {name} retained expressions from its prior import")
    master.set_editor_property("two_sided", True)
    master.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if feathered else unreal.BlendMode.BLEND_OPAQUE)
    base = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, -370,
                parameter_name="AlbedoMap", texture=textures["DampSilt"]["Albedo"])
    normal = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, -80,
                  parameter_name="NormalMap", texture=textures["DampSilt"]["NormalDX"])
    orm = node(master, unreal.MaterialExpressionTextureSampleParameter2D, -950, 220,
               parameter_name="ORMMap", texture=textures["DampSilt"]["ORM"])
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
    if feathered:
        vertex = node(master, unreal.MaterialExpressionVertexColor, -630, 610)
        output(vertex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    lib.layout_material_expressions(master)
    lib.recompile_material(master)
    assets.save_loaded_asset(master)
    if {str(x) for x in lib.get_texture_parameter_names(master)} != {"AlbedoMap","NormalMap","ORMMap"}:
        raise RuntimeError(f"Roadside master PBR parameters disappeared: {name}")
    return master


masters = {
    "opaque": make_master("M_NyaagyuRoadside_OpaquePBR", False),
    "feathered": make_master("M_NyaagyuRoadside_FeatheredPBR", True),
}

instances = {}
for slot, definition in record["slot_definitions"].items():
    surface = definition["source"]
    if surface not in textures or len(definition["tint"]) != 3:
        raise RuntimeError(f"Roadside slot definition changed: {slot}")
    instance_name = "MI_NyaagyuRoadside_" + slot.removeprefix("M_Ground_")
    path = dest + "/" + instance_name
    instance = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        instance_name, dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance, masters["feathered" if slot in {
        "M_Ground_DampSilt", "M_Ground_Moss"} else "opaque"])
    for parameter, channel in (("AlbedoMap","Albedo"),("NormalMap","NormalDX"),("ORMMap","ORM")):
        expected = textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance, parameter, expected)
        bound = lib.get_material_instance_texture_parameter_value(instance, parameter)
        if not bound or bound.get_path_name() != expected.get_path_name():
            raise RuntimeError(f"Roadside {instance_name} lost {parameter}")
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
options.static_mesh_import_data.set_editor_property(
    "vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
options.static_mesh_import_data.set_editor_property("build_nanite", True)
task.options = options
asset_tools.import_asset_tasks([task])
mesh = assets.load_asset(prop_path + "/" + name)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Roadside static mesh import failed")
slots = [str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if sorted(slots) != record["material_slots"]:
    raise RuntimeError(f"Roadside FBX material slots changed: {slots}")
static_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite = static_subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Roadside Windows Nanite data was not built")
nanite.set_editor_property("fallback_percent_triangles", 1.0)
nanite.set_editor_property("fallback_target", unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("generate_fallback", unreal.NaniteGenerateFallback.ENABLED)
static_subsystem.set_nanite_settings(mesh, nanite, True)
nanite = static_subsystem.get_nanite_settings(mesh)
if (not nanite.get_editor_property("enabled")
        or nanite.get_editor_property("fallback_percent_triangles") < .999
        or nanite.get_editor_property("fallback_target") != unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
        or nanite.get_editor_property("generate_fallback") != unreal.NaniteGenerateFallback.ENABLED):
    raise RuntimeError("Roadside conventional Mac fallback is missing")
if static_subsystem.get_lod_count(mesh) < 1 or static_subsystem.get_number_verts(mesh, 0) < 1000:
    raise RuntimeError("Roadside conventional fallback LOD0 is missing")
for index, slot in enumerate(slots):
    mesh.set_material(index, instances[slot])
    if mesh.get_material(index).get_path_name() != instances[slot].get_path_name():
        raise RuntimeError(f"Roadside lost exact material binding for {slot}")
assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
assets.save_directory(prop_path, only_if_is_dirty=False, recursive=True)
unreal.log(f"NYAAGYU_ROADSIDE_READY: 4 m visual module, {len(instances)} material slots, Nanite + full conventional fallback; terrain collision unchanged")
