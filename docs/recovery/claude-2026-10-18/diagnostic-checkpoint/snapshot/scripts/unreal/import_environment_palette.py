"""Import the pinned CC0 Nyaagyu production palette in Unreal Engine 5.8.3.

Creates world-aligned PBR material instances with real-world texture scale, DX
normal maps and correctly unpacked AO/Roughness/Metallic maps. No website assets
are fetched in the game or editor; the manifest-pinned source files must exist.
"""
from pathlib import Path
import hashlib
import json
import runpy
import unreal

if not unreal.SystemLibrary.get_engine_version().startswith('5.8.3'):
    raise RuntimeError('This asset authoring script requires Unreal Engine 5.8.3')
ROOT=Path(unreal.Paths.project_dir()).resolve()
SOURCE=ROOT/'Content/SourceArt/Environment/PolyHaven'
manifest=json.loads((SOURCE/'manifest.json').read_text())
assert manifest['asset_license']=='CC0-1.0'
roof=json.loads((SOURCE/'GreyRoofTiles/manifest.json').read_text())
if (roof['asset_id']!='grey_roof_tiles' or roof['role']!='kawara'
        or roof['license']!='CC0-1.0' or roof['tile_size_cm']!=300.0):
    raise RuntimeError('Pinned CC0 kawara surface identity changed')
plaster=json.loads((SOURCE/'WhitePlaster02/manifest.json').read_text())
if (plaster['asset_id']!='white_plaster_02' or plaster['role']!='plaster'
        or plaster['license']!='CC0-1.0' or plaster['tile_size_cm']!=100.0
        or plaster['unreal_instance']!='/Game/Generated/Environment/MI_Nyaagyu_Plaster.MI_Nyaagyu_Plaster'):
    raise RuntimeError('Pinned CC0 white plaster surface identity changed')
