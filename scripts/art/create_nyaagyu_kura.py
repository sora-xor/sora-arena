"""Create the original Nyaagyu production storehouse (kura) source asset.

Run with Blender 5.2.2 LTS:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_kura.py

The editable .blend preserves individual timber, plaster, door, and kawara
parts; FBX exports one visual mesh and three UCX review proxies. Blender's
review render is source-art evidence, not an Unreal gameplay screenshot.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKura"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SVG_RECORD = json.loads((SVG.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(SVG.read_bytes()).hexdigest() == SVG_RECORD["source_sha256"]
NAME = "SM_Nyaagyu_ProvisionKura"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
SCENE = bpy.context.scene
SCENE.unit_settings.system = "METRIC"
SCENE.unit_settings.scale_length = 1.0
EDITABLE = bpy.data.collections.new("Nyaagyu_ProvisionKura_Editable")
SCENE.collection.children.link(EDITABLE)


def basic(name, color, metal=0.0, rough=.64, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    if emission:
        shader.inputs["Emission Color"].default_value = (*color, 1)
        shader.inputs["Emission Strength"].default_value = emission
    return mat


def pinned_pbr(name, folder, tile):
    """Link only already-pinned CC0 maps; Unreal binds measured PBR roles."""
    mat = basic(name, (.32,.31,.28), rough=.75)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (tile,)*3
    links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    textures = {}
    for role,marker in (("diffuse","_diff_"),("normal","_nor_dx_"),("arm","_arm_")):
        path = next(folder.glob("*"+marker+"*"))
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if role == "diffuse" else "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.name = role
        node.image = image
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        textures[role] = node
    links.new(textures["diffuse"].outputs["Color"], shader.inputs["Base Color"])
    split_arm = nodes.new("ShaderNodeSeparateColor")
    links.new(textures["arm"].outputs["Color"], split_arm.inputs["Color"])
    links.new(split_arm.outputs["Green"], shader.inputs["Roughness"])
    links.new(split_arm.outputs["Blue"], shader.inputs["Metallic"])
    split_normal = nodes.new("ShaderNodeSeparateColor")
    links.new(textures["normal"].outputs["Color"], split_normal.inputs["Color"])
    inverted_green = nodes.new("ShaderNodeMath")
    inverted_green.operation = "SUBTRACT"
    inverted_green.inputs[0].default_value = 1
    links.new(split_normal.outputs["Green"], inverted_green.inputs[1])
    recombine = nodes.new("ShaderNodeCombineColor")
    links.new(split_normal.outputs["Red"], recombine.inputs["Red"])
    links.new(inverted_green.outputs[0], recombine.inputs["Green"])
    links.new(split_normal.outputs["Blue"], recombine.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .65
    links.new(recombine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


TIMBER = pinned_pbr("M_Env_Timber",PALETTE/"wood_planks_dirt",2.4)
STONE = pinned_pbr("M_Env_Stone",PALETTE/"stone_floor",1.45)
KAWARA = pinned_pbr("M_Kura_Kawara",PALETTE/"GreyRoofTiles",1.55)
PLASTER = pinned_pbr("M_Kura_LimePlaster",PALETTE/"WhitePlaster02",1.15)
for plaster_node in PLASTER.node_tree.nodes:
    if plaster_node.type == "NORMAL_MAP":
        plaster_node.inputs["Strength"].default_value = .18
    elif plaster_node.type == "TEX_IMAGE":
        # Generated XY sampling collapses onto one scanline on Y-facing thin
        # walls. Box projection gives the editable review source a true planar
        # surface sample, matching the Unreal world-aligned material path.
        plaster_node.projection = "BOX"
        plaster_node.projection_blend = .18
CHAR = basic("M_Kura_CharredCedar",(.055,.052,.049),rough=.74)
IRON = basic("M_Kura_BlackIron",(.032,.037,.039),metal=.75,rough=.53)
WASHI = basic("M_Kura_WashiVent",(.62,.58,.48),rough=.84)
BRASS = basic("M_Kura_AgedBrass",(.46,.32,.15),metal=.77,rough=.42)
SHADOW = basic("M_Kura_Recess",(.033,.031,.027),rough=.95)


def keep(obj,name,mat=None):
    obj.name=name
    for coll in tuple(obj.users_collection):coll.objects.unlink(obj)
    EDITABLE.objects.link(obj)
    if mat:obj.data.materials.append(mat)
    obj["author"]="Original SORA Arena provision-storehouse geometry"
    return obj


def box(name,location,dimensions,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location)
    obj=keep(bpy.context.object,name,mat)
    obj.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new("worn_arris","BEVEL")
        mod.width=bevel
        mod.segments=2
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:face.use_smooth=True
    return obj


def beam(name,start,end,width,depth,mat):
    delta=Vector(end)-Vector(start)
    obj=box(name,(Vector(start)+Vector(end))*.5,(width,depth,delta.length),mat,.007)
    obj.rotation_euler=delta.to_track_quat("Z","Y").to_euler()
    return obj


def cylinder(name,location,radius,depth,mat,vertices=24,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,
                                        location=location,rotation=rotation)
    return keep(bpy.context.object,name,mat)


def source_mesh(name,verts,faces,mat):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    EDITABLE.objects.link(obj)
    data.materials.append(mat)
    obj["author"]="Original SORA Arena provision-storehouse geometry"
    return obj


def label(name,text,location,size,mat):
    bpy.ops.object.text_add(location=location,rotation=(math.pi/2,0,0))
    obj=bpy.context.object
    obj.data.body=text
    obj.data.font=bpy.data.fonts.load(str(FONT),check_existing=True)
    obj.data.align_x="CENTER"
    obj.data.align_y="CENTER"
    obj.data.size=size
    obj.data.extrude=.0018
    obj.data.bevel_depth=.0008
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    return keep(bpy.context.object,name)


def crest(name,x,y,z,size):
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SVG))
    curves=[obj for obj in set(bpy.data.objects)-before if obj.type=="CURVE"]
    assert len(curves)==2
    pts=[obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
    min_x,max_x=min(p.x for p in pts),max(p.x for p in pts)
    min_y,max_y=min(p.y for p in pts),max(p.y for p in pts)
    cx,cy=(min_x+max_x)/2,(min_y+max_y)/2
    scale=size/max(max_x-min_x,max_y-min_y)
    for i,obj in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        obj=bpy.context.object
        for vert in obj.data.vertices:
            p=obj.matrix_world @ vert.co
            vert.co=(x+(p.x-cx)*scale,y,z+(p.y-cy)*scale)
        obj.matrix_world.identity()
        obj=keep(obj,f"UserSupplied_SORAKamon_{name}_Path_{i}")
        obj.data.materials.clear()
        obj.data.materials.append(BRASS)
        obj["source_svg_sha256"]=SVG_RECORD["source_sha256"]


# Stone-footed, fire-resisting plaster mass. This is a fictional production
# storehouse inspired by white-walled Edo kura, not a measured reconstruction.
box("Stone_RaisedPlinth",(0,0,.29),(6.23,6.25,.58),STONE,.04)
for course in range(2):
    for side in (-1,1):
        for i in range(14):
            x=-2.94+i*.45+(.225 if course else 0)
            if x>3.05:continue
            box(f"Plinth_FrontBack_{side}_{course}_{i}",(x,side*3.14,.13+course*.25),
                (.43,.14,.22),STONE,.010)
        for i in range(14):
            y=-2.94+i*.45+(.225 if course else 0)
            if y>3.05:continue
            box(f"Plinth_Side_{side}_{course}_{i}",(side*3.14,y,.13+course*.25),
                (.14,.43,.22),STONE,.010)

box("White_StorehouseCore",(0,0,2.21),(5.93,5.97,3.29),PLASTER,.045)
for side in (-1,1):
    x=side*2.994
    box(f"CornerQuoin_X_{side}",(x,0,2.21),(.115,6.09,3.36),PLASTER,.017)
    for y in (-2.77,2.77):
        box(f"Timber_CornerGuard_{side}_{y}",(side*2.99,y,2.16),(.11,.115,3.17),CHAR,.009)
    for z in (.72,1.81,3.61):
        box(f"WeatherRail_X_{side}_{z}",(x,0,z),(.13,6.0,.09),CHAR,.009)
    # Black-and-white lower namako-wall rhythm: diagonally grouted diamonds
    # are applied over the solid lime wall, never over a transparent shoji.
    for j in range(9):
        y=-2.84+j*.71
        beam(f"Namako_Rising_X_{side}_{j}",(x+.067*side,y-.31,.76),
             (x+.067*side,y+.31,1.47),.032,.034,CHAR)
        beam(f"Namako_Falling_X_{side}_{j}",(x+.067*side,y+.31,.76),
             (x+.067*side,y-.31,1.47),.032,.034,CHAR)
for side in (-1,1):
    y=side*2.994
    for z in (.72,1.81,3.61):
        box(f"WeatherRail_Y_{side}_{z}",(0,y,z),(6.0,.13,.09),CHAR,.009)
    for x in (-2.85,2.85):
        box(f"FrontBack_CornerGuard_{side}_{x}",(x,y,2.16),(.115,.12,3.17),CHAR,.009)

# A timber loading door is more appropriate for a kura than broad shoji. The
# small washi-backed upper vent and thick plaster shutters stay protected.
box("LoadingPortal_Recess",(0,-3.025,2.12),(2.83,.028,2.82),SHADOW,.010)
box("LoadingPortal_Header",(0,-3.083,3.55),(3.05,.12,.16),CHAR,.013)
for side in (-1,1):
    x=side*1.51
    box(f"Portal_Post_{side}",(x,-3.08,2.12),(.17,.17,2.88),TIMBER,.011)
    center=side*.706
    box(f"LoadingDoor_{side}",(center,-3.085,2.12),(1.39,.078,2.68),TIMBER,.018)
    for i in range(7):
        px=center-.59+i*.195
        box(f"Door_PlankSeam_{side}_{i}",(px,-3.134,2.12),(.012,.011,2.59),CHAR,.002)
    for z in (1.13,2.05,2.96):
        box(f"Door_CrossRail_{side}_{z}",(center,-3.15,z),(1.31,.057,.095),CHAR,.008)
        for q in (-1,1):
            cylinder(f"Door_Rivet_{side}_{z}_{q}",(center+q*.53,-3.190,z),
                     .023,.019,IRON,12,(math.pi/2,0,0))
    cylinder(f"Door_RingPlate_{side}",(side*.20,-3.187,2.03),.11,.025,IRON,24,(math.pi/2,0,0))
    cylinder(f"Door_PullRing_{side}",(side*.20,-3.22,2.03),.066,.019,BRASS,32,(math.pi/2,0,0))
box("Door_Sill",(0,-3.23,.71),(3.22,.38,.15),STONE,.014)
for i in range(3):
    box(f"Loading_Step_{i}",(0,-3.48-i*.15,.55-i*.11),(2.60+i*.20,.25,.11),STONE,.013)

def shutter(name,side_x,side_y):
    # Closed upper shutters have substantial plaster reveals and iron hinges.
    x=side_x*3.055
    y=side_y*1.35
    box(f"Window_Reveal_{name}",(x,y,2.88),(.045,.97,.84),SHADOW,.008)
    for yoff in (-.53,.53):
        box(f"Window_Jamb_{name}_{yoff}",(x+side_x*.04,y+yoff,2.88),
            (.12,.11,.99),PLASTER,.009)
    for z in (2.36,3.4):
        box(f"Window_Lintel_{name}_{z}",(x+side_x*.04,y,z),(.12,1.19,.12),PLASTER,.009)
    box(f"Plank_Shutter_{name}",(x+side_x*.084,y,2.88),(.082,.84,.75),TIMBER,.010)
    for i in range(4):
        py=y-.31+i*.20
        box(f"Shutter_Batten_{name}_{i}",(x+side_x*.14,py,2.88),(.018,.025,.72),CHAR,.002)
    for z in (2.59,3.17):
        box(f"Shutter_Hinge_{name}_{z}",(x+side_x*.142,y-.31,z),(.028,.16,.034),IRON,.004)
for sx in (-1,1):
    for sy in (-1,1):
        shutter(f"{sx}_{sy}",sx,sy)

box("Gable_Vent_Recess",(0,-3.03,4.12),(1.13,.033,.51),SHADOW,.006)
box("Gable_Vent_Washi",(0,-3.052,4.12),(1.04,.014,.42),WASHI)
for x in (-.55,0,.55):
    box(f"Gable_Vent_LatticeV_{x}",(x,-3.07,4.12),(.025,.025,.47),CHAR,.002)
for z in (3.99,4.25):
    box(f"Gable_Vent_LatticeH_{z}",(0,-3.07,z),(1.08,.025,.025),CHAR,.002)

# Distinct front-facing gable: the dojo ridge runs across the road, but this
# storehouse ridge runs inward. Original curved geometry carries scanned,
# measured CC0 grey-ceramic color/normal/ARM rather than a flat roof swatch.
eave_z,ridge_z,half_x=3.69,5.12,3.64
for side in (-1,1):
    sx=side*2.94
    verts=[(sx,-2.97,3.63),(sx,2.97,3.63),(0,2.97,4.85),(0,-2.97,4.85)]
    source_mesh(f"GableLime_Infill_{side}",verts,[(0,1,2,3)],PLASTER)
for side in (-1,1):
    y=side*3.0
    verts=[(-2.93,y,3.64),(2.93,y,3.64),(0,y,4.86)]
    source_mesh(f"GableEnd_Lime_{side}",verts,[(0,1,2)],PLASTER)
    for xs in (-1,1):
        beam(f"Gable_Rake_{side}_{xs}",(0,y,4.93),(xs*3.45,y,3.64),.075,.11,CHAR)

# Curved tile courses are combined into two meshes to keep the FBX compact.
for side in (-1,1):
    verts,faces=[],[]
    columns,rows=30,10
    cell_y=7.20/columns
    cell_x=half_x/rows
    for row in range(rows):
        for col in range(columns):
            y0=-3.60+col*cell_y
            x0=row*cell_x
            start=len(verts)
            for ix in range(3):
                x=min(half_x,x0+ix*(cell_x+.015)/2)
                xx=side*x
                z=ridge_z-(ridge_z-eave_z)*x/half_x
                for iy in range(5):
                    fy=iy/4
                    y=y0+fy*cell_y
                    # Shallow pan/channel and thicker lower overlap course.
                    curve=.024*math.sin(math.pi*fy)
                    lip=.012 if ix==2 else 0
                    verts.append((xx,y,z+.027+curve+lip))
            for ix in range(2):
                for iy in range(4):
                    a=start+ix*5+iy
                    faces.append((a,a+1,a+6,a+5) if side<0 else (a+5,a+6,a+1,a))
    source_mesh(f"Kawara_CurvedCourses_{side}",verts,faces,KAWARA)
    for row in range(rows):
        x=side*min(half_x,(row+1)*cell_x)
        z=ridge_z-(ridge_z-eave_z)*abs(x)/half_x+.063
        box(f"Kawara_HorizontalLap_{side}_{row}",(x,0,z),(.027,7.22,.020),KAWARA,.004)
    beam(f"Raked_Eave_{side}",(0,-3.66,ridge_z-.08),
         (side*half_x,-3.66,eave_z-.08),.11,.10,CHAR)
    for y in (-3.63,3.63):
        beam(f"Gable_Verge_{side}_{y}",(0,y,ridge_z+.06),
             (side*half_x,y,eave_z+.04),.13,.065,KAWARA)
    box(f"Eave_Fascia_{side}",(side*3.64,0,eave_z-.11),(.13,7.30,.15),CHAR,.017)
for i in range(30):
    y=-3.48+i*.24
    cylinder(f"Ridge_RoundCap_{i}",(0,y,ridge_z+.07),.095,.25,KAWARA,16,(math.pi/2,0,0))
for i in range(11):
    y=-3.5+i*.7
    for sx in (-1,1):
        beam(f"Rafter_{sx}_{i}",(0,y,ridge_z-.22),
             (sx*3.55,y,eave_z-.24),.10,.12,TIMBER)

# A discrete resistance supply-house sign carries the exact supplied SVG mon.
# The exterior structure itself does not pretend this mon was an Edo family crest.
box("ProductionSign_Backplate",(0,-3.19,3.62),(2.15,.11,.31),CHAR,.012)
label("ProductionSign_Japanese","生産蔵",(0,-3.252,3.59),.20,BRASS)
for sx in (-1,1):
    x=sx*1.23
    cylinder(f"ProductionSign_KamonDisc_{sx}",(x,-3.20,3.62),.117,.018,IRON,32,(math.pi/2,0,0))
    crest("supply_left" if sx<0 else "supply_right",x,-3.214,3.62,.18)

# Join duplicate source parts for a one-render-mesh FBX. UCX boxes are art
# proxies only: WorldBuilder retains the prior campaign collision volumes.
parts=[ob for ob in EDITABLE.objects if ob.type=="MESH"]
triangles=sum(len(poly.vertices)-2 for ob in parts for poly in ob.data.polygons)
corners=[ob.matrix_world @ Vector(corner) for ob in parts for corner in ob.bound_box]
bounds={"min":[round(min(p[a] for p in corners),3) for a in range(3)],
        "max":[round(max(p[a] for p in corners),3) for a in range(3)]}
linked=[(node,node.image) for mat in (TIMBER,STONE,KAWARA,PLASTER)
        for node in mat.node_tree.nodes if node.type=="TEX_IMAGE"]
for node,_ in linked:node.image=None
bpy.ops.object.select_all(action="DESELECT")
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.object.duplicate()
copies=list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join()
render=bpy.context.object
render.name=NAME
render["author"]="Original SORA Arena provision-storehouse geometry"
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
proxies=[]
for i,(loc,dims) in enumerate([
    ((0,0,2.09),(5.92,5.98,4.18)),
    ((0,-3.12,.46),(6.08,.72,.92)),
    ((0,0,4.41),(7.12,7.25,1.47)),
]):
    proxies.append(box(f"UCX_{NAME}_{i:02d}",loc,dims,IRON))
bpy.ops.object.select_all(action="DESELECT")
render.select_set(True)
for ob in proxies:ob.select_set(True)
bpy.context.view_layer.objects.active=render
fbx=OUT/(NAME+".fbx")
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
    object_types={"MESH"},apply_unit_scale=True,global_scale=1.0,
    axis_forward="-Y",axis_up="Z",add_leaf_bones=False,bake_anim=False,path_mode="STRIP")
for ob in proxies:bpy.data.objects.remove(ob,do_unlink=True)
bpy.data.objects.remove(render,do_unlink=True)
for node,image in linked:node.image=image

# Source-art review under neutral late-afternoon lighting. Nothing here is
# exported to the game; no rendered pixels are represented as UE evidence.
STAGE=bpy.data.collections.new("ArtReview_NotForFBX")
SCENE.collection.children.link(STAGE)
ground=box("Review_StonePlatform",(0,0,-.15),(8.1,8.1,.28),STONE,.03)
for coll in tuple(ground.users_collection):coll.objects.unlink(ground)
STAGE.objects.link(ground)
def area(name,pos,color,energy,size,target=(0,0,2.2)):
    bpy.ops.object.light_add(type="AREA",location=pos)
    obj=bpy.context.object
    obj.name=name
    obj.data.energy=energy
    obj.data.color=color
    obj.data.shape="DISK"
    obj.data.size=size
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
area("Warm_West_Key",(-5,-6,8),(1,.73,.49),1650,7)
area("Cool_East_Fill",(4,4,8),(.58,.76,1),1000,8)
area("Door_Bounce",(0,-5,3),(1,.82,.61),160,3)
bpy.ops.object.camera_add(location=(9,-11,7.5))
camera=bpy.context.object
camera.name="ProvisionKura_ArtReviewCamera"
camera.rotation_euler=(Vector((0,0,2.4))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO"
camera.data.ortho_scale=12.2
SCENE.camera=camera
SCENE.world.color=(.10,.12,.15)
SCENE.render.engine="CYCLES"
SCENE.cycles.samples=48
SCENE.cycles.use_denoising=True
SCENE.render.resolution_x=1500
SCENE.render.resolution_y=1150
SCENE.render.resolution_percentage=100
SCENE.view_settings.view_transform="AgX"
SCENE.view_settings.exposure=-.8
preview=OUT/"Nyaagyu_ProvisionKura_Blender.png"
SCENE.render.filepath=str(preview)
SCENE.render.image_settings.file_format="PNG"
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source=="FILE":image.filepath=bpy.path.relpath(image.filepath,start=str(OUT))
for font in bpy.data.fonts:
    if font.filepath and Path(bpy.path.abspath(font.filepath)).resolve()==FONT.resolve():
        font.filepath=bpy.path.relpath(str(FONT),start=str(OUT))
blend=OUT/"Nyaagyu_ProvisionKura.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
palette_manifest=PALETTE/"manifest.json"
roof_manifest=PALETTE/"GreyRoofTiles/manifest.json"
plaster_manifest=PALETTE/"WhitePlaster02/manifest.json"
manifest={
    "schema_version":1,"name":NAME,
    "generator":"scripts/art/create_nyaagyu_kura.py",
    "generator_blender":bpy.app.version_string,
    "source_blend":blend.name,"fbx":fbx.name,"preview":preview.name,
    "blend_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
    "fbx_sha256":hashlib.sha256(fbx.read_bytes()).hexdigest(),
    "preview_sha256":hashlib.sha256(preview.read_bytes()).hexdigest(),
    "palette_manifest_sha256":hashlib.sha256(palette_manifest.read_bytes()).hexdigest(),
    "roof_manifest_sha256":hashlib.sha256(roof_manifest.read_bytes()).hexdigest(),
    "plaster_manifest_sha256":hashlib.sha256(plaster_manifest.read_bytes()).hexdigest(),
    "font_sha256":hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "sora_kamon_svg_sha256":SVG_RECORD["source_sha256"],
    "palette_asset_ids":["wood_planks_dirt","stone_floor","grey_roof_tiles","white_plaster_02"],
    "unreal_asset":f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "source_parts":len(parts),"source_triangles":triangles,
    "roof_tile_count":600,"shutter_count":4,"collision_boxes":3,
    "bounds_m":bounds,
    "placement_origin":"Ground center; local -Y front/loading doors face estate road",
    "placement_cm":"Use for four of the ten MapId 0 row buildings at existing P with yaw 0 on north row and 180 on south row, preserving all Building() collision pieces.",
    "collision_guidance":"UCX proxies in FBX are art-review only. In campaign, hidden original WorldBuilder building components retain collision. Practice map uses none of this mesh.",
    "license":"Original project-owned geometry and review render. Exact user-supplied SORA SVG retains user-provided provenance. Linked timber, stone, grey roof tile, and white plaster PBR maps are CC0 Poly Haven; Noto Japanese font is SIL OFL. No purchased assets.",
    "history_reference":[{"url":"https://japan-heritage.bunka.go.jp/ja/special/145/","note":"Agency for Cultural Affairs heritage overview of white kura walls, protected storage, and Edo-period shop-house design. This production storehouse is fictional, not a reconstruction."}],
    "scope":"Original editable source, FBX, and Blender review render. Unreal import, in-game photorealism, historical reconstruction, and performance require separate qualification."
}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("NYAAGYU_KURA_READY",len(parts),triangles,bounds,preview,flush=True)
