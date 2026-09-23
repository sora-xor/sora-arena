"""Isolated anatomical Nyaakoto head study; Blender 5.2 LTS.

Run from repository root with:
  blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadSculpt/create_head_study.py

This deliberately does not touch the game character or its import pipeline.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.noise import noise_vector


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
PBR = REPO / "Content/SourceArt/Characters/Hero/PBR"
EYE = REPO / "Content/SourceArt/Characters/Hero/EyeStudy/T_Nyaakoto_Iris_Albedo.png"
random.seed(240924)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = "METRIC"
bpy.context.scene.unit_settings.scale_length = 1.0


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material(name, rgb, rough=.8, metallic=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Transmission Weight"].default_value = transmission
    if transmission:
        bsdf.inputs["IOR"].default_value = 1.38
    return m


GREY = material("M_Coat_Grey_Review", (.25, .245, .23), .85)
WHITE = material("M_Coat_Ivory_Review", (.77, .73, .65), .87)
EAR_OUT = material("M_Ear_Cartilage_Outer", (.29, .265, .25), .85)
EAR_IN = material("M_Ear_Cartilage_Inner", (.33, .185, .17), .77)
EAR_RIM = material("M_Ear_LightRim", (.59, .54, .47), .87)
NOSE = material("M_Nose_Leather", (.37, .19, .18), .57)
NOSE_DARK = material("M_Naris_And_Lip", (.055, .039, .038), .63)
SOCKET = material("M_Eye_Cavity", (.05, .038, .037), .65)
SCLERA = material("M_Cool_Ivory_Sclera", (.59, .65, .66), .25)
PUPIL = material("M_Pupil", (.008, .014, .018), .11)
CORNEA = material("M_Cornea_Bulge", (.68, .79, .84), .035, transmission=.89)
WET = material("M_Eyelid_Wetline", (.11, .066, .06), .24)
WHISKER = material("M_Whisker_Keratin", (.77, .76, .69), .62)


def uv_sphere(name, loc, scale, mat, seg=48, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    for face in ob.data.polygons:
        face.use_smooth = True
    return ob


def selected(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


# The underlying adult-cat cranium is wider caudally; the facial wedge and
# paired masseter/whisker pads are volumes in one remeshed coat shell.
shell_parts = [
    uv_sphere("work_braincase", (.016, 0, 1.676), (.155, .147, .131), GREY),
    uv_sphere("work_facial_wedge", (.112, 0, 1.641), (.095, .106, .085), GREY),
    uv_sphere("work_nasal_bridge", (.172, 0, 1.652), (.060, .035, .053), GREY),
    uv_sphere("work_mandible", (.121, 0, 1.557), (.092, .087, .037), GREY),
    uv_sphere("work_throat", (-.015, 0, 1.502), (.092, .100, .128), GREY),
]
for side in (-1, 1):
    shell_parts.extend([
        uv_sphere(f"work_zygomatic_{side}", (.113, side*.098, 1.619), (.080, .053, .052), GREY),
        uv_sphere(f"work_whisker_pad_{side}", (.183, side*.044, 1.573), (.055, .046, .027), GREY),
        uv_sphere(f"work_brow_{side}", (.149, side*.066, 1.692), (.063, .053, .026), GREY),
    ])
selected(shell_parts)
bpy.ops.object.join()
head = bpy.context.object
head.name = "SM_Nyaakoto_AnatomicalHead_Study"
# Joining keeps the first sphere's transform. All subsequent anatomical
# coordinates, coat masks, and fur-root rays use world-aligned local meters.
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
head.data.remesh_voxel_size = .0029
bpy.ops.object.voxel_remesh()
smooth = head.modifiers.new("AnatomicalSmoothing", "SMOOTH")
smooth.factor = 1.35
smooth.iterations = 9
bpy.ops.object.modifier_apply(modifier=smooth.name)

# Carve orbital recesses and tame the human/toy spherical cranium silhouette.
for v in head.data.vertices:
    x, y, z = v.co
    ay = abs(y)
    if z > 1.64:
        v.co.y *= 1 - .17*min(1.0, (z-1.64)/.15)
    if 1.57 < z < 1.70 and x > .075:
        cheek = math.exp(-((z-1.619)/.052)**2-((ay-.102)/.055)**2)
        v.co.y += math.copysign(.007*cheek, y)
    if x > .128:
        orbit = math.exp(-((y-math.copysign(.069,y))/.038)**2-((z-1.673)/.024)**2)
        v.co.x -= .018*orbit
    if z < 1.57 and x < .12:
        v.co.y *= .95
for face in head.data.polygons:
    face.use_smooth = True

# The fused face contains overhangs and a throat; cylindrical projection folds
# those surfaces over one another. Unwrap disjoint islands for the unique bake.
selected([head])
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(island_margin=.006)
bpy.ops.object.mode_set(mode="OBJECT")
head.data.uv_layers.active.name = "UVMap"

mix = head.data.color_attributes.new(name="CoatMix", type="FLOAT_COLOR", domain="CORNER")
for loop in head.data.loops:
    p = head.data.vertices[loop.vertex_index].co
    x, y, z = p
    a = abs(y)
    # Soft ivory bib and facial blaze, plus hand-positioned tabby M and cheek bars.
    ivory = max(0, min(1, (1.635-z)/.028))*max(0,min(1,(x+.018)/.11))
    if x > .115 and z < 1.615:
        ivory = max(ivory, max(0,min(1,(.13-a)/.032)))
    blaze = math.exp(-(y/.017)**2-((z-1.690)/.09)**2)*max(0,min(1,(x-.135)/.035))
    ivory = max(ivory, .78*blaze)
    mark = 0.0
    if x > .11 and z > 1.67:
        for yy, zz in [(-.057,1.747),(-.019,1.759),(.019,1.759),(.057,1.747)]:
            mark = max(mark, math.exp(-((y-yy)/.009)**2-((z-zz)/.069)**2)*.77)
    if a > .074 and .09 < x < .19:
        for zz, bend in [(1.646,.105),(1.607,.112),(1.568,.123)]:
            mark = max(mark, math.exp(-((z-zz-(x-.12)*.22)/.007)**2-((a-bend)/.046)**2)*.68)
    n = noise_vector(Vector((x*87,y*81,z*77))).length
    mark = max(0,min(.9,mark*(.82+.24*n)))
    mix.data[loop.index].color = (ivory, mark, 0, 1)

# Copy project-owned swatches into the isolated study for editability and
# traceable bake inputs. The original user image is intentionally not copied.
texture_sources = {}
for key, filename in {
    "grey":"T_Nyaakoto_fur_grey_Albedo.png",
    "white":"T_Nyaakoto_fur_white_Albedo.png",
    "dark":"T_Nyaakoto_fur_charcoal_Albedo.png",
}.items():
    src = PBR / filename
    dst = ROOT / filename
    shutil.copy2(src, dst)
    texture_sources[key] = dst
shutil.copy2(EYE, ROOT / EYE.name)

author = bpy.data.materials.new("M_HeadFur_EditableAuthoring")
author.use_nodes = True
author.node_tree.nodes.clear()
nodes = author.node_tree.nodes
links = author.node_tree.links
attr = nodes.new("ShaderNodeAttribute")
attr.attribute_name = "CoatMix"
sep = nodes.new("ShaderNodeSeparateColor")
links.new(attr.outputs["Color"], sep.inputs["Color"])
texcoord = nodes.new("ShaderNodeTexCoord")
scale = nodes.new("ShaderNodeVectorMath")
scale.operation = "SCALE"
scale.inputs[3].default_value = 3.4
links.new(texcoord.outputs["Generated"],scale.inputs[0])
images = {}
for key, path in texture_sources.items():
    im = bpy.data.images.load(str(path), check_existing=False)
    im.pack()
    node = nodes.new("ShaderNodeTexImage")
    node.image = im
    node.projection = "BOX"
    node.projection_blend = .32
    links.new(scale.outputs["Vector"],node.inputs["Vector"])
    images[key] = node
light = nodes.new("ShaderNodeMixRGB")
links.new(sep.outputs["Red"], light.inputs[0])
links.new(images["grey"].outputs["Color"], light.inputs[1])
links.new(images["white"].outputs["Color"], light.inputs[2])
stripe = nodes.new("ShaderNodeMixRGB")
links.new(sep.outputs["Green"], stripe.inputs[0])
links.new(light.outputs[0],stripe.inputs[1])
links.new(images["dark"].outputs["Color"],stripe.inputs[2])
emission = nodes.new("ShaderNodeEmission")
links.new(stripe.outputs[0],emission.inputs["Color"])
out = nodes.new("ShaderNodeOutputMaterial")
links.new(emission.outputs[0],out.inputs["Surface"])
bake_target = nodes.new("ShaderNodeTexImage")
bake_target.name = "SelectedBakeTarget"
bake_image = bpy.data.images.new("T_Nyaakoto_HeadStudy_Albedo",width=2048,height=2048,alpha=True)
bake_target.image = bake_image
nodes.active = bake_target
head.data.materials.clear()
head.data.materials.append(author)
selected([head])
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = 4
bpy.context.scene.render.bake.margin = 8
bpy.ops.object.bake(type="EMIT")
bake_image.filepath_raw = str(ROOT / "T_Nyaakoto_HeadStudy_Albedo.png")
bake_image.file_format = "PNG"
bake_image.save()

baked = material("M_Nyaakoto_HeadStudy_BakedPBR",(.7,.7,.7),.82)
bsdf = baked.node_tree.nodes.get("Principled BSDF")
tex = baked.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = bake_image
baked.node_tree.links.new(tex.outputs["Color"],bsdf.inputs["Base Color"])
noise = baked.node_tree.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 325
bump = baked.node_tree.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = .16
bump.inputs["Distance"].default_value = .00022
baked.node_tree.links.new(noise.outputs["Fac"],bump.inputs["Height"])
baked.node_tree.links.new(bump.outputs["Normal"],bsdf.inputs["Normal"])
head.data.materials.clear()
head.data.materials.append(baked)
head["deform_target"] = "head + jaw sculpt retopology needed; no production skin yet"


def mesh_object(name, vertices, faces, mat, uv_by_vertex=None, face_mats=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    if isinstance(mat,list):
        for m in mat: data.materials.append(m)
    else:
        data.materials.append(mat)
    layer = data.uv_layers.new(name="UVMap")
    for face in data.polygons:
        face.use_smooth = True
        if face_mats: face.material_index = face_mats[face.index]
        for li in face.loop_indices:
            idx = data.loops[li].vertex_index
            layer.data[li].uv = uv_by_vertex[idx] if uv_by_vertex else (0,0)
    return ob


def ear(side):
    verts=[];uvs=[];faces=[];mats=[]
    rows = 12; cols = 12
    for surface in (0,1):
        for j in range(rows+1):
            t=j/rows
            z=1.767+.130*t
            center=side*(.109+.023*t)
            half=(.039*(1-t)**.75+.001)*(.90+.10*math.sin(math.pi*t))
            x_rim=.054-.022*t
            for i in range(cols+1):
                u=2*i/cols-1
                # Center of front cartilage sits deeper than rolled rim.
                hollow=.013*(1-u*u)*math.sin(math.pi*min(1,t+.05))
                x=x_rim-hollow-(.008+.003*t if surface else 0)
                verts.append((x,center+side*u*half,z))
                uvs.append((i/cols,t))
    stride=cols+1;sheet=(rows+1)*stride
    for surf in (0,1):
        for j in range(rows):
            for i in range(cols):
                a=surf*sheet+j*stride+i
                quad=(a,a+1,a+stride+1,a+stride)
                faces.append(quad if surf==0 else quad[::-1])
                mats.append(1 if surf==0 and 1<i<cols-2 and j>1 else (0 if surf==0 else 2))
    for j in range(rows):
        for i in (0,cols):
            a=j*stride+i;b=(j+1)*stride+i
            faces.append((a,b,b+sheet,a+sheet));mats.append(2)
    ob=mesh_object(f"Ear_CuppedCartilage_{side}",verts,faces,[EAR_OUT,EAR_IN,EAR_RIM],uvs,mats)
    return ob


ears=[ear(-1),ear(1)]


def curve_tube(name, pts, radius, mat, resolution=2):
    curve=bpy.data.curves.new(name,"CURVE")
    curve.dimensions="3D"
    curve.resolution_u=16
    curve.bevel_depth=radius
    curve.bevel_resolution=resolution
    spline=curve.splines.new("BEZIER")
    spline.bezier_points.add(len(pts)-1)
    for bp,p in zip(spline.bezier_points,pts):
        bp.co=p
        bp.handle_left_type="AUTO";bp.handle_right_type="AUTO"
    ob=bpy.data.objects.new(name,curve)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    selected([ob])
    bpy.ops.object.convert(target="MESH")
    ob=bpy.context.object
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name="UVMap")
    return ob


def eye(side):
    y=side*.070
    uv_sphere(f"Eye_socket_shadow_{side}",(.168,y,1.672),(.025,.032,.021),SOCKET,48,24)
    uv_sphere(f"Eye_globe_{side}",(.169,y,1.671),(.027,.025,.021),SCLERA,48,24)
    # Iris is a convex tessellated disc with centered UVs rather than an
    # untextured blue glass bead.
    verts=[(.195,y,1.671)];uvs=[(.5,.5)];faces=[]
    for ring in range(1,7):
        r=ring/6
        for i in range(48):
            a=i*2*math.pi/48
            yy=y+.016*r*math.cos(a)
            zz=1.671+.014*r*math.sin(a)
            xx=.195-.003*r*r
            verts.append((xx,yy,zz))
            uvs.append((.5+.48*r*math.cos(a),.5+.48*r*math.sin(a)))
    for i in range(48):faces.append((0,1+i,1+(i+1)%48))
    for ring in range(1,6):
        for i in range(48):
            a=1+(ring-1)*48+i;b=1+(ring-1)*48+(i+1)%48
            faces.append((a,b,b+48,a+48))
    iris_mat=material("M_Iris_BlueGrey",(.37,.53,.62),.30)
    iris_tex=iris_mat.node_tree.nodes.new("ShaderNodeTexImage")
    iris_tex.image=bpy.data.images.load(str(ROOT/EYE.name),check_existing=True)
    iris_mat.node_tree.links.new(iris_tex.outputs["Color"],iris_mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    mesh_object(f"Iris_UV0_{side}",verts,faces,iris_mat,uvs)
    uv_sphere(f"Eye_Pupil_Slit_{side}",(.197,y,1.671),(.0014,.0022,.011),PUPIL,24,16)
    uv_sphere(f"Cornea_ClearConvex_{side}",(.183,y,1.671),(.015,.019,.016),CORNEA,48,24)
    # Upper lid droops over the iris; lower lid encloses the ocular globe.
    for upper in (True,False):
        coords=[]
        for k in range(9):
            u=-1+2*k/8
            yy=y+u*.030
            zz=1.671+(1 if upper else -1)*(.006+.012*math.sqrt(max(0,1-u*u)))
            xx=.190+.006*math.sqrt(max(0,1-u*u))
            coords.append((xx,yy,zz))
        curve_tube(f"{'Upper' if upper else 'Lower'}_LidMargin_{side}",coords,.0018,EAR_OUT)
        if upper:
            wet=[(x+.0007,yy,z-.0015) for x,yy,z in coords]
            curve_tube(f"Upper_Wetline_{side}",wet,.0006,WET)
    # Medial canthus partly masks the spherical endpoint.
    uv_sphere(f"Eye_medial_canthus_{side}",(.191,side*.045,1.670),(.004,.005,.004),EAR_IN,16,12)


for side in (-1,1):eye(side)

# Nose leather is a shallow triangular organ with paired recessed nares.
noseverts=[(.242,-.025,1.592),(.246,.025,1.592),(.254,0,1.572),(.238,0,1.580),
           (.246,-.020,1.585),(.247,.020,1.585)]
nosefaces=[(0,1,3),(0,3,2),(1,2,3),(0,4,2),(1,2,5)]
mesh_object("Nose_Leather_Triangular",noseverts,nosefaces,NOSE,
            [(0,1),(1,1),(.5,0),(.5,.45),(.15,.55),(.85,.55)])
for side in (-1,1):
    uv_sphere(f"Naris_{side}",(.251,side*.012,1.582),(.0009,.0042,.0022),NOSE_DARK,16,10)
curve_tube("Philtrum",[(.250,0,1.571),(.251,0,1.559),(.247,0,1.549)],.0008,NOSE_DARK)
curve_tube("Mouth_Left",[(.247,0,1.549),(.230,-.021,1.543),(.213,-.039,1.547)],.0008,NOSE_DARK)
curve_tube("Mouth_Right",[(.247,0,1.549),(.230,.021,1.543),(.213,.039,1.547)],.0008,NOSE_DARK)

for side in (-1,1):
    for row in range(3):
        for col in range(4):
            yy=side*(.025+.011*col)
            xx=.225-.007*col-.004*row
            zz=1.584-.010*row+.001*(col%2)
            uv_sphere(f"Follicle_{side}_{row}_{col}",(xx,yy,zz),(.0012,.0011,.0011),NOSE_DARK,12,8)
    for k in range(9):
        yy=side*(.041+.002*(k%3))
        z=1.579-.006*(k//3)
        root=(.221-.006*(k%3),yy,z)
        reach=.060+.020*random.random()
        tip=(.167-.020*random.random(),side*(.125+reach),z+.016*(k%3-1))
        mid=(.205,side*(.115+reach*.27),z+.008)
        curve_tube(f"Whisker_{side}_{k}",[root,mid,tip],.00030,WHISKER,1)

# Silhouette fur cards: original tapered meshes, rooted on the head and
# oriented along feline growth (crown caudal, cheek lateral/down, jaw ventral).
card_verts=[];card_faces=[];card_uv=[];card_mats=[]
center=Vector((.042,0,1.667))
for i in range(780):
    theta=random.uniform(-2.55,2.55)
    z=random.uniform(1.565,1.795)
    if abs(theta)<.45 and z<1.625:continue # leave eye/nose/muzzle legible
    ray=Vector((math.cos(theta),math.sin(theta),(z-1.667)/.12)).normalized()
    hit,point,normal,_=head.ray_cast(center,ray)
    if not hit:continue
    if point.x>.128 and abs(point.y)<.107 and 1.645<point.z<1.705:continue
    side=1 if point.y>=0 else -1
    growth=Vector((-.35,side*.40,-.72 if point.z<1.72 else .18))
    growth=(growth-normal*growth.dot(normal)).normalized()
    width_dir=growth.cross(normal).normalized()
    length=random.uniform(.004,.012)
    width=random.uniform(.0008,.0022)
    base=point+normal*.0005
    tip=base+growth*length+normal*random.uniform(.001,.004)
    count=len(card_verts)
    card_verts += [tuple(base-width_dir*width*.5),tuple(base+width_dir*width*.5),tuple(tip+width_dir*width*.08)]
    card_uv += [(0,0),(1,0),(.5,1)]
    card_faces.append((count,count+1,count+2))
    card_mats.append(1 if point.x>.12 and point.z<1.62 else 0)
cards=mesh_object("Fur_Cards_Head_Directional",card_verts,card_faces,[GREY,WHITE],card_uv,card_mats)
cards["rendering_note"]="Opaque geometry cards for M1 fallback; needs artist groom and atlas before integration"

# Small ear tufts remain separate from cartilage, for targeted LOD pruning.
for side in (-1,1):
    for k in range(21):
        y=side*(.105+.035*random.random())
        z=1.784+.088*random.random()
        x=.047-.018*((z-1.784)/.088)
        curve_tube(f"Ear_guard_hair_{side}_{k}",[(x,y,z),(x+.006,y+side*.005,z+.012),
            (x+.009,y+side*.010,z+.023+random.uniform(-.006,.006))],.00026,WHISKER,1)

# Review objects are in their own collection and excluded from FBX.
geometry=[o for o in bpy.context.scene.objects if o.type=="MESH"]
for ob in geometry:
    ob["source_study_only"] = True

selected(geometry)
bpy.ops.export_scene.fbx(filepath=str(ROOT/"SM_Nyaakoto_AnatomicalHead_Study.fbx"),
    use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
    add_leaf_bones=False, path_mode="COPY", embed_textures=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE")

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=24
scene.render.resolution_x=960;scene.render.resolution_y=960
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.world.color=(.12,.11,.10)

def area(name,loc,energy,size,color):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=energy;data.shape="DISK";data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    obj.location=loc
    direction=Vector((.12,0,1.68))-obj.location
    obj.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    return obj

area("Key_softbox",(.56,-.42,2.11),18,.57,(1.0,.90,.80))
area("Fill_card",(.33,.50,1.78),9,.75,(.73,.83,1.0))
area("Rim_strip",(-.32,.18,2.13),12,.42,(1.0,.84,.70))

cam_data=bpy.data.cameras.new("Portrait_85mm")
cam=bpy.data.objects.new("Portrait_85mm",cam_data)
bpy.context.collection.objects.link(cam)
cam.data.type="ORTHO";cam.data.ortho_scale=.48
scene.camera=cam
scene.view_settings.view_transform="AgX"
scene.view_settings.look="AgX - Medium High Contrast"
scene.view_settings.exposure=-.35

for label,location in [
    ("Front",(.72,0,1.66)),
    ("ThreeQuarter",(.55,-.49,1.72)),
    ("Profile",(.05,-.75,1.68)),
]:
    cam.location=location
    cam.rotation_euler=(Vector((.080,0,1.674))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(ROOT/f"Nyaakoto_HeadStudy_{label}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Nyaakoto_AnatomicalHead_Study.blend"))

manifest={
    "schema_version":1,
    "identity":"Nyaakoto / ニャーコト source-only feline head study",
    "scale":"meters; +X face forward, +Z up; existing character coordinates",
    "fbx":"SM_Nyaakoto_AnatomicalHead_Study.fbx",
    "source_blend":"Nyaakoto_AnatomicalHead_Study.blend",
    "uv_channel":"UVMap / UV0 on every mesh",
    "user_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
    "user_reference_embedded":False,
    "anatomy_reference":"https://commons.wikimedia.org/wiki/File:KATZENSCHAEDEL_LATERAL_1280x1024.jpg (CC0; visual reference only, not embedded)",
    "texture_provenance":"Copies of project-owned OpenAI-generated fur swatches and iris bitmap; see ../Hero/PBR/Source/README.md",
    "baked_albedo":"T_Nyaakoto_HeadStudy_Albedo.png",
    "production_status":"REVIEW_ONLY; no integration, rig, game import, or photoreal qualification",
    "files_sha256":{}
}
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.suffix != ".blend1" and p.name not in {
        "manifest.json", "create_head_study.py", "validate_head_study.py", "README.md"
    }:
        manifest["files_sha256"][str(p.relative_to(ROOT))]=sha(p)
(ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAKOTO_HEAD_STUDY_COMPLETE",len(geometry),"mesh objects",len(head.data.polygons),"head polys")
