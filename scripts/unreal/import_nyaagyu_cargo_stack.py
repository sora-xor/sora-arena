"""Standalone pinned-UE import of the Estate visual-only cargo stack.

Run: UnrealEditor-Cmd SoraArena.uproject \
  -ExecutePythonScript=scripts/unreal/import_nyaagyu_cargo_stack.py

WorldBuilder placement and its existing simple cover collision are separate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import unreal


sys.path.insert(0, str(Path(__file__).resolve().parent))
from sora_engine_pin import require_running_engine  # noqa: E402

require_running_engine("Nyaagyu cargo import")
root=Path(unreal.Paths.project_dir()).resolve()
source=root/"Content/SourceArt/Environment/NyaagyuCargoStack"
record=json.loads((source/"manifest.json").read_text())
pbr=json.loads((source/"PBR/manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


name="SM_Nyaagyu_CargoStack"
prop_path="/Game/Generated/Environment/Props"
destination="/Game/Generated/Environment/CargoStack"
if (record["schema_version"]!=1 or record["name"]!=name
        or record["generator"]!="scripts/art/create_nyaagyu_cargo_stack.py"
        or record["unreal_asset"]!=f"{prop_path}/{name}.{name}"
        or record["collision_envelope_m"]!=[2.30,1.80,1.40]
        or not record["collision"].startswith("Visual only")
        or record["nanite_windows"] is not True
        or record["mac_conventional_fallback"]!={
            "source_fbx":name+".fbx", "fallback_percent_triangles":1.0,
            "fallback_target":"PercentTriangles", "generate_fallback":"Enabled",
            "render_config":"Config/Mac/MacEngine.ini"}
        or pbr["schema_version"]!=1
        or record["pbr_manifest_sha256"]!=sha(source/"PBR/manifest.json")
        or sha(source/record["fbx"])!=record["fbx_sha256"]):
    raise RuntimeError("Nyaagyu cargo geometry, collision envelope or package identity changed")
mac_config=(root/record["mac_conventional_fallback"]["render_config"]).read_text()
if "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Nyaagyu cargo Mac conventional fallback policy changed")
logo=(source/record["insignia_source"]).resolve()
if sha(logo)!=record["insignia_sha256"] or len(record["exact_sora_kamon_objects"])!=2:
    raise RuntimeError("Nyaagyu cargo exact SORA stamp is missing or changed")
if (record["bounds_m"]["min"][0]<-1.15 or record["bounds_m"]["max"][0]>1.15
        or record["bounds_m"]["min"][1]<-.90 or record["bounds_m"]["max"][1]>.90
        or record["bounds_m"]["min"][2]<0 or record["bounds_m"]["max"][2]>1.40):
    raise RuntimeError("Nyaagyu cargo visual escaped its cover collision envelope")
expected_slots={"M_Cargo_AgedTimber","M_Cargo_BlackIron","M_Cargo_DarkInterior",
                "M_Cargo_HempRope","M_Cargo_IndigoCloth","M_Cargo_SORA_Red",
                "M_Cargo_StrawWrap","M_Cargo_WornEdge"}
if set(record["material_slots"])!=expected_slots or set(pbr["material_slots"])!=expected_slots-{"M_Cargo_BlackIron","M_Cargo_SORA_Red"}:
    raise RuntimeError("Nyaagyu cargo material-slot identity changed")
if pbr["generator_sha256"]!=sha(root/pbr["generator"]):
    raise RuntimeError("Nyaagyu cargo procedural texture generator changed")

tools=unreal.AssetToolsHelpers.get_asset_tools()
assets=unreal.EditorAssetLibrary
lib=unreal.MaterialEditingLibrary
assets.make_directory(destination)
assets.make_directory(destination+"/Textures")
assets.make_directory(prop_path)
textures={}
for texture_set in pbr["sets"]:
    surface=texture_set["name"]
    if texture_set["resolution"]!=[2048,2048] or {part["channel"] for part in texture_set["maps"]}!={"Albedo","NormalDX","ORM"}:
        raise RuntimeError(f"Nyaagyu cargo PBR map set incomplete: {surface}")
    textures[surface]={}
    for part in texture_set["maps"]:
        path=(source/"PBR"/part["file"]).resolve()
        if path.parent!=(source/"PBR").resolve() or sha(path)!=part["sha256"]:
            raise RuntimeError(f"Nyaagyu cargo PBR map changed: {path}")
        task=unreal.AssetImportTask()
        task.filename=str(path)
        task.destination_path=destination+"/Textures"
        task.destination_name=path.stem
        task.automated=True
        task.replace_existing=True
        task.save=True
        tools.import_asset_tasks([task])
        texture=assets.load_asset(destination+"/Textures/"+path.stem)
        if not isinstance(texture,unreal.Texture2D):
            raise RuntimeError(f"Nyaagyu cargo texture failed import: {path.name}")
        texture.set_editor_property("srgb",part["channel"]=="Albedo")
        if part["channel"]=="NormalDX":
            texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel",False)
        elif part["channel"]=="ORM":
            texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size",2048)
        assets.save_loaded_asset(texture)
        textures[surface][part["channel"]]=texture


def node(material,cls,x,y,**properties):
    expression=lib.create_material_expression(material,cls,x,y)
    for key,value in properties.items():
        expression.set_editor_property(key,value)
    return expression


def link(left,output,right,pin):
    if not lib.connect_material_expressions(left,output,right,pin):
        raise RuntimeError(f"Nyaagyu cargo material connection failed: {output}->{pin}")


def output(expression,output_name,property_name):
    if not lib.connect_material_property(expression,output_name,property_name):
        raise RuntimeError(f"Nyaagyu cargo material output failed: {property_name}")


master_name="M_NyaagyuCargo_PBR"
master_path=destination+"/"+master_name
master=assets.load_asset(master_path) if assets.does_asset_exist(master_path) else tools.create_asset(
    master_name,destination,unreal.Material,unreal.MaterialFactoryNew())
master.set_editor_property("used_with_nanite", True)
for old_expression in list(lib.get_material_expressions(master)):
    lib.delete_material_expression(master, old_expression)
if lib.get_num_material_expressions(master):
    raise RuntimeError("Cargo material retained expressions from its prior import")
base_map=node(master,unreal.MaterialExpressionTextureSampleParameter2D,-850,-330,
              parameter_name="AlbedoMap",texture=textures["Wood"]["Albedo"])
normal_map=node(master,unreal.MaterialExpressionTextureSampleParameter2D,-850,-30,
                parameter_name="NormalMap",texture=textures["Wood"]["NormalDX"])
orm_map=node(master,unreal.MaterialExpressionTextureSampleParameter2D,-850,260,
             parameter_name="ORMMap",texture=textures["Wood"]["ORM"])
tint=node(master,unreal.MaterialExpressionVectorParameter,-540,-520,
          parameter_name="Tint",default_value=unreal.LinearColor(1,1,1,1))
multiply=node(master,unreal.MaterialExpressionMultiply,-220,-330)
link(base_map,"RGB",multiply,"A")
link(tint,"RGB",multiply,"B")
output(multiply,"",unreal.MaterialProperty.MP_BASE_COLOR)
output(normal_map,"RGB",unreal.MaterialProperty.MP_NORMAL)
for axis,property_name,y,flags in (
        ("R",unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,80,(True,False,False)),
        ("G",unreal.MaterialProperty.MP_ROUGHNESS,260,(False,True,False)),
        ("B",unreal.MaterialProperty.MP_METALLIC,440,(False,False,True))):
    mask=node(master,unreal.MaterialExpressionComponentMask,-470,y,
              r=flags[0],g=flags[1],b=flags[2],a=False)
    link(orm_map,"RGB",mask,"")
    output(mask,"",property_name)
lib.layout_material_expressions(master)
lib.recompile_material(master)
assets.save_loaded_asset(master)
if {str(item) for item in lib.get_texture_parameter_names(master)}!={"AlbedoMap","NormalMap","ORMMap"}:
    raise RuntimeError("Nyaagyu cargo master PBR map parameters disappeared")

instances={}
for slot,definition in pbr["material_slots"].items():
    surface=definition["surface"]
    if surface not in textures or len(definition["tint"])!=3:
        raise RuntimeError(f"Nyaagyu cargo material definition changed: {slot}")
    instance_name="MI_NyaagyuCargo_"+slot.removeprefix("M_Cargo_")
    asset_path=destination+"/"+instance_name
    instance=assets.load_asset(asset_path) if assets.does_asset_exist(asset_path) else tools.create_asset(
        instance_name,destination,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,master)
    for parameter,channel in (("AlbedoMap","Albedo"),("NormalMap","NormalDX"),("ORMMap","ORM")):
        expected=textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance,parameter,expected)
        bound=lib.get_material_instance_texture_parameter_value(instance,parameter)
        if not bound or bound.get_path_name()!=expected.get_path_name():
            raise RuntimeError(f"Nyaagyu cargo {instance_name} lost {parameter}")
    lib.set_material_instance_vector_parameter_value(instance,"Tint",unreal.LinearColor(*definition["tint"],1))
    assets.save_loaded_asset(instance)
    instances[slot]=instance

# Small hardware and the exact SVG stamp use authored scalar PBR values. They
# share no texture entitlement with the wood/fabric surfaces.
flat_name="M_NyaagyuCargo_FlatPBR"
flat_path=destination+"/"+flat_name
flat=assets.load_asset(flat_path) if assets.does_asset_exist(flat_path) else tools.create_asset(
    flat_name,destination,unreal.Material,unreal.MaterialFactoryNew())
flat.set_editor_property("used_with_nanite", True)
for old_expression in list(lib.get_material_expressions(flat)):
    lib.delete_material_expression(flat, old_expression)
if lib.get_num_material_expressions(flat):
    raise RuntimeError("Flat cargo material retained expressions from its prior import")
flat_color=node(flat,unreal.MaterialExpressionVectorParameter,-360,-180,
                parameter_name="BaseColor",default_value=unreal.LinearColor(1,1,1,1))
flat_rough=node(flat,unreal.MaterialExpressionScalarParameter,-360,40,
                parameter_name="Roughness",default_value=.8)
flat_metal=node(flat,unreal.MaterialExpressionScalarParameter,-360,260,
                parameter_name="Metallic",default_value=0)
output(flat_color,"RGB",unreal.MaterialProperty.MP_BASE_COLOR)
output(flat_rough,"",unreal.MaterialProperty.MP_ROUGHNESS)
output(flat_metal,"",unreal.MaterialProperty.MP_METALLIC)
lib.recompile_material(flat)
assets.save_loaded_asset(flat)
for slot,color,roughness,metallic in (
        ("M_Cargo_BlackIron",(.09,.087,.079),.49,.81),
        ("M_Cargo_SORA_Red",(.67,.025,.035),.74,0)):
    instance_name="MI_NyaagyuCargo_"+slot.removeprefix("M_Cargo_")
    path=destination+"/"+instance_name
    instance=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        instance_name,destination,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,flat)
    lib.set_material_instance_vector_parameter_value(instance,"BaseColor",unreal.LinearColor(*color,1))
    lib.set_material_instance_scalar_parameter_value(instance,"Roughness",roughness)
    lib.set_material_instance_scalar_parameter_value(instance,"Metallic",metallic)
    assets.save_loaded_asset(instance)
    instances[slot]=instance

task=unreal.AssetImportTask()
task.filename=str(source/record["fbx"])
task.destination_path=prop_path
task.destination_name=name
task.automated=True
task.replace_existing=True
task.save=True
options=unreal.FbxImportUI()
options.import_mesh=True
options.import_materials=True
options.import_textures=False
options.import_as_skeletal=False
options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
options.static_mesh_import_data.combine_meshes=True
options.static_mesh_import_data.generate_lightmap_u_vs=False
options.static_mesh_import_data.auto_generate_collision=False
options.static_mesh_import_data.set_editor_property("build_nanite",True)
task.options=options
tools.import_asset_tasks([task])
mesh=assets.load_asset(prop_path+"/"+name)
if not isinstance(mesh,unreal.StaticMesh):
    raise RuntimeError("Nyaagyu cargo static mesh failed import")
slots=[str(entry.material_slot_name) for entry in mesh.get_editor_property("static_materials")]
if sorted(slots)!=record["material_slots"]:
    raise RuntimeError(f"Nyaagyu cargo FBX material slot identities changed: {slots}")
static_subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
nanite=static_subsystem.get_nanite_settings(mesh)
if not nanite.get_editor_property("enabled"):
    raise RuntimeError("Nyaagyu cargo Windows Nanite data was not built")
nanite.set_editor_property("fallback_percent_triangles",1.0)
nanite.set_editor_property("fallback_target",unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
nanite.set_editor_property("generate_fallback",unreal.NaniteGenerateFallback.ENABLED)
static_subsystem.set_nanite_settings(mesh,nanite,True)
nanite=static_subsystem.get_nanite_settings(mesh)
if (not nanite.get_editor_property("enabled")
        or nanite.get_editor_property("fallback_percent_triangles")<.999
        or nanite.get_editor_property("fallback_target")!=unreal.NaniteFallbackTarget.PERCENT_TRIANGLES
        or nanite.get_editor_property("generate_fallback")!=unreal.NaniteGenerateFallback.ENABLED):
    raise RuntimeError("Nyaagyu cargo lost its full conventional Mac fallback")
if static_subsystem.get_lod_count(mesh)<1 or static_subsystem.get_number_verts(mesh,0)<1000:
    raise RuntimeError("Nyaagyu cargo conventional fallback LOD0 was not built")
for index,slot in enumerate(slots):
    mesh.set_material(index,instances[slot])
    if mesh.get_material(index).get_path_name()!=instances[slot].get_path_name():
        raise RuntimeError(f"Nyaagyu cargo mesh lost exact {slot} binding")
assets.save_loaded_asset(mesh)
assets.save_directory(destination,only_if_is_dirty=False,recursive=True)
assets.save_directory(prop_path,only_if_is_dirty=False,recursive=True)
unreal.log(f"NYAAGYU_CARGO_READY: {len(textures)} map sets, {len(instances)} material slots, Nanite with full conventional fallback, visual-only collision envelope {record['collision_envelope_m']}")