surface_assets=manifest['assets']+[roof,plaster]
assets=unreal.EditorAssetLibrary;tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
DEST='/Game/Generated/Environment'
assets.make_directory(DEST+'/Textures')
textures={}
for record in surface_assets:
    textures[record['role']]={}
    for file in record['files']:
        folder=('GreyRoofTiles' if record['role']=='kawara' else
                'WhitePlaster02' if record['role']=='plaster' else '')
        source=SOURCE/folder/file['file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=file['sha256']:
            raise RuntimeError('Source asset hash mismatch: '+str(source))
        name='T_NyaagyuOvercast' if file['channel']=='hdri' else f"T_{record['role'].title()}_{file['channel']}"
        task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=DEST+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=True;task.save=True;tools.import_asset_tasks([task])
        texture=assets.load_asset(DEST+'/Textures/'+name)
        if texture is None:raise RuntimeError('Texture import failed: '+name)
        if file['channel']=='hdri':
            if not isinstance(texture,unreal.TextureCube):raise RuntimeError('Overcast HDR must import as a TextureCube')
        else:
            texture.set_editor_property('srgb',file['channel']=='Diffuse')
            if file['channel']=='nor_dx':
                texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property('flip_green_channel',False)
            elif file['channel']=='arm':texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
            texture.set_editor_property('max_texture_size',int(record['resolution'][:-1])*1024)
        assets.save_loaded_asset(texture)
        textures[record['role']][file['channel']]=texture


def create_material(name):
    path=DEST+'/'+name
    mat=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(mat)
    return mat


def node(mat,cls,x,y,**properties):
    result=lib.create_material_expression(mat,cls,x,y)
    for key,value in properties.items():result.set_editor_property(key,value)
    return result


def link(a,out,b,pin):
    if not lib.connect_material_expressions(a,out,b,pin):raise RuntimeError(f'Material connection failed: {out} -> {pin}')


def output(a,pin,prop):
    if not lib.connect_material_property(a,pin,prop):raise RuntimeError(f'Material output failed: {prop}')

mat=create_material('M_Nyaagyu_PBR')
mat.set_editor_property('tangent_space_normal',False)
tile=node(mat,unreal.MaterialExpressionVectorParameter,-1100,-450,parameter_name='TileSize',default_value=unreal.LinearColor(200,200,200,1))
tint=node(mat,unreal.MaterialExpressionVectorParameter,-550,-500,parameter_name='Tint',default_value=unreal.LinearColor(1,1,1,1))
projected={}
for index,(parameter,channel) in enumerate([('AlbedoMap','Diffuse'),('NormalMap','nor_dx'),('ARMMap','arm')]):
    obj=node(mat,unreal.MaterialExpressionTextureObjectParameter,-1100,index*260,parameter_name=parameter,texture=textures['timber'][channel])
    call=node(mat,unreal.MaterialExpressionMaterialFunctionCall,-750,index*260)
    function_name='WorldAlignedNormal' if channel=='nor_dx' else 'WorldAlignedTexture'
    function=assets.load_asset('/Engine/Functions/Engine_MaterialFunctions01/Texturing/'+function_name)
    if function is None or not call.set_material_function(function):raise RuntimeError('Missing world-aligned material function '+function_name)
    link(obj,'',call,'TextureObject');link(tile,'RGB',call,'TextureSize');projected[channel]=call
colored=node(mat,unreal.MaterialExpressionMultiply,-250,-200)
link(projected['Diffuse'],'XYZ Texture',colored,'A');link(tint,'RGB',colored,'B')
vertex=node(mat,unreal.MaterialExpressionVertexColor,-550,-760)
vertex_rgb=node(mat,unreal.MaterialExpressionComponentMask,-360,-600,
                r=True,g=True,b=True,a=False)
link(vertex,'',vertex_rgb,'')
macro_strength=node(mat,unreal.MaterialExpressionScalarParameter,-330,-760,
                    parameter_name='TerrainVertexTint',default_value=0.0)
macro_colored=node(mat,unreal.MaterialExpressionMultiply,0,-440)
link(colored,'',macro_colored,'A');link(vertex_rgb,'',macro_colored,'B')
macro_blend=node(mat,unreal.MaterialExpressionLinearInterpolate,200,-200)
link(colored,'',macro_blend,'A');link(macro_colored,'',macro_blend,'B')
link(macro_strength,'',macro_blend,'Alpha')
output(macro_blend,'',unreal.MaterialProperty.MP_BASE_COLOR)
output(projected['nor_dx'],'XYZ Texture',unreal.MaterialProperty.MP_NORMAL)
for index,(component,prop) in enumerate([('r',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),('g',unreal.MaterialProperty.MP_ROUGHNESS),('b',unreal.MaterialProperty.MP_METALLIC)]):
    mask=node(mat,unreal.MaterialExpressionComponentMask,-250,index*120+160,r=component=='r',g=component=='g',b=component=='b',a=False)
    link(projected['arm'],'XYZ Texture',mask,'')
    if component=='g':
        # Vertex alpha is a source-authored dampness mask. Non-terrain
        # instances leave TerrainVertexTint at zero, so their roughness stays
        # exactly on the scanned material's ARM green channel.
        enabled_damp=node(mat,unreal.MaterialExpressionMultiply,-380,590)
        link(vertex,'A',enabled_damp,'A')
        link(macro_strength,'',enabled_damp,'B')
        damp_amount=node(mat,unreal.MaterialExpressionScalarParameter,-620,790,
                         parameter_name='TerrainDampRoughness',default_value=.30)
        damp_reduction=node(mat,unreal.MaterialExpressionMultiply,-140,590)
        link(enabled_damp,'',damp_reduction,'A')
        link(damp_amount,'',damp_reduction,'B')
        dry_fraction=node(mat,unreal.MaterialExpressionOneMinus,40,590)
        link(damp_reduction,'',dry_fraction,'')
        wet_roughness=node(mat,unreal.MaterialExpressionMultiply,250,590)
        link(mask,'',wet_roughness,'A')
        link(dry_fraction,'',wet_roughness,'B')
        output(wet_roughness,'',prop)
    else:
        output(mask,'',prop)
lib.layout_material_expressions(mat);lib.recompile_material(mat);assets.save_loaded_asset(mat)
if set(str(name) for name in lib.get_texture_parameter_names(mat)) != {'AlbedoMap','NormalMap','ARMMap'}:
    raise RuntimeError('The world-aligned material texture parameters are incomplete')

for record in surface_assets:
    if record['role']=='sky':continue
    name='MI_Nyaagyu_'+record['role'].title();path=DEST+'/'+name
    instance=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,DEST,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    lib.set_material_instance_parent(instance,mat)
    for param,channel in [('AlbedoMap','Diffuse'),('NormalMap','nor_dx'),('ARMMap','arm')]:
        expected=textures[record['role']][channel]
        lib.set_material_instance_texture_parameter_value(instance,param,expected)
        actual=lib.get_material_instance_texture_parameter_value(instance,param)
        if actual is None or actual.get_path_name()!=expected.get_path_name():
            raise RuntimeError('Texture parameter did not bind: '+param+' for '+record['role'])
    size=record['tile_size_cm'];lib.set_material_instance_vector_parameter_value(instance,'TileSize',unreal.LinearColor(size,size,size,1))
    assets.save_loaded_asset(instance)

# Only terrain receives world-space vertex macro tint. Architectural stone and
# soil instances keep the photographed palette unchanged.
for role in ('Soil','Stone'):
    name='MI_Nyaagyu_Terrain'+role
    path=DEST+'/'+name
    instance=assets.load_asset(path) if assets.does_asset_exist(path) else tools.create_asset(name,DEST,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    base=assets.load_asset(DEST+'/MI_Nyaagyu_'+role)
    lib.set_material_instance_parent(instance,base)
    lib.set_material_instance_scalar_parameter_value(instance,'TerrainVertexTint',1.0)
    lib.set_material_instance_scalar_parameter_value(instance,'TerrainDampRoughness',.30)
    if abs(lib.get_material_instance_scalar_parameter_value(instance,'TerrainVertexTint')-1.0)>1e-5:
        raise RuntimeError('Terrain vertex macro tint did not bind: '+name)
    if abs(lib.get_material_instance_scalar_parameter_value(instance,'TerrainDampRoughness')-.30)>1e-5:
        raise RuntimeError('Terrain vertex dampness did not bind: '+name)
    assets.save_loaded_asset(instance)

# The irregular estate pathway is a terrain-only scan. Architectural stone
# continues to use the separate, measured foundation palette above.
terrain_root=ROOT/'Content/SourceArt/Environment/NyaagyuTerrain'
terrain_manifest=json.loads((terrain_root/'manifest.json').read_text())
pathway=terrain_manifest.get('stone_pathway_scan',{})
if (pathway.get('asset_id')!='grey_stone_path'
        or pathway.get('source_url')!='https://polyhaven.com/a/grey_stone_path'
        or pathway.get('license')!='CC0-1.0'
        or pathway.get('tile_size_cm')!=180
        or [item.get('channel') for item in pathway.get('files',[])]!=
        ['Diffuse','nor_dx','arm','disp']):
    raise RuntimeError('Pinned CC0 estate stone pathway source identity changed')
pathway_textures={}
for entry in pathway['files']:
    source_file=(terrain_root/entry['file']).resolve()
    if (not source_file.is_relative_to(terrain_root.resolve())
            or not source_file.is_file()
            or hashlib.sha256(source_file.read_bytes()).hexdigest()!=entry['sha256']):
        raise RuntimeError('Stone pathway scan missing or changed: '+str(source_file))
    channel=entry['channel']
    name='T_TerrainGreyStonePath_'+channel
    task=unreal.AssetImportTask()
    task.filename=str(source_file)
    task.destination_path=DEST+'/Textures'
    task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=True
    tools.import_asset_tasks([task])
    texture=assets.load_asset(DEST+'/Textures/'+name)
    if not isinstance(texture,unreal.Texture2D):
        raise RuntimeError('Estate stone pathway texture import failed: '+name)
    texture.set_editor_property('srgb',channel=='Diffuse')
    if channel=='nor_dx':
        texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property('flip_green_channel',False)
    elif channel=='arm':
        texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('max_texture_size',2048)
    assets.save_loaded_asset(texture)
    pathway_textures[channel]=texture
terrain_stone=assets.load_asset(DEST+'/MI_Nyaagyu_TerrainStone')
for parameter,channel in [('AlbedoMap','Diffuse'),('NormalMap','nor_dx'),('ARMMap','arm')]:
    lib.set_material_instance_texture_parameter_value(terrain_stone,parameter,pathway_textures[channel])
    actual=lib.get_material_instance_texture_parameter_value(terrain_stone,parameter)
    if actual is None or actual.get_path_name()!=pathway_textures[channel].get_path_name():
        raise RuntimeError('Estate pathway scan did not bind: '+parameter)
size=pathway['tile_size_cm']
lib.set_material_instance_vector_parameter_value(terrain_stone,'TileSize',unreal.LinearColor(size,size,size,1))
assets.save_loaded_asset(terrain_stone)

sky=create_material('M_Nyaagyu_Sky')
sky.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
sky.set_editor_property('two_sided',True);sky.set_editor_property('is_sky',True)
position=node(sky,unreal.MaterialExpressionWorldPosition,-800,-200)
camera=node(sky,unreal.MaterialExpressionCameraPositionWS,-800,50)
direction=node(sky,unreal.MaterialExpressionSubtract,-550,-100)
link(position,'XYZ',direction,'A');link(camera,'',direction,'B')
normal=node(sky,unreal.MaterialExpressionNormalize,-350,-100);link(direction,'',normal,'')
cube=node(sky,unreal.MaterialExpressionTextureSampleParameterCube,-100,-100,parameter_name='SkyTexture',texture=textures['sky']['hdri'])
link(normal,'',cube,'');output(cube,'RGB',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.layout_material_expressions(sky);lib.recompile_material(sky);assets.save_loaded_asset(sky)
assets.save_directory(DEST,only_if_is_dirty=False,recursive=True)
runpy.run_path(str(ROOT/'scripts/unreal/import_torii_lacquer_pbr.py'),run_name='__main__')
unreal.log('NYAAGYU_PBR_READY: 6 real-scale CC0 materials, terrain-only stone pathway, kawara and plaster + overcast HDRI. Powered by Poly Haven — https://polyhaven.com')
