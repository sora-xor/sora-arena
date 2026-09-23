"""Render a source-asset material check using the downloaded production maps.

This is a Blender material preview, not an Unreal game screenshot. No remote
preview images are used. Powered by Poly Haven: https://polyhaven.com
"""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'Content/SourceArt/Environment/PolyHaven'
manifest=json.loads((SOURCE/'manifest.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials={}
for asset in manifest['assets']:
    if asset['role']=='sky':
        sky_file=SOURCE/asset['files'][0]['file'];continue
    material=bpy.data.materials.new('PBR_'+asset['role']);material.use_nodes=True
    nodes=material.node_tree.nodes;links=material.node_tree.links;shader=nodes.get('Principled BSDF')
    images={}
    for file in asset['files']:
        image=bpy.data.images.load(str(SOURCE/file['file']))
        image.colorspace_settings.name='sRGB' if file['channel']=='Diffuse' else 'Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=image;images[file['channel']]=node
    links.new(images['Diffuse'].outputs['Color'],shader.inputs['Base Color'])
    arm=nodes.new('ShaderNodeSeparateColor');links.new(images['arm'].outputs['Color'],arm.inputs['Color'])
    links.new(arm.outputs['Green'],shader.inputs['Roughness']);links.new(arm.outputs['Blue'],shader.inputs['Metallic'])
    normal_channels=nodes.new('ShaderNodeSeparateColor');links.new(images['nor_dx'].outputs['Color'],normal_channels.inputs['Color'])
    flip=nodes.new('ShaderNodeMath');flip.operation='SUBTRACT';flip.inputs[0].default_value=1
    links.new(normal_channels.outputs['Green'],flip.inputs[1])
    rgb=nodes.new('ShaderNodeCombineColor');links.new(normal_channels.outputs['Red'],rgb.inputs['Red']);links.new(flip.outputs[0],rgb.inputs['Green']);links.new(normal_channels.outputs['Blue'],rgb.inputs['Blue'])
    normal=nodes.new('ShaderNodeNormalMap');links.new(rgb.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    materials[asset['role']]=material

for i,role in enumerate(['timber','stone','soil','metal']):
    x=(i-1.5)*2.3
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,0,.95))
    cube=bpy.context.object;cube.name='Palette_'+role;cube.dimensions=(1.85,1.85,1.9)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=cube.modifiers.new('Small_real_edges','BEVEL');mod.width=.055;mod.segments=4
    cube.data.materials.append(materials[role])
    bpy.ops.object.text_add(location=(x,-1.08,.10),rotation=(math.pi/2,0,0))
    label=bpy.context.object;label.data.body=role.upper();label.data.align_x='CENTER';label.data.size=.22
    label_mat=bpy.data.materials.new('Label_'+role);label_mat.diffuse_color=(.06,.065,.055,1);label.data.materials.append(label_mat)

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025))
floor=bpy.context.object;floor.name='Neutral_preview_floor'
neutral=bpy.data.materials.new('Neutral');neutral.diffuse_color=(.16,.17,.16,1);neutral.use_nodes=True
neutral.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.16,.17,.16,1)
neutral.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72
floor.data.materials.append(neutral)
world=bpy.context.scene.world;world.use_nodes=True
env=world.node_tree.nodes.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(sky_file))
world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs['Color'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.85
bpy.ops.object.camera_add(location=(5.5,-10,6.8))
camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,.8))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=11.3
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.filepath=str(SOURCE/'Nyaagyu_PBR_Palette_Preview.png')
bpy.ops.render.render(write_still=True)
print('NYAAGYU_SOURCE_PALETTE_RENDERED — Blender preview, not Unreal runtime')
