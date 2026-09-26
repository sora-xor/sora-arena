"""Standalone pinned-UE import of the runtime SORA mon mesh.

Run: UnrealEditor-Cmd SoraArena.uproject \
  -ExecutePythonScript=scripts/unreal/import_sora_kamon_mon.py
import_original_assets.py also runs it, after M_ArenaSurface exists.

The FBX is scripts/art/create_sora_kamon_mon.py's exact extrusion of the
user-supplied SVG's two paths; this import checks both hashes and never
simplifies the mesh. Practice presentation places and colours it at runtime,
and it never collides. It keeps its vertices CPU-readable in cooked builds, so
the packaged practice test can check its orientation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("SORA mon import")
root = Path(unreal.Paths.project_dir()).resolve()
source = root / "Content/SourceArt/UI/SoraKamonMon"
record = json.loads((source / "manifest.json").read_text())
logo = json.loads((root / "Content/SourceArt/UI/sora_logo_manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


name = "SM_SoraKamon"
destination = "/Game/Generated/UI"
if (record["schema_version"] != 1 or record["name"] != name
        or record["generator"] != "scripts/art/create_sora_kamon_mon.py"
        or record["unreal_asset"] != f"{destination}/{name}.{name}"
        or record["source_svg_sha256"] != logo["source_sha256"]
        or sha((source / record["source_svg"]).resolve()) != logo["source_sha256"]
        or sha(source / record["fbx"]) != record["fbx_sha256"]
        or record["diameter_m"] != 1.0 or record["thickness_m"] != .01
        or record["material_slots"] != ["M_SoraKamon"]):
    raise RuntimeError("The SORA mon source, its SVG or its identity changed")

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary
lib = unreal.MaterialEditingLibrary
assets.make_directory(destination)
surface = assets.load_asset("/Game/Generated/Materials/M_ArenaSurface")
if not isinstance(surface, unreal.Material):
    raise RuntimeError("M_ArenaSurface must be imported before the SORA mon")
# The mark's own red, E3242D in the SVG, as linear colour on the lacquer surface.
instance_path = f"{destination}/MI_SoraKamon_Red"
instance = assets.load_asset(instance_path) if assets.does_asset_exist(instance_path) else tools.create_asset(
    "MI_SoraKamon_Red", destination, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
lib.set_material_instance_parent(instance, surface)
lib.set_material_instance_vector_parameter_value(instance, "BaseColor", unreal.LinearColor(.768, .0176, .0262, 1))
lib.set_material_instance_scalar_parameter_value(instance, "Roughness", .42)
lib.set_material_instance_scalar_parameter_value(instance, "Metallic", 0)
assets.save_loaded_asset(instance)

task = unreal.AssetImportTask()
task.filename = str(source / record["fbx"])
task.destination_path = destination
task.destination_name = name
task.automated = True
task.replace_existing = True
task.save = True
options = unreal.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.generate_lightmap_u_vs = False
options.static_mesh_import_data.auto_generate_collision = False
options.static_mesh_import_data.set_editor_property("build_nanite", False)
task.options = options
tools.import_asset_tasks([task])
mesh = assets.load_asset(f"{destination}/{name}")
if not isinstance(mesh, unreal.StaticMesh):
    raise RuntimeError("The SORA mon static mesh failed to import")
static_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
if static_subsystem.get_number_verts(mesh, 0) < record["vertices"] or static_subsystem.get_lod_count(mesh) < 1:
    raise RuntimeError("The SORA mon lost vertices on import")
# One metre across, one centimetre thick, facing +X.
bounds = mesh.get_bounding_box()
size = bounds.max - bounds.min
if abs(size.x - 1.0) > .01 or abs(size.y - 100.0) > .1 or abs(size.z - 100.0) > .1:
    raise RuntimeError(f"The SORA mon imported at the wrong size or orientation: {size}")
mesh.set_material(0, instance)
if mesh.get_material(0).get_path_name() != instance.get_path_name():
    raise RuntimeError("The SORA mon lost its lacquer red")
# A cooked build releases vertex data from CPU memory after upload unless the
# mesh keeps it. SoraArena.Practice.MarksTextScoreboard reads the mon's
# positions to prove it stands upright, in the editor and in the package alike.
mesh.set_editor_property("allow_cpu_access", True)
assets.save_loaded_asset(mesh)
assets.save_directory(destination, only_if_is_dirty=False, recursive=True)
unreal.log(f"SORA_KAMON_MON_READY: {record['vertices']} vertices, {record['triangles']} triangles from the pinned SVG, visual only")
