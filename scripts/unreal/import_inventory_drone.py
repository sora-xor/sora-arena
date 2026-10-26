"""Import the reviewed Inventory disc, authored LODs and precision UCX hulls.

Run in the pinned editor after building the game module. This does not change
the level, patrol heights or movement envelope. Its saved readback is source
admission evidence; the DroneBody and route tests exercise actual collisions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inventory_drone import DESTINATION, NAME, RECORD_SHA256, geometry_readback, require, socket_readback, source_record
from sora_engine_pin import require_running_engine

require_running_engine("Inventory drone import")
root = Path(unreal.Paths.project_dir()).resolve()
record = source_record(root)
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = unreal.MaterialEditingLibrary
meshes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
assets.make_directory(DESTINATION)
assets.make_directory(DESTINATION + "/Textures")


def import_file(path, destination, name, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(path)
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options is not None:
        task.options = options
    tools.import_asset_tasks([task])
    asset = assets.load_asset(destination + "/" + name)
    require(asset is not None, "import failed: " + name)
    return asset


textures = {}
for channel, entry in record["textures"].items():
    file = root / entry["file"]
    texture = import_file(file, DESTINATION + "/Textures", file.stem)
    require(isinstance(texture, unreal.Texture2D), "texture import returned wrong type")
    texture.set_editor_property("srgb", channel == "BaseColor")
    texture.set_editor_property("max_texture_size", 2048)
    if channel == "Normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif channel in {"ORM", "Mask"}:
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    require(assets.save_loaded_asset(texture), "could not save texture")
    textures[channel] = texture

material_name = "M_Drone_Inventory"
material_path = DESTINATION + "/" + material_name
material = assets.load_asset(material_path) if assets.does_asset_exist(material_path) else tools.create_asset(
    material_name, DESTINATION, unreal.Material, unreal.MaterialFactoryNew())
require(isinstance(material, unreal.Material), "material import returned wrong type")
for expression in list(materials.get_material_expressions(material)):
    materials.delete_material_expression(material, expression)


def node(kind, x, y, **properties):
    expression = materials.create_material_expression(material, kind, x, y)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def link(left, output, right, pin):
    require(materials.connect_material_expressions(left, output, right, pin), "material connection failed")


def output(expression, pin, target):
    require(materials.connect_material_property(expression, pin, target), "material output failed")


samples = {}
for index, (channel, texture) in enumerate(textures.items()):
    samples[channel] = node(unreal.MaterialExpressionTextureSampleParameter2D, -800, index*220,
                            parameter_name=channel + "Map", texture=texture)
output(samples["BaseColor"], "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
output(samples["Normal"], "RGB", unreal.MaterialProperty.MP_NORMAL)
for channel, target in (("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
                        ("G", unreal.MaterialProperty.MP_ROUGHNESS), ("B", unreal.MaterialProperty.MP_METALLIC)):
    output(samples["ORM"], channel, target)
color = node(unreal.MaterialExpressionVectorParameter, -450, 850,
             parameter_name="EmissiveColor", default_value=unreal.LinearColor(.12, .85, 1, 1))
strength = node(unreal.MaterialExpressionScalarParameter, -450, 1050,
                parameter_name="EmissiveStrength", default_value=8.0)
masked = node(unreal.MaterialExpressionMultiply, -180, 700)
emission = node(unreal.MaterialExpressionMultiply, 50, 700)
link(samples["Mask"], "R", masked, "A")
link(color, "RGB", masked, "B")
link(masked, "", emission, "A")
link(strength, "", emission, "B")
output(emission, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
materials.layout_material_expressions(material)
materials.recompile_material(material)
require(assets.save_loaded_asset(material), "could not save material")

options = unreal.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
data = options.static_mesh_import_data
data.combine_meshes = True
data.generate_lightmap_u_vs = False
data.auto_generate_collision = False
data.one_convex_hull_per_ucx = True
data.set_editor_property("build_nanite", False)
mesh = import_file(root / record["assets"][NAME]["lods"][0]["file"], DESTINATION, NAME, options)
require(isinstance(mesh, unreal.StaticMesh), "drone did not import as a static mesh")
nanite = meshes.get_nanite_settings(mesh)
nanite.set_editor_property("enabled", False)
meshes.set_nanite_settings(mesh, nanite, True)
for index, entry in enumerate(record["assets"][NAME]["lods"][1:], 1):
    require(meshes.import_lod(mesh, index, str(root / entry["file"])) == index, f"LOD{index} import failed")
require(len(mesh.get_editor_property("static_materials")) == 1, "drone must retain its single baked material")
mesh.set_material(0, material)
# SetMaterial runs Pre/PostEditChange and can rebuild render data. Apply the
# authored thresholds after that edit, then verify the final saved result.
require(meshes.set_lod_screen_sizes(mesh, record["assets"][NAME]["screen_sizes"]), "LOD screen setup failed")
require(assets.save_loaded_asset(mesh), "could not save mesh")

# Read actual imported geometry, sockets, collisions and material bindings.
# Do not create replacement sockets or generate generic collision to pass this.
lods = []
for lod in range(meshes.get_lod_count(mesh)):
    points, triangles = [], 0
    for section in range(mesh.get_num_sections(lod)):
        positions, indices, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, lod, section)
        require(len(indices) % 3 == 0, "malformed imported render section")
        points.extend((p.x, p.y, p.z) for p in positions)
        triangles += len(indices) // 3
    require(triangles == mesh.get_num_triangles(lod), "readback missed render triangles")
    lods.append((points, triangles))
screens = list(meshes.get_lod_screen_sizes(mesh))
unreal.log("INVENTORY_DRONE_LOD_SCREENS: " + json.dumps(screens))
geometry = geometry_readback(record, lods, screens)
sockets = {}
for socket in mesh.get_editor_property("sockets"):
    name = str(socket.get_editor_property("socket_name"))
    require(name not in sockets, "duplicate imported socket")
    position = socket.get_editor_property("relative_location")
    scale = socket.get_editor_property("relative_scale")
    direction = unreal.MathLibrary.get_forward_vector(socket.get_editor_property("relative_rotation"))
    sockets[name] = {"position": [position.x, position.y, position.z], "scale": [scale.x, scale.y, scale.z],
                     "forward": [direction.x, direction.y, direction.z]}
socket_readback(record, sockets)
convex_count = meshes.get_convex_collision_count(mesh)
simple_count = meshes.get_simple_collision_count(mesh)
require(convex_count == 3 and simple_count == 0, "expected only the three authored convex UCX hulls")
require(meshes.get_collision_complexity(mesh) != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
        "simple precision queries must use the authored hulls")
require(mesh.get_material(0).get_path_name() == material.get_path_name(), "lost body material")
for channel, texture in textures.items():
    bound = materials.get_material_default_texture_parameter_value(material, channel + "Map")
    require(bound is not None and bound.get_path_name() == texture.get_path_name(), "lost " + channel + " binding")
require(not meshes.get_nanite_settings(mesh).get_editor_property("enabled"), "unexpected Nanite substitution")
report = {"source_record_sha256": RECORD_SHA256, "engine": unreal.SystemLibrary.get_engine_version(),
          "importer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "asset": mesh.get_path_name(), "geometry": geometry, "screen_sizes": screens, "sockets": sockets,
          "convex_count": convex_count, "other_simple_count": simple_count,
          "material": material.get_path_name(), "nanite": False,
          "status": "import readback passed; runtime collisions, routes and final art remain separate"}
out = root / "Saved/InventoryDroneImports" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
out.mkdir(parents=True, exist_ok=False)
(out / "readback.json").write_text(json.dumps(report, indent=2) + "\n")
unreal.log("INVENTORY_DRONE_IMPORT_READY: " + str(out / "readback.json"))
