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
from mathutils import Vector


ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"Content/SourceArt/Environment/NyaagyuTerrain"
OUT.mkdir(parents=True,exist_ok=True)
PALETTE=ROOT/"Content/SourceArt/Environment/PolyHaven"
PALETTE_MANIFEST=json.loads((PALETTE/"manifest.json").read_text())
assert PALETTE_MANIFEST["asset_license"]=="CC0-1.0"
BLEND=OUT/"Nyaagyu_Estate_MeshTerrain_Source.blend"
PREVIEW=OUT/"Nyaagyu_Estate_MeshTerrain_Blender.png"
MANIFEST=OUT/"manifest.json"
WORLD_X_M=64.0
WORLD_Y_M=52.0
TILES_X=TILES_Y=4
TILE_X_M=WORLD_X_M/TILES_X
TILE_Y_M=WORLD_Y_M/TILES_Y
GRID={"hi":(128,104),"mac":(16,13)}  # 12.5 cm / 1 m quad edges
MATERIALS={"soil":("brown_mud_leaves_01",1.30),
           "stone":("stone_floor",1.85)}
SITES=[(-12.5,-7.0),(0.0,10.0),(12.5,-8.0)]

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


source_files=[]
def terrain_material(role,asset_id):
    mat=bpy.data.materials.new("M_Terrain_"+role.capitalize()+"_PolyHaven")
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value=.83 if role=="soil" else .71
    links=mat.node_tree.links
    images={}
    for channel,marker in (("diffuse","_diff_"),("normal","_nor_dx_"),("arm","_arm_")):
        path,item=tex_record(asset_id,marker)
        image=bpy.data.images.load(str(path),check_existing=True)
        image.colorspace_settings.name="sRGB" if channel=="diffuse" else "Non-Color"
        node=mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.name=channel
        node.image=image
        node.interpolation="Linear"
        images[channel]=node
        source_files.append({"role":role,"channel":channel,
                             "path":str(path.relative_to(ROOT)),
                             "sha256":item["sha256"],"bytes":item["bytes"]})
    links.new(images["diffuse"].outputs["Color"],bsdf.inputs["Base Color"])
    arm=mat.node_tree.nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"],arm.inputs["Color"])
    links.new(arm.outputs["Green"],bsdf.inputs["Roughness"])
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
stone=terrain_material("stone","stone_floor")
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


def elevation(x,y):
    """Global meters. Cosmetic displacement remains a few centimeters only."""
    road_mask=smoothstep(3.0,4.2,abs(y))
    nearest=min(math.hypot(x-sx,y-sy) for sx,sy in SITES)
    pad_mask=smoothstep(1.2,3.8,nearest)
    broad=(.0035*math.sin(x*.43)*math.sin(y*.53)
           +.0027*math.sin(x*1.31+y*.76)*math.sin(y*1.16-x*.21))
    fine=.0009*math.sin(x*16.1+y*3.3)*math.sin(y*18.4-x*2.7)
    z=.018+(broad+fine)*road_mask*pad_mask
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
            material_indices.append(1 if abs(world_y)<=3.3 else 0)
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
    for index,poly in enumerate(data.polygons):
        mi=material_indices[index]
        poly.material_index=mi
        poly.use_smooth=True
        tile_size=MATERIALS["stone" if mi else "soil"][1]
        for loop_index in poly.loop_indices:
            p=data.vertices[data.loops[loop_index].vertex_index].co
            uv.data[loop_index].uv=((cx+p.x)/tile_size,(cy+p.y)/tile_size)
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
            temp.data.materials.clear()
            temp.data.materials.append(export_soil)
            temp.data.materials.append(export_stone)
            temp.location=(0,0,0)
            temp.name=export_name
            bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
                                     object_types={"MESH"},apply_unit_scale=True,
                                     global_scale=1.0,axis_forward="-Y",axis_up="Z",
                                     bake_anim=False,path_mode="STRIP")
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
    "units":"meters in Blender; centimeters in UE placement records",
    "world_xy_cm":[-3200,-2600,3200,2600],
    "tile_layout":[TILES_X,TILES_Y],
    "tile_size_cm":[1600,1300],
    "density":{"hi":{"quads_per_tile":[128,104],"quad_spacing_cm":12.5,
                      "intended":"Windows Nanite candidate"},
               "mac":{"quads_per_tile":[16,13],"quad_spacing_cm":100,
                      "intended":"M1 Ultra conventional mesh fallback candidate"}},
    "height_function":"scripts/art/create_nyaagyu_mesh_terrain.py:elevation",
    "max_visual_collision_delta_cm":4.5,
    "material_slots":[soil.name,stone.name],
    "palette_manifest":"../PolyHaven/manifest.json",
    "palette_license":"CC0-1.0; https://polyhaven.com/license",
    "palette_files":source_files,
    "tiles":tiles,
    "license":"Original project-owned terrain geometry and Blender review render; reused Poly Haven texture maps are CC0-1.0 under their separate asset records. No purchased assets.",
    "limitations":"Source-art meshes only. No UE 5.8.2 import, World Partition level, Mesh Partition conversion, compiled sections, Nanite setup, Lumen validation, collision integration, lighting comparison, or performance qualification is claimed.",
}
MANIFEST.write_text(json.dumps(manifest,indent=2)+"\n")
print("NYAAGYU_MESH_TERRAIN_SOURCE_CREATED",len(tiles),
      sum(t["triangles"] for t in tiles if t["tier"]=="hi"),
      sum(t["triangles"] for t in tiles if t["tier"]=="mac"))
