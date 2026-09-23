"""Add original prototype skeletons and keyed idle/walk clips to generated cats.

Run after create_original_assets.py. Produces actual skinned FBX assets and keeps
the editable rigs/actions in the .blend. Weights are procedural starting points,
requiring artist refinement before production animation or close-up use.
"""
from pathlib import Path
import math
import json
import bpy

out=Path(__file__).resolve().parents[2]/"Content/SourceArt"
bpy.ops.wm.open_mainfile(filepath=str(out/"SoraArena_OriginalAssets.blend"))
bpy.context.preferences.filepaths.save_version=0


def rig_cat(mesh_name, offset):
    mesh=bpy.data.objects[mesh_name]
    old_rig=mesh.parent if mesh.parent and mesh.parent.type=='ARMATURE' else None
    mesh.parent=None
    for modifier in list(mesh.modifiers):
        if modifier.type=='ARMATURE':mesh.modifiers.remove(modifier)
    mesh.vertex_groups.clear()
    if old_rig:bpy.data.objects.remove(old_rig,do_unlink=True)
    for action in list(bpy.data.actions):
        if action.name.startswith(mesh_name.replace('SM_','RIG_')+'_'):bpy.data.actions.remove(action)
    mesh.hide_set(False);mesh.location=(0,0,0)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.armature_add(enter_editmode=True,location=(0,0,0))
    rig=bpy.context.object;rig.name=mesh_name.replace('SM_','RIG_')
    bones=rig.data.edit_bones
    bones.remove(bones[0])
    def bone(name,head,tail,parent=None):
        b=bones.new(name);b.head=head;b.tail=tail
        if parent:b.parent=bones[parent]
        return b
    bone('root',(0,0,0),(0,0,.20))
    bone('pelvis',(0,0,.65),(0,0,.85),'root')
    bone('spine',(0,0,.85),(0,0,1.19),'pelvis')
    bone('neck',(0,0,1.19),(0,0,1.39),'spine')
    bone('head',(0,0,1.39),(0,0,1.75),'neck')
    bone('tail_01',(-.12,0,.70),(-.30,0,.78),'pelvis')
    bone('tail_02',(-.30,0,.78),(-.48,0,.9),'tail_01')
    bone('tail_03',(-.48,0,.9),(-.63,0,1.03),'tail_02')
    for side,sign in [('L',-1),('R',1)]:
        bone(f'upperarm_{side}',(0,sign*.23,1.24),(.035,sign*.34,1.01),'spine')
        bone(f'forearm_{side}',(.035,sign*.34,1.01),(.085,sign*.38,.83),f'upperarm_{side}')
        bone(f'hand_{side}',(.085,sign*.38,.83),(.09,sign*.39,.73),f'forearm_{side}')
        bone(f'thigh_{side}',(0,sign*.14,.66),(0,sign*.15,.36),'pelvis')
        bone(f'shin_{side}',(0,sign*.15,.36),(0,sign*.15,.10),f'thigh_{side}')
        bone(f'foot_{side}',(0,sign*.15,.10),(.18,sign*.15,.055),f'shin_{side}')
    bpy.ops.object.mode_set(mode='OBJECT')
    for b in rig.data.bones:mesh.vertex_groups.new(name=b.name)
    for vertex in mesh.data.vertices:
        x,y,z=vertex.co;side='L' if y<0 else 'R'
        if x<-.25 and .63<z<1.12: name='tail_01' if x>-.34 else 'tail_02' if x>-.5 else 'tail_03'
        elif z>1.365:name='head'
        elif abs(y)>.275 and z>.7:name=f'hand_{side}' if z<.85 else f'forearm_{side}' if z<1.02 else f'upperarm_{side}'
        elif z<.64:name=f'foot_{side}' if z<.14 else f'shin_{side}' if z<.35 else f'thigh_{side}'
        elif z>1.22:name='neck'
        elif z>.85:name='spine'
        else:name='pelvis'
        mesh.vertex_groups[name].add([vertex.index],1.0,'REPLACE')
    modifier=mesh.modifiers.new('Sora_PrototypeSkin','ARMATURE');modifier.object=rig
    mesh.parent=rig
    rig.animation_data_create()
    actions={}
    for clip,frames in [('Idle',96),('Walk',32)]:
        action=bpy.data.actions.new(rig.name+'_'+clip);action.use_fake_user=True;rig.animation_data.action=action
        for pose in rig.pose.bones:pose.rotation_mode='XYZ';pose.rotation_euler=(0,0,0);pose.location=(0,0,0)
        for frame in range(1,frames+2,4):
            t=(frame-1)/frames*math.tau
            for side,sign in [('L',-1),('R',1)]:
                rig.pose.bones[f'thigh_{side}'].rotation_euler[2]=math.sin(t)*.32*sign if clip=='Walk' else 0
                rig.pose.bones[f'shin_{side}'].rotation_euler[2]=max(0,-math.sin(t)*sign)*.40 if clip=='Walk' else 0
                rig.pose.bones[f'upperarm_{side}'].rotation_euler[2]=-math.sin(t)*.18*sign if clip=='Walk' else math.sin(t)*.008
            rig.pose.bones['pelvis'].location[1]=abs(math.sin(t))*.014 if clip=='Walk' else math.sin(t)*.004
            rig.pose.bones['spine'].rotation_euler[0]=math.sin(t)*.012
            rig.pose.bones['tail_02'].rotation_euler[0]=math.sin(t)*.12
            for pose in rig.pose.bones:
                pose.keyframe_insert(data_path='rotation_euler',frame=frame,group=pose.name)
                pose.keyframe_insert(data_path='location',frame=frame,group=pose.name)
        actions[clip]=action
        bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=frames+1;bpy.context.scene.frame_set(1)
        bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        filename=mesh_name.replace('SM_','SK_') if clip=='Idle' else mesh_name.replace('SM_','A_')+'_Walk'
        bpy.ops.export_scene.fbx(filepath=str(out/(filename+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
            axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,use_armature_deform_only=True,
            bake_anim=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_simplify_factor=0)
    rig.animation_data.action=actions['Idle'];rig.location=(0,offset,0)
    assert len(rig.data.bones)==20
    assert all(len(vertex.groups)>0 for vertex in mesh.data.vertices), 'Unweighted vertices in prototype skin'
    return rig

rig_cat('SM_NyaagyuSamurai',-.6)
rig_cat('SM_AlienBanker',.7)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'SoraArena_OriginalAssets.blend'))
manifest=json.loads((out/'manifest.json').read_text())
manifest['skeletal_characters']=['SK_NyaagyuSamurai','SK_AlienBanker']
manifest['walk_animations']=['A_NyaagyuSamurai_Walk','A_AlienBanker_Walk']
manifest['rig_status']='Original 20-bone prototype rigs with skin weights and keyed idle/walk clips; deformation needs artist refinement.'
manifest['limitations']=['Prototype anatomy and short geometric fur cards, not production grooming','Procedural cloth and rigid per-region skin weights need refinement','No photorealism or performance qualification','Skeletal asset loading and idle/walk switching are implemented in the UE pawn; engine import and playback verification remain pending']
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('SORA_RIGS_COMPLETE: two skinned cats, two idle clips, two walk clips')
