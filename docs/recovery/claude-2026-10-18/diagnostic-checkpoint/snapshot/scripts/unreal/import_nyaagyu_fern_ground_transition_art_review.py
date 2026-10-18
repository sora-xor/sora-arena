"""Strict UE 5.8.2 Fern 02 ground-transition import, isolated to ArtReview.

Requires import_nyaagyu_fern_art_review.py to have run first. No level,
WorldBuilder, gameplay collision, or player-save data is changed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import unreal


version=unreal.SystemLibrary.get_engine_version()
if not version.startswith("5.8.3"):
    raise RuntimeError(f"Fern ground transition requires pinned UE 5.8.2; got {version}")
root=Path(unreal.Paths.project_dir()).resolve()
source=root/"Content/SourceArt/Environment/PolyHaven/Fern02/GroundTransition"
record_path=source/"manifest.json"
EXPECTED_MANIFEST_SHA256="19033f5b5aec4e86531c86e2c1ae84849553abc3bdb5e9b41ace10dfef4ff5e3"


def sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


if sha(record_path)!=EXPECTED_MANIFEST_SHA256:
    raise RuntimeError("Fern ground-transition source manifest changed")
record=json.loads(record_path.read_text())
if (record["schema_version"]!=1
        or record["name"]!="SM_NyaagyuFernGroundTransition"
        or record["generator"]!="scripts/art/create_nyaagyu_fern_ground_transition.py"
        or record["generator_sha256"]!=sha(root/record["generator"])
        or record["gameplay_collision"] is not False
        or record["nanite_windows"] is not True
        or record["recommended_review_origin_cm"]!=[-1950,335,0]
        or len(record["placements_local_m"])!=6
        or sha(source/record["source_blend"])!=record["source_blend_sha256"]
        or sha(root/"Content/SourceArt/Environment/PolyHaven/Fern02/manifest.json")!=record["fern_source_manifest_sha256"]
        or sha(root/"Content/SourceArt/Environment/NyaagyuGroundDressing/manifest.json")!=record["ground_dressing_manifest_sha256"]):
    raise RuntimeError("Fern ground-transition art/collision identity changed")
for tier,item in record["previews"].items():
    if tier not in ("hi","mac_lod1") or sha(source/item["file"])!=item["sha256"]:
        raise RuntimeError("Fern ground-transition source preview changed")
if set(record["scan_dependencies"])!={"DampSilt","ForestLitter","RiverStone"}:
    raise RuntimeError("Fern ground-transition scan set changed")
for dep in record["scan_dependencies"].values():
    if dep["license"]!="CC0-1.0" or not dep["source_url"].startswith("https://polyhaven.com/a/"):
        raise RuntimeError("Fern ground-transition surface rights changed")
    if set(dep["files"])!={"Albedo","NormalDX","ORM"}:
        raise RuntimeError("Fern ground-transition PBR channels changed")
    for file in dep["files"].values():
        path=(root/file["repo_path"]).resolve()
        if (not path.is_relative_to(root/"Content/SourceArt/Environment")
                or sha(path)!=file["sha256"]
                or not file["upstream_url"].startswith("https://dl.polyhaven.org/")):
            raise RuntimeError(f"Fern ground-transition PBR source changed: {path}")
mac_config=(root/"Config/Mac/MacEngine.ini").read_text()
if "r.Nanite=0" not in mac_config or "r.Nanite.ProxyRenderMode=0" not in mac_config:
    raise RuntimeError("Mac conventional fallback policy changed")

dest="/Game/Generated/ArtReview/Fern02/GroundTransition"
tex_dest=dest+"/Textures"
mat_dest=dest+"/Materials"
mesh_dest=dest+"/Meshes"
assets=unreal.EditorAssetLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.MaterialEditingLibrary
for folder in (dest,tex_dest,mat_dest,mesh_dest):
    assets.make_directory(folder)


def import_asset(file,folder,name,options=None):
    task=unreal.AssetImportTask()
    task.filename=str(file)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=True
    if options is not None: task.options=options
    tools.import_asset_tasks([task])
    asset=assets.load_asset(f"{folder}/{name}")
    if not asset: raise RuntimeError(f"Fern ground-transition import failed: {file}")
    return asset


textures={}
for surface,dep in record["scan_dependencies"].items():
    textures[surface]={}
    for channel,file in dep["files"].items():
        path=root/file["repo_path"]
        name=f"T_FernGround_{surface}_{channel}"
        texture=import_asset(path,tex_dest,name)
        if not isinstance(texture,unreal.Texture2D):
            raise RuntimeError(f"Fern ground-transition texture not 2D: {name}")
        texture.set_editor_property("srgb",channel=="Albedo")
        if channel=="NormalDX":
            texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel",False)
        elif channel=="ORM":
            texture.set_editor_property("compression_settings",unreal.TextureCompressionSettings.TC_MASKS)
        texture.set_editor_property("max_texture_size",2048)
        assets.save_loaded_asset(texture)
        textures[surface][channel]=texture


def expr(material,cls,x,y,**settings):
    node=lib.create_material_expression(material,cls,x,y)
    for key,value in settings.items(): node.set_editor_property(key,value)
    return node


masters={}
for masked in (False,True):
    name="M_FernGround_MaskedPBR" if masked else "M_FernGround_OpaquePBR"
    path=f"{mat_dest}/{name}"
    material=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name,mat_dest,unreal.Material,unreal.MaterialFactoryNew())
    for old in list(lib.get_material_expressions(material)):
        lib.delete_material_expression(material,old)
    if lib.get_num_material_expressions(material):
        raise RuntimeError(f"Fern ground-transition retained material nodes: {name}")
    material.set_editor_property("two_sided",True)
    material.set_editor_property("blend_mode",unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
    if masked: material.set_editor_property("opacity_mask_clip_value",.5)
    albedo=expr(material,unreal.MaterialExpressionTextureSampleParameter2D,-850,-360,
                parameter_name="AlbedoMap",texture=textures["DampSilt"]["Albedo"])
    normal=expr(material,unreal.MaterialExpressionTextureSampleParameter2D,-850,-80,
                parameter_name="NormalMap",texture=textures["DampSilt"]["NormalDX"])
    orm=expr(material,unreal.MaterialExpressionTextureSampleParameter2D,-850,220,
             parameter_name="ORMMap",texture=textures["DampSilt"]["ORM"])
    tint=expr(material,unreal.MaterialExpressionVectorParameter,-550,-530,
              parameter_name="Tint",default_value=unreal.LinearColor(1,1,1,1))
    multiply=expr(material,unreal.MaterialExpressionMultiply,-290,-310)
    if not lib.connect_material_expressions(albedo,"RGB",multiply,"A") or not lib.connect_material_expressions(tint,"RGB",multiply,"B"):
        raise RuntimeError("Fern ground-transition tint graph failed")
    for node,pin,output in (
        (multiply,"",unreal.MaterialProperty.MP_BASE_COLOR),
        (normal,"RGB",unreal.MaterialProperty.MP_NORMAL),
        (orm,"R",unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
        (orm,"G",unreal.MaterialProperty.MP_ROUGHNESS),
        (orm,"B",unreal.MaterialProperty.MP_METALLIC),
    ):
        if not lib.connect_material_property(node,pin,output):
            raise RuntimeError(f"Fern ground-transition material graph failed: {name}/{output}")
    if masked:
        color=expr(material,unreal.MaterialExpressionVertexColor,-500,520)
        if not lib.connect_material_property(color,"A",unreal.MaterialProperty.MP_OPACITY_MASK):
            raise RuntimeError("Fern ground-transition edge opacity failed")
    lib.layout_material_expressions(material)
    lib.recompile_material(material)
    assets.save_loaded_asset(material)
    if {str(x) for x in lib.get_texture_parameter_names(material)}!={"AlbedoMap","NormalMap","ORMMap"}:
        raise RuntimeError("Fern ground-transition PBR pins missing")
    masters["masked" if masked else "opaque"]=material


definitions={
    "M_FernGround_Soil":("DampSilt",(.50,.50,.49),"masked"),
    "M_FernGround_Litter":("ForestLitter",(.68,.65,.61),"masked"),
    "M_FernGround_Stone":("RiverStone",(.73,.71,.66),"opaque"),
    "M_FernGround_Root":("ForestLitter",(.48,.38,.31),"opaque"),
}
instances={}
for slot,(surface,tint,blend) in definitions.items():
    name="MI_"+slot.removeprefix("M_")
    path=f"{mat_dest}/{name}"
    instance=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(
        name,mat_dest,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,masters[blend])
    for parameter,channel in (("AlbedoMap","Albedo"),("NormalMap","NormalDX"),("ORMMap","ORM")):
        expected=textures[surface][channel]
        lib.set_material_instance_texture_parameter_value(instance,parameter,expected)
        actual=lib.get_material_instance_texture_parameter_value(instance,parameter)
        if not actual or actual.get_path_name()!=expected.get_path_name():
            raise RuntimeError(f"Fern ground-transition exact PBR binding failed: {name}/{parameter}")
    lib.set_material_instance_vector_parameter_value(instance,"Tint",unreal.LinearColor(*tint,1))
    assets.save_loaded_asset(instance)
    instances[slot]=instance

# The Fern 02 importer pins official separate alpha maps. Check that this
# combined asset consumes those exact 4K/2K instances, not a JPEG alpha guess.
for tier in ("4K","2K"):
    instance=assets.load_asset(f"/Game/Generated/ArtReview/Fern02/Materials/MI_Fern02_{tier}")
    expected=assets.load_asset(f"/Game/Generated/ArtReview/Fern02/Textures/T_Fern02_{tier}_ALPHA")
    if not instance or not expected:
        raise RuntimeError("Import the pinned Fern 02 art-review materials before the ground transition")
    bound=lib.get_material_instance_texture_parameter_value(instance,"AlphaMap")
    if not bound or bound.get_path_name()!=expected.get_path_name():
        raise RuntimeError(f"Fern ground-transition alpha binding failed: {tier}")
    instances["M_Fern02_"+tier]=instance

mesh_records=record["meshes"]
if set(mesh_records)!={"hi","mac_lod1"}:
    raise RuntimeError("Fern ground-transition mesh tiers changed")
subsystem=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for tier,item in mesh_records.items():
    suffix="HI" if tier=="hi" else "MAC_LOD1"
    name=record["name"]+"_"+suffix
    if (item["fbx"]!=name+".fbx" or sha(source/item["fbx"])!=item["sha256"]
            or item["nanite_candidate"]!=(tier=="hi")
            or item["triangles"]<7000
            or item["bounds_m"]["max"][2]>.55
            or item["bounds_m"]["min"][2]<-.02):
        raise RuntimeError(f"Fern ground-transition geometry/collision envelope changed: {name}")
    options=unreal.FbxImportUI()
    options.import_mesh=True
    options.import_materials=False
    options.import_textures=False
    options.import_as_skeletal=False
    options.mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes=True
    options.static_mesh_import_data.generate_lightmap_u_vs=False
    options.static_mesh_import_data.auto_generate_collision=False
    options.static_mesh_import_data.set_editor_property("vertex_color_import_option",unreal.VertexColorImportOption.REPLACE)
    options.static_mesh_import_data.set_editor_property("build_nanite",tier=="hi")
    mesh=import_asset(source/item["fbx"],mesh_dest,name,options)
    if not isinstance(mesh,unreal.StaticMesh):
        raise RuntimeError(f"Fern ground-transition mesh import failed: {name}")
    slots=[str(slot.get_editor_property("material_slot_name")) for slot in mesh.get_editor_property("static_materials")]
    if slots!=item["material_slots"]:
        raise RuntimeError(f"Fern ground-transition material slots changed: {name}: {slots}")
    if subsystem.get_lod_count(mesh)<1 or subsystem.get_number_verts(mesh,0)<3000:
        raise RuntimeError(f"Fern ground-transition geometry failed to build: {name}")
    nanite=subsystem.get_nanite_settings(mesh)
    if bool(nanite.get_editor_property("enabled"))!=(tier=="hi"):
        raise RuntimeError(f"Fern ground-transition Nanite tier mismatch: {name}")
    if tier=="hi":
        nanite.set_editor_property("fallback_target",unreal.NaniteFallbackTarget.PERCENT_TRIANGLES)
        nanite.set_editor_property("fallback_percent_triangles",1.0)
        nanite.set_editor_property("generate_fallback",unreal.NaniteGenerateFallback.ENABLED)
        subsystem.set_nanite_settings(mesh,nanite,True)
        nanite=subsystem.get_nanite_settings(mesh)
        if (nanite.get_editor_property("fallback_percent_triangles")<.999
                or nanite.get_editor_property("generate_fallback")!=unreal.NaniteGenerateFallback.ENABLED):
            raise RuntimeError("Fern ground-transition full conventional fallback lost")
    for index,slot in enumerate(slots):
        expected=instances[slot]
        mesh.set_material(index,expected)
        actual=mesh.get_material(index)
        if not actual or actual.get_path_name()!=expected.get_path_name():
            raise RuntimeError(f"Fern ground-transition material assignment failed: {name}/{slot}")
    assets.save_loaded_asset(mesh)

assets.save_directory(dest,only_if_is_dirty=False,recursive=True)
unreal.log("NYAAGYU_FERN_GROUND_TRANSITION_ART_REVIEW_READY: scanned fern/soil/litter/stone PBR; Nanite HI and conventional Mac LOD; no WorldBuilder placement")
