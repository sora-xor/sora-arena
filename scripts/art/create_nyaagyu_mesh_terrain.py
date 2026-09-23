"""Author seam-matched Nyaagyu Estate terrain meshes, dense and conventional.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_mesh_terrain.py

The generated FBXs are local-origin source meshes for a proposed 4x4 ground
layout, NOT compiled UE Mesh Terrain sections. See the adjacent README.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Environment/NyaagyuTerrain"
OUT.mkdir(parents=True,exist_ok=True)
PALETTE=ROOT/"Content/SourceArt/Environment/PolyHaven"
PALETTE_MANIFEST=json.loads((PALETTE/"manifest.json").read_text())
assert PALETTE_MANIFEST["asset_license"]=="CC0-1.0"
BLEND=OUT/"Nyaagyu_Estate_MeshTerrain_Source.blend"
PREVIEW=OUT/"Nyaagyu_Estate_MeshTerrain_Blender.png"
DETAIL_PREVIEW=OUT/"Nyaagyu_Estate_StonePath_Detail_Blender.png"
MANIFEST=OUT/"manifest.json"
WORLD_X_M=64.0
WORLD_Y_M=52.0
TILES_X=TILES_Y=4
TILE_X_M=WORLD_X_M/TILES_X
TILE_Y_M=WORLD_Y_M/TILES_Y
GRID={"hi":(128,104),"mac":(32,26)}  # 12.5 cm / 50 cm quad edges
MATERIALS={"soil":("brown_mud_leaves_01",1.30),
           "stone":("grey_stone_path",1.80)}
SITES=[(-12.5,-7.0),(0.0,10.0),(12.5,-8.0)]
STONE_PATHWAY_SCAN={
    "asset_id":"grey_stone_path",
    "source_url":"https://polyhaven.com/a/grey_stone_path",
    "license":"CC0-1.0",
    "tile_size_cm":180,
    "files":[
        {"channel":"Diffuse","file":"GreyStonePath/grey_stone_path_diff_2k.jpg",
         "sha256":"bf405e4e8a2d720976f710c4bb6de7734bc0bea613657e6c9362d3716418cc51",
         "upstream_md5":"686579822b7b6c1c4600a738156328d4","bytes":3569941},
        {"channel":"nor_dx","file":"GreyStonePath/grey_stone_path_nor_dx_2k.png",
         "sha256":"51d7936c326ed7a2582f700109ba0a53b9a8b588d664b48ab11f3a7d3af225e4",
         "upstream_md5":"796ad56cddc2d31c987b47cca16809d4","bytes":22777736},
        {"channel":"arm","file":"GreyStonePath/grey_stone_path_arm_2k.png",
         "sha256":"58e43f2a4daad0503b74347b5e7b07b2d92d0fbe56d707ba225269e5442f8d4b",
         "upstream_md5":"69027c0e579a18c4a7e944552463bc63","bytes":16048111},
        {"channel":"disp","file":"GreyStonePath/grey_stone_path_disp_2k.png",
         "sha256":"648b48ccbd497ba28100e56baa6eee10d5d37d66156816bafd79548c4295298b",
         "upstream_md5":"effeebe2b7feea91d9e7e480e74d4590","bytes":6510319},
    ],
}

bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.unit_settings.scale_length=1.0
high_collection=bpy.data.collections.new("EstateTerrain_HighDensity_NaniteCandidate")
mac_collection=bpy.data.collections.new("EstateTerrain_ConventionalMacCandidate")
scene.collection.children.link(high_collection)
scene.collection.children.link(mac_collection)
mac_collection.hide_render=True


def tex_record(asset_id,marker):
    record=next(a for a in PALETTE_MANIFEST["assets"] if a["asset_id"]==asset_id)
    item=next(f for f in record["files"] if marker in f["file"])
    path=PALETTE/item["file"]
    assert path.is_file() and path.stat().st_size==item["bytes"]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item["sha256"]
    return path,item


def stone_pathway_file(channel):
    record=next(item for item in STONE_PATHWAY_SCAN["files"]
                if item["channel"]==channel)
    path=OUT/record["file"]
    assert path.is_file() and path.stat().st_size==record["bytes"]
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==record["sha256"]
    assert hashlib.md5(data).hexdigest()==record["upstream_md5"]
    return path


source_files=[]
def terrain_material(role,asset_id):
    mat=bpy.data.materials.new("M_Terrain_"+role.capitalize()+"_PolyHaven")
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value=.83 if role=="soil" else .71
    links=mat.node_tree.links
    images={}
    for channel,marker in (("diffuse","_diff_"),("normal","_nor_dx_"),("arm","_arm_")):
        if role=="stone":
            scan_channel={"diffuse":"Diffuse","normal":"nor_dx","arm":"arm"}[channel]
            path=stone_pathway_file(scan_channel)
        else:
            path,item=tex_record(asset_id,marker)
            source_files.append({"role":role,"channel":channel,
                                 "path":str(path.relative_to(ROOT)),
                                 "sha256":item["sha256"],"bytes":item["bytes"]})
        image=bpy.data.images.load(str(path),check_existing=True)
        image.colorspace_settings.name="sRGB" if channel=="diffuse" else "Non-Color"
        node=mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.name=channel
        node.image=image
        node.interpolation="Linear"
        images[channel]=node
    vertex_tint=mat.node_tree.nodes.new("ShaderNodeVertexColor")
    vertex_tint.layer_name="EstateMacroTint"
    modulate=mat.node_tree.nodes.new("ShaderNodeMixRGB")
    modulate.blend_type="MULTIPLY"
    modulate.inputs[0].default_value=1.0
    links.new(images["diffuse"].outputs["Color"],modulate.inputs[1])
    links.new(vertex_tint.outputs["Color"],modulate.inputs[2])
    links.new(modulate.outputs["Color"],bsdf.inputs["Base Color"])
    arm=mat.node_tree.nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"],arm.inputs["Color"])
    # Source preview interprets the vertex alpha as local dampness. The FBX
    # retains that channel for the terrain-only UE material; ordinary palette
    # instances continue to use the scan's unmodified roughness.
    wet_amount=mat.node_tree.nodes.new("ShaderNodeMath")
    wet_amount.name="TerrainWetnessStrength"
    wet_amount.operation="MULTIPLY"
    wet_amount.inputs[1].default_value=.30 if role=="stone" else .22
    links.new(vertex_tint.outputs["Alpha"],wet_amount.inputs[0])
    dry_fraction=mat.node_tree.nodes.new("ShaderNodeMath")
    dry_fraction.operation="SUBTRACT"
    dry_fraction.inputs[0].default_value=1.0
    links.new(wet_amount.outputs[0],dry_fraction.inputs[1])
    damp_roughness=mat.node_tree.nodes.new("ShaderNodeMath")
    damp_roughness.operation="MULTIPLY"
    links.new(arm.outputs["Green"],damp_roughness.inputs[0])
    links.new(dry_fraction.outputs[0],damp_roughness.inputs[1])
    links.new(damp_roughness.outputs[0],bsdf.inputs["Roughness"])
    links.new(arm.outputs["Blue"],bsdf.inputs["Metallic"])
    # Poly Haven supplies DirectX normal maps. Invert green for Blender's
    # OpenGL-style normal input; UE import should retain the original DX map.
    split=mat.node_tree.nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal"].outputs["Color"],split.inputs["Color"])
    invert=mat.node_tree.nodes.new("ShaderNodeMath")
    invert.operation="SUBTRACT"
    invert.inputs[0].default_value=1.0
    links.new(split.outputs["Green"],invert.inputs[1])
    rgb=mat.node_tree.nodes.new("ShaderNodeCombineColor")
    links.new(split.outputs["Red"],rgb.inputs["Red"])
    links.new(invert.outputs[0],rgb.inputs["Green"])
    links.new(split.outputs["Blue"],rgb.inputs["Blue"])
    normal=mat.node_tree.nodes.new("ShaderNodeNormalMap")
    links.new(rgb.outputs["Color"],normal.inputs["Color"])
    links.new(normal.outputs["Normal"],bsdf.inputs["Normal"])
    for node in images.values():
        links.new(mat.node_tree.nodes.new("ShaderNodeTexCoord").outputs["UV"],
                  node.inputs["Vector"])
    return mat


soil=terrain_material("soil","brown_mud_leaves_01")
stone=terrain_material("stone",None)
# The global architectural stone palette stays untouched. Terrain stone uses
# only the separately catalogued, hash-pinned pathway scan.
displacement_image=bpy.data.images.load(str(stone_pathway_file("disp")),check_existing=True)
displacement_image.colorspace_settings.name="Non-Color"
width,height=displacement_image.size
pixels=np.empty(len(displacement_image.pixels),dtype=np.float32)
displacement_image.pixels.foreach_get(pixels)
displacement_values=pixels.reshape((height,width,4))[:,:,0]
# FBX files retain only slot identities; their PBR maps are rebound to the
# project's already licensed UE palette at import. A plain export material
# prevents Blender's FBX writer from embedding machine-specific Video paths.
soil.name+="_BlenderSource"
stone.name+="_BlenderSource"
export_soil=bpy.data.materials.new("M_Terrain_Soil_PolyHaven")
export_stone=bpy.data.materials.new("M_Terrain_Stone_PolyHaven")
export_soil.diffuse_color=(.23,.19,.13,1)
export_stone.diffuse_color=(.30,.30,.29,1)


def smoothstep(a,b,value):
    t=max(0.0,min(1.0,(value-a)/(b-a)))
    return t*t*(3-2*t)


def value_noise(x,y,cell):
    gx=x/cell;gy=y/cell
    ix=math.floor(gx);iy=math.floor(gy)
    fx=smoothstep(0,1,gx-ix);fy=smoothstep(0,1,gy-iy)
    def corner(cx,cy):
        h=((cx*73856093)^(cy*19349663))&0xffffffff
        h=(h^(h>>13))*1274126177&0xffffffff
        return h/0xffffffff
    a=corner(ix,iy)*(1-fx)+corner(ix+1,iy)*fx
    b=corner(ix,iy+1)*(1-fx)+corner(ix+1,iy+1)*fx
    return a*(1-fy)+b*fy


PUDDLES=((-24.0,-1.75,2.5,.85),(-14.0,1.85,2.0,.75),
         (-3.0,-1.25,3.2,1.0),(8.0,1.75,2.7,.85),
         (19.0,-1.8,2.3,.8),(27.0,1.35,1.9,.7))


def puddle_mask(x,y):
    # Shallow, irregular runoff basins sit off the main footfall line.
    edge=.20*(value_noise(x+.3*y,y-.2*x,.9)-.5)
    return max((1-smoothstep(.58,1.08,
                            math.hypot((x-px)/rx,(y-py)/ry)+edge))
               for px,py,rx,ry in PUDDLES)


def wetness(x,y,role):
    if role=="stone":
        gutter=smoothstep(1.4,2.8,abs(y))*smoothstep(.34,.74,
                    value_noise(x+11.0,y-7.0,4.1))
        return min(.96,.07+.76*puddle_mask(x,y)+.29*gutter)
    shoulder=math.exp(-((abs(y)-3.7)/1.7)**2)
    low=smoothstep(.34,.74,value_noise(x-23.0,y+9.0,5.6))
    return min(.85,.09+.50*low+.18*shoulder)


def macro_tint(x,y,role):
    # World-space 4–16 m color patches break the short scan repeat and remain
    # identical on both LODs and at every tile edge. No extra texture lookup.
    broad=value_noise(x+.17*y,y-.17*x,15.0)
    middle=value_noise(.7*x-.71*y,.71*x+.7*y,6.4)
    fine=value_noise(x-.23*y,y+.23*x,3.8)
    v=.40*broad+.37*middle+.23*fine-.5
    damp=wetness(x,y,role)
    if role=="soil":
        channels=(.93+.66*v,.91+.54*v,.86+.50*v)
        darken=1-.24*damp
    else:
        channels=(.96+.46*v,.94+.43*v,.91+.40*v)
        darken=1-.32*damp
        # Silt from the muddy shoulder collects in discontinuous pockets
        # between the edge stones. This remains a vertex tint on both LODs;
        # the licensed scan supplies the actual leaf and grout detail.
        shoulder=smoothstep(1.78,2.85,abs(y))
        deposit=smoothstep(.42,.70,value_noise(x+4.7,y-8.2,1.55))
        silt=.22*shoulder*deposit
        channels=(channels[0]*(1-.10*silt),
                  channels[1]*(1-.32*silt),
                  channels[2]*(1-.60*silt))
    return tuple(max(.54,min(1.0,channel*darken)) for channel in channels)+(damp,)


def path_half_width(x,side):
    # Independently worn shoulders keep the route centered under the torii,
    # while avoiding the same six-metre silhouette along all 64 metres.
    irregular=value_noise(x+side*37.0,side*13.0,3.2)-.5
    width=3.04+.16*math.sin(x*.37+side*.4)+.12*math.sin(x*1.21+side*1.3)+.17*irregular
    # Narrow, asymmetrical soil incursions replace occasional outer stones.
    # The playable center lane stays broad and its collision remains flat.
    broken_edges=((-26.0,-1,1.05),(-16.5,1,.85),(-7.2,-1,.75),
                  (3.5,1,1.15),(14.0,-1,.9),(24.4,1,.8))
    for bx,bs,span in broken_edges:
        if bs==side:
            width-=.34*(1-smoothstep(.35,span,abs(x-bx)))
    return max(2.43,min(3.32,width))


def scan_displacement(x,y):
    """Bilinearly sample the licensed pathway scan at its measured 1.8 m scale."""
    u=(x/MATERIALS["stone"][1])%1*width-.5
    v=(y/MATERIALS["stone"][1])%1*height-.5
    x0=math.floor(u);y0=math.floor(v)
    tx=u-x0;ty=v-y0
    a=displacement_values[y0%height,x0%width]
    b=displacement_values[y0%height,(x0+1)%width]
    c=displacement_values[(y0+1)%height,x0%width]
    d=displacement_values[(y0+1)%height,(x0+1)%width]
    return float((a*(1-tx)+b*tx)*(1-ty)+(c*(1-tx)+d*tx)*ty)


def elevation(x,y):
    """Global meters. Cosmetic displacement remains a few centimeters only."""
    road_mask=smoothstep(3.0,4.2,abs(y))
    nearest=min(math.hypot(x-sx,y-sy) for sx,sy in SITES)
    pad_mask=smoothstep(1.2,3.8,nearest)
    broad=(.0035*math.sin(x*.43)*math.sin(y*.53)
           +.0027*math.sin(x*1.31+y*.76)*math.sin(y*1.16-x*.21))
    fine=(.0009*math.sin(x*16.1+y*3.3)*math.sin(y*18.4-x*2.7)
          +.0016*(value_noise(x,y,.75)-.5))
    z=.018+(broad+fine)*road_mask*pad_mask
    # The photographed stone map supplies matched color, normal, and height.
    # Only its low-amplitude profile enters geometry; gameplay stays flat.
    edge=path_half_width(x,1 if y>=0 else -1)
    stone_interior=1-smoothstep(edge-.20,edge,abs(y))
    if stone_interior:
        settled=.0022*(value_noise(x+.2*y,y-.1*x,.65)-.5)
        z+=(.006*(scan_displacement(x,y)-.5)+settled
            -.0032*puddle_mask(x,y))*stone_interior
    shoulder=smoothstep(2.15,3.15,abs(y))*(1-smoothstep(3.7,4.5,abs(y)))
    silt=.0026*shoulder*smoothstep(.46,.74,value_noise(x-6.4,y+3.2,1.55))
    z+=silt
    # Banks flank two narrative sluice positions, without an actual trench,
    # hole, or gameplay slope. Peak lip is < 4 cm above collision-ground Z=0.
    for sx,sy in SITES[:2]:
        channel_y=sy-2.05
        x_window=1-smoothstep(2.0,3.2,abs(x-sx))
        for side in (-1,1):
            bank_y=channel_y+side*.78
            z+=.018*math.exp(-((y-bank_y)/.31)**2)*x_window
    return z


def create_tile(tier,ix,iy):
    nx,ny=GRID[tier]
    cx=-WORLD_X_M/2+(ix+.5)*TILE_X_M
    cy=-WORLD_Y_M/2+(iy+.5)*TILE_Y_M
    vertices=[]
    for gy in range(ny+1):
        y=-TILE_Y_M/2+gy*TILE_Y_M/ny
        for gx in range(nx+1):
            x=-TILE_X_M/2+gx*TILE_X_M/nx
            vertices.append((x,y,elevation(cx+x,cy+y)))
    faces=[]
    material_indices=[]
    for gy in range(ny):
        for gx in range(nx):
            a=gy*(nx+1)+gx
            faces.append((a,a+1,a+nx+2,a+nx+1))
            world_y=cy+(-TILE_Y_M/2+(gy+.5)*TILE_Y_M/ny)
            world_x=cx+(-TILE_X_M/2+(gx+.5)*TILE_X_M/nx)
            material_indices.append(1 if abs(world_y)<=path_half_width(
                world_x,1 if world_y>=0 else -1) else 0)
    name=f"SourceTerrain_{tier}_X{ix}_Y{iy}"
    data=bpy.data.meshes.new(name)
    data.from_pydata(vertices,[],faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    (high_collection if tier=="hi" else mac_collection).objects.link(obj)
    obj.location=(cx,cy,0)
    obj["world_tile_index"]=(ix,iy)
    obj["asset_tier"]=tier
    obj["world_center_m"]=(cx,cy,0)
    for mat in (soil,stone):
        data.materials.append(mat)
    uv=data.uv_layers.new(name="UV0_ProjectWorldScale")
    color=data.color_attributes.new(name="EstateMacroTint",type="FLOAT_COLOR",domain="CORNER")
    data.color_attributes.active_color=color
    for index,poly in enumerate(data.polygons):
        mi=material_indices[index]
        poly.material_index=mi
        poly.use_smooth=True
        tile_size=MATERIALS["stone" if mi else "soil"][1]
        for loop_index in poly.loop_indices:
            p=data.vertices[data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=((cx+p.x)/tile_size,(cy+p.y)/tile_size)
            color.data[loop_index].color=macro_tint(cx+p.x,cy+p.y,"stone" if mi else "soil")
    return obj,cx,cy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


tiles=[]
for tier in ("hi","mac"):
    for iy in range(TILES_Y):
        for ix in range(TILES_X):
            obj,cx,cy=create_tile(tier,ix,iy)
            export_name=f"SM_NyaagyuTerrain_{tier.upper()}_X{ix}_Y{iy}"
            fbx=OUT/(export_name+".fbx")
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active=obj
            bpy.ops.object.duplicate()
            temp=bpy.context.object
            temp.data=temp.data.copy()
            # Clearing the slots resets every polygon's material index to 0,
            # silently turning the authored stone route into soil in the FBX.
            # Replace each slot in place so the per-face split survives export.
            temp.data.materials[0]=export_soil
            temp.data.materials[1]=export_stone
            # UE's FBX conversion mirrors local Y while retaining local X/Z.
            # Pre-mirror only the export copy; the editable Blender source
            # remains in world coordinates. Reverse face winding so the
            # exported terrain keeps upward-facing normals after the mirror.
            # Preserve UV and vertex tint by polygon/vertex because flipping
            # a polygon changes the order of its per-corner loops.
            export_uv=temp.data.uv_layers.active
            export_tint=temp.data.color_attributes["EstateMacroTint"]
            corner_attributes={}
            for poly in temp.data.polygons:
                for loop_index in poly.loop_indices:
                    vertex_index=temp.data.loops[loop_index].vertex_index
                    corner_attributes[(poly.index,vertex_index)]=(
                        export_uv.data[loop_index].uv.copy(),
                        tuple(export_tint.data[loop_index].color))
            for vertex in temp.data.vertices:
                vertex.co.y=-vertex.co.y
            for poly in temp.data.polygons:
                poly.flip()
            for poly in temp.data.polygons:
                for loop_index in poly.loop_indices:
                    vertex_index=temp.data.loops[loop_index].vertex_index
                    uv_value,tint_value=corner_attributes[(poly.index,vertex_index)]
                    export_uv.data[loop_index].uv=uv_value
                    export_tint.data[loop_index].color=tint_value
            temp.data.update()
            assert min(poly.normal.z for poly in temp.data.polygons)>.97
            temp.location=(0,0,0)
            temp.name=export_name
            bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
                                     object_types={"MESH"},apply_unit_scale=True,
                                     global_scale=1.0,axis_forward="-Y",axis_up="Z",
                                     bake_anim=False,path_mode="STRIP",
                                     colors_type="LINEAR",prioritize_active_color=True)
            bpy.data.objects.remove(temp,do_unlink=True)
            world_bounds_cm=[round((cx-TILE_X_M/2)*100),round((cy-TILE_Y_M/2)*100),
                             round((cx+TILE_X_M/2)*100),round((cy+TILE_Y_M/2)*100)]
            z_values=[v.co.z for v in obj.data.vertices]
            tiles.append({"tier":tier,"index":[ix,iy],"name":export_name,
                          "fbx":fbx.name,"fbx_sha256":sha(fbx),
                          "placement_center_cm":[round(cx*100),round(cy*100),0],
                          "world_bounds_xy_cm":world_bounds_cm,
                          "sample_grid":[GRID[tier][0]+1,GRID[tier][1]+1],
                          "triangles":GRID[tier][0]*GRID[tier][1]*2,
                          "source_object":obj.name,
                          "z_range_cm":[round(min(z_values)*100,4),
                                        round(max(z_values)*100,4)]})
bpy.data.materials.remove(export_soil)
bpy.data.materials.remove(export_stone)
soil.name="M_Terrain_Soil_PolyHaven"
stone.name="M_Terrain_Stone_PolyHaven"

# All source tiles stay editable in the .blend; the FBXs carry local vertices.
# Only high-density geometry is displayed in this Blender contact sheet.
world=bpy.data.worlds.new("Estate_OvercastReview")
scene.world=world;world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.72,.78,.88,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.75
sun_data=bpy.data.lights.new("Review_soft_sun","SUN")
sun_data.energy=1.8;sun_data.angle=.18
sun=bpy.data.objects.new("Review_soft_sun",sun_data)
scene.collection.objects.link(sun)
sun.rotation_euler=(.45,-.42,-.4)
cam_data=bpy.data.cameras.new("Review_camera")
cam=bpy.data.objects.new("Review_camera",cam_data)
scene.collection.objects.link(cam)
scene.camera=cam
cam_data.type="ORTHO";cam_data.ortho_scale=75
cam.location=(29,-46,66)
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat("-Z","Y").to_euler()
scene.render.engine="CYCLES"
scene.cycles.samples=16
scene.cycles.use_denoising=True
scene.render.resolution_x=1500
scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
scene.render.filepath=str(PREVIEW)
bpy.ops.render.render(write_still=True)
# A second, eye-height review exposes the scan scale, stone joints, and
# transition into the soil. The overview alone cannot reveal those details.
cam_data.type="PERSP";cam_data.lens=40
cam.location=(3.2,-3.8,1.45)
cam.rotation_euler=(Vector((-2.0,-.2,.06))-cam.location).to_track_quat("-Z","Y").to_euler()
sun_data.angle=.085
scene.cycles.samples=32
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.filepath=str(DETAIL_PREVIEW)
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source=="FILE":
        image.filepath=bpy.path.relpath(image.filepath,start=str(OUT))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest={
    "schema_version":1,
    "generator":"scripts/art/create_nyaagyu_mesh_terrain.py",
    "validator":"scripts/art/validate_nyaagyu_mesh_terrain.py",
    "source_blend":BLEND.name,"source_blend_sha256":sha(BLEND),
    "preview":PREVIEW.name,"preview_sha256":sha(PREVIEW),
    "detail_preview":DETAIL_PREVIEW.name,"detail_preview_sha256":sha(DETAIL_PREVIEW),
    "units":"meters in Blender; centimeters in UE placement records",
    "world_xy_cm":[-3200,-2600,3200,2600],
    "tile_layout":[TILES_X,TILES_Y],
    "tile_size_cm":[1600,1300],
    "density":{"hi":{"quads_per_tile":[128,104],"quad_spacing_cm":12.5,
                      "intended":"Windows Nanite candidate"},
               "mac":{"quads_per_tile":[32,26],"quad_spacing_cm":50,
                      "intended":"M1 Ultra conventional mesh fallback candidate"}},
    "height_function":"scripts/art/create_nyaagyu_mesh_terrain.py:elevation",
    "macro_tint":{"vertex_color_attribute":"EstateMacroTint",
                  "function":"scripts/art/create_nyaagyu_mesh_terrain.py:macro_tint",
                  "alpha_semantics":"0..1 world-space dampness; Blender source reduces scanned roughness at high alpha",
                  "intended":"Terrain-only vertex-color albedo and wetness modulation; no extra texture fetch"},
    "max_visual_collision_delta_cm":4.5,
    "material_slots":[soil.name,stone.name],
    "palette_manifest":"../PolyHaven/manifest.json",
    "palette_license":"CC0-1.0; https://polyhaven.com/license",
    "palette_files":source_files,
    "stone_pathway_scan":STONE_PATHWAY_SCAN,
    "tiles":tiles,
    "license":"Original project-owned terrain geometry and Blender review render; reused Poly Haven texture maps are CC0-1.0 under their separate asset records. No purchased assets.",
    "limitations":"Source-art meshes only. No UE 5.8.2 import, World Partition level, Mesh Partition conversion, compiled sections, Nanite setup, Lumen validation, collision integration, lighting comparison, or performance qualification is claimed.",
}
MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n")
print("NYAAGYU_MESH_TERRAIN_SOURCE_CREATED",len(tiles),
      sum(t["triangles"] for t in tiles if t["tier"]=="hi"),
      sum(t["triangles"] for t in tiles if t["tier"]=="mac"))
