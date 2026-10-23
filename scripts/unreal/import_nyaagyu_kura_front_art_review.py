"""Import the source-only Kura frontage into isolated pinned-UE ArtReview.

No WorldBuilder placement, gameplay collision, map data, or save data changes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Kura front art review")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/Environment/NyaagyuKuraFront"
record = json.loads((source / "manifest.json").read_text())
texture_record = json.loads((source / record["texture_manifest"]).read_text())
palette = json.loads((root / "Content/SourceArt/Environment/PolyHaven/manifest.json").read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


if (record["schema_version"] != 1
        or record["name"] != "SM_Nyaagyu_KuraFront_Candidate"
        or record["generator_sha256"] != sha(root / record["generator"])
        or record["source_blend_sha256"] != sha(source / record["source_blend"])
        or record["fbx_sha256"] != sha(source / record["fbx"])
        or record["texture_manifest_sha256"] != sha(source / record["texture_manifest"])
        or record["door_board_count"] != 14
        or record["source_triangles"] != 59342
        or not record["collision"].startswith("Visual only")):
    raise RuntimeError("Kura front source, identity or collision policy changed")
if "r.Nanite.ProxyRenderMode=0" not in (root / "Config/Mac/MacEngine.ini").read_text():
    raise RuntimeError("Mac conventional fallback policy changed")
for role, item in texture_record["atlas_files"].items():
    if role not in ("Albedo", "NormalDX", "ARM") or sha(source / item["file"]) != item["sha256"]:
        raise RuntimeError(f"Kura front atlas changed: {role}")
wood = next(x for x in palette["assets"] if x["asset_id"] == "wood_planks_dirt")
iron = next(x for x in palette["assets"] if x["asset_id"] == "rusty_metal_02")
if wood["license"] != "CC0-1.0" or iron["license"] != "CC0-1.0":
    raise RuntimeError("Kura front scan rights changed")
for role, item in texture_record["source_files"].items():
    if sha(root / item["file"]) != item["sha256"] or item["sha256"] not in {f["sha256"] for f in wood["files"]}:
        raise RuntimeError(f"Kura front wood input changed: {role}")

dest = "/Game/Generated/ArtReview/KuraFront"
tex_dest, mat_dest, mesh_dest = [dest + "/" + x for x in ("Textures", "Materials", "Meshes")]
assets = unreal.EditorAssetLibrary
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.MaterialEditingLibrary
for folder in (dest, tex_dest, mat_dest, mesh_dest):
    assets.make_directory(folder)


def import_asset(path, folder, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    asset_tools.import_asset_tasks([task])
    asset = assets.load_asset(folder + "/" + name)
    if not asset:
        raise RuntimeError(f"Kura front import failed: {path}")
    return asset


textures = {}
input_sets = {
    "Cedar": {role: source / item["file"] for role,item in texture_record["atlas_files"].items()},
    "Iron": {},
}
for file in iron["files"]:
    role = {"diffuse":"Albedo", "nor_dx":"NormalDX", "arm":"ARM"}.get(file["channel"].lower())
    if role:
        path = root / "Content/SourceArt/Environment/PolyHaven" / file["file"]
        if sha(path) != file["sha256"]:
            raise RuntimeError(f"Kura front iron scan changed: {path}")
        input_sets["Iron"][role] = path
if any(set(group) != {"Albedo", "NormalDX", "ARM"} for group in input_sets.values()):
    raise RuntimeError("Kura front PBR channel set incomplete")
for group, items in input_sets.items():
    textures[group] = {}
    for role, path in items.items():
        name = f"T_KuraFront_{group}_{role}"
        obj = import_asset(path, tex_dest, name)
        if not isinstance(obj, unreal.Texture2D):
            raise RuntimeError(f"Kura front texture is not Texture2D: {name}")
        obj.set_editor_property("srgb", role == "Albedo")
        if role == "NormalDX":
            obj.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            obj.set_editor_property("flip_green_channel", False)
        elif role == "ARM":
            obj.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        obj.set_editor_property("max_texture_size", 2048)
        assets.save_loaded_asset(obj)
        textures[group][role] = obj


materials = {}
for group, tint in (("Cedar", (1,1,1)), ("Iron", (.21,.24,.27))):
    name = "M_KuraFront_" + group + "_PBR"
    path = mat_dest + "/" + name
    mat = assets.load_asset(path) if assets.does_asset_exist(path) else asset_tools.create_asset(
        name, mat_dest, unreal.Material, unreal.MaterialFactoryNew())
    for old in list(lib.get_material_expressions(mat)):
        lib.delete_material_expression(mat, old)
    if lib.get_num_material_expressions(mat):
        raise RuntimeError(f"Kura front material retained stale expressions: {name}")
    nodes = {}
    for role, y in (("Albedo",-300),("NormalDX",0),("ARM",300)):
        node = lib.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, y)
        node.set_editor_property("parameter_name",role+"Map")
        node.set_editor_property("texture", textures[group][role])
        nodes[role] = node
    tint_node = lib.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -520, -490)
    tint_node.set_editor_property("parameter_name", "ScanTint")
    tint_node.set_editor_property("default_value", unreal.LinearColor(*tint, 1))
    multiply = lib.create_material_expression(mat, unreal.MaterialExpressionMultiply, -270, -260)
    if not (lib.connect_material_expressions(nodes["Albedo"], "RGB", multiply, "A")
            and lib.connect_material_expressions(tint_node, "RGB", multiply, "B")):
        raise RuntimeError(f"Kura front tint graph failed: {name}")
    for node,pin,prop in (
            (multiply,"",unreal.MaterialProperty.MP_BASE_COLOR),
            (nodes["NormalDX"],"RGB",unreal.MaterialProperty.MP_NORMAL),
            (nodes["ARM"],"R",unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
            (nodes["ARM"],"G",unreal.MaterialProperty.MP_ROUGHNESS),
            (nodes["ARM"],"B",unreal.MaterialProperty.MP_METALLIC)):
        if not lib.connect_material_property(node,pin,prop):
            raise RuntimeError(f"Kura front PBR output failed: {name}/{prop}")
    lib.layout_material_expressions(mat)
    lib.recompile_material(mat)
    assets.save_loaded_asset(mat)
    materials[group] = mat

base_mesh = assets.load_asset("/Game/Generated/Environment/Props/SM_Nyaagyu_ProvisionKura")
if not isinstance(base_mesh, unreal.StaticMesh):
    raise RuntimeError("Kura front parent mesh missing from imported environment")
base_slots = {str(slot.get_editor_property("material_slot_name")): base_mesh.get_material(i)
              for i,slot in enumerate(base_mesh.get_editor_property("static_materials"))}
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.generate_lightmap_u_vs = True
options.static_mesh_import_data.auto_generate_collision = False
options.static_mesh_import_data.set_editor_property("build_nanite", True)
mesh = import_asset(source / record["fbx"], mesh_dest, record["name"], options)
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("Kura front mesh import did not produce StaticMesh")
actual_slots = [str(slot.get_editor_property("material_slot_name"))
                for slot in mesh.get_editor_property("static_materials")]
expected = set(base_slots) | {"M_KuraFront_CC0CedarAtlas", "M_KuraFront_ForgedIron"}
if set(actual_slots) != expected or len(actual_slots) != len(expected):
    raise RuntimeError(f"Kura front material-zone identity changed: {actual_slots}")
for i, slot in enumerate(actual_slots):
    assigned = (materials["Cedar"] if slot == "M_KuraFront_CC0CedarAtlas" else
                materials["Iron"] if slot == "M_KuraFront_ForgedIron" else base_slots[slot])
    if not assigned:
        raise RuntimeError(f"Kura front source material missing: {slot}")
    mesh.set_material(i, assigned)
    if mesh.get_material(i).get_path_name() != assigned.get_path_name():
        raise RuntimeError(f"Kura front material assignment failed: {slot}")
subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if subsystem.get_number_verts(mesh,0) < 1000:
    raise RuntimeError("Kura front full-size FBX geometry was lost")
nanite = subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Kura front Nanite source build was lost")
nanite.set_editor_property("fallback_target",unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("fallback_percent_triangles",1.0)
nanite.set_editor_property("generate_fallback",unreal.NaniteGenerateFallback.ENABLED)
subsystem.set_nanite_settings(mesh,nanite,True)
nanite = subsystem.get_nanite_settings(mesh)
if nanite.get_editor_property("fallback_percent_triangles") < .999:
    raise RuntimeError("Kura front Mac conventional fallback was reduced")
assets.save_loaded_asset(mesh)
assets.save_directory(dest, only_if_is_dirty=False, recursive=True)
unreal.log("NYAAGYU_KURA_FRONT_ART_REVIEW_READY: one visual-only 59,342-triangle candidate with pinned PBR and full Mac fallback")
