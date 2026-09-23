"""Isolated Nyaakoto facial-anatomy revision; Blender 5.2 LTS.

Run from repository root with:
  blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoAnatomyV2/create_anatomy_v2.py

This deliberately does not touch the game character or its import pipeline.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.noise import noise_vector


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
PBR = REPO / "Content/SourceArt/Characters/Hero/PBR"
EYE = REPO / "Content/SourceArt/Characters/Hero/EyeStudy/T_Nyaakoto_Iris_Albedo.png"
random.seed(260924)

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
LID = material("M_Fur_Lid_Review", (.18, .17, .16), .9)
EAR_OUT = material("M_Ear_Cartilage_Outer", (.29, .265, .25), .85)
EAR_IN = material("M_Ear_Cartilage_Inner", (.33, .185, .17), .77)
EAR_RIM = material("M_Ear_LightRim", (.59, .54, .47), .87)
BOWL = material("M_Ear_GradatedBowl", (.29, .265, .25), .86)
ear_attr = BOWL.node_tree.nodes.new("ShaderNodeAttribute")
ear_attr.attribute_name = "BowlMix"
ear_mix = BOWL.node_tree.nodes.new("ShaderNodeMixRGB")
ear_mix.blend_type = "MIX"
ear_mix.inputs[1].default_value = (.29, .265, .25, 1)
ear_mix.inputs[2].default_value = (.33, .185, .17, 1)
BOWL.node_tree.links.new(ear_attr.outputs["Fac"], ear_mix.inputs[0])
BOWL.node_tree.links.new(ear_mix.outputs[0], BOWL.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
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
    uv_sphere("work_braincase", (.012, 0, 1.680), (.142, .121, .101), GREY),
    uv_sphere("work_facial_wedge", (.092, 0, 1.654), (.096, .085, .070), GREY),
    uv_sphere("work_nasal_bridge", (.161, 0, 1.661), (.055, .030, .043), GREY),
    uv_sphere("work_mandible", (.136, 0, 1.568), (.076, .065, .026), GREY),
    uv_sphere("work_throat", (.008, 0, 1.530), (.087, .078, .102), GREY),
]
for side in (-1, 1):
    shell_parts.extend([
        uv_sphere(f"work_zygomatic_{side}", (.082, side*.080, 1.625), (.069, .044, .037), GREY),
        uv_sphere(f"work_whisker_pad_{side}", (.178, side*.033, 1.583), (.036, .028, .017), GREY),
        uv_sphere(f"work_brow_{side}", (.128, side*.060, 1.698), (.044, .037, .012), GREY),
    ])
selected(shell_parts)
bpy.ops.object.join()
head = bpy.context.object
head.name = "SM_Nyaakoto_FacialAnatomy_V2_Study"
# Joining keeps the first sphere's transform. All subsequent anatomical
# coordinates, coat masks, and fur-root rays use world-aligned local meters.
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
head.data.remesh_voxel_size = .0024
bpy.ops.object.voxel_remesh()
smooth = head.modifiers.new("AnatomicalSmoothing", "SMOOTH")
smooth.factor = 1.18
smooth.iterations = 7
bpy.ops.object.modifier_apply(modifier=smooth.name)

# Carve true orbital recesses; taper the forehead and narrow the jaw.
for v in head.data.vertices:
    x, y, z = v.co
    ay = abs(y)
    if z > 1.69:
        v.co.y *= 1 - .075*min(1.0, (z-1.69)/.09)
    if 1.59 < z < 1.67 and x > .075:
        cheek = math.exp(-((z-1.626)/.042)**2-((ay-.088)/.048)**2)
        v.co.y += math.copysign(.0025*cheek, y)
    if x > .105:
        orbit = math.exp(-((ay-.066)/.027)**2-((z-1.677)/.018)**2)
        v.co.x -= .010*orbit
    if z < 1.58 and x < .13:
        v.co.y *= .91
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
    ivory = max(0, min(1, (1.632-z)/.027))*max(0,min(1,(x+.010)/.095))
    if x > .125 and z < 1.611:
        ivory = max(ivory, max(0,min(1,(.085-a)/.030)))
    blaze = math.exp(-(y/.015)**2-((z-1.688)/.072)**2)*max(0,min(1,(x-.125)/.032))
    ivory = max(ivory, .62*blaze)
    mark = 0.0
    if x > .07 and z > 1.688:
        for yy, zz in [(-.056,1.737),(-.020,1.752),(.020,1.752),(.056,1.737)]:
            mark = max(mark, math.exp(-((y-yy)/.006)**2-((z-zz)/.045)**2)*.88)
    if a > .066 and .07 < x < .18:
        for zz, bend in [(1.646,.079),(1.613,.084),(1.589,.089)]:
            mark = max(mark, math.exp(-((z-zz-(x-.12)*.16)/.005)**2-((a-bend)/.030)**2)*.78)
    n = noise_vector(Vector((x*87,y*81,z*77))).length
    mark = max(0,min(.9,mark*(.82+.24*n)))
    mix.data[loop.index].color = (ivory, mark, 0, 1)

# Pack project-owned swatches in the editable Blender study. The supplied
# user screenshot is a design reference and is never copied into the asset.
texture_sources = {}
for key, filename in {
    "grey":"T_Nyaakoto_fur_grey_Albedo.png",
    "white":"T_Nyaakoto_fur_white_Albedo.png",
    "dark":"T_Nyaakoto_fur_charcoal_Albedo.png",
}.items():
    src = PBR / filename
    texture_sources[key] = src

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
    verts=[];uvs=[];faces=[]
    rows = 20; cols = 16
    for surface in (0,1):
        for j in range(rows+1):
            t=j/rows
            z=1.752+.109*t
            center=side*(.096+.018*t+.003*math.sin(math.pi*t))
            half=(.038*(1-t)**.78+.0006)*(.98+.02*math.sin(math.pi*t))
            for i in range(cols+1):
                u=2*i/cols-1
                # Front-facing bowl recedes behind a rolled margin; the two
                # surfaces form substantial tapered cartilage, not a plane.
                hollow=.014*(1-u*u)*math.sin(math.pi*(.10+.80*t))
                x=(.043-.034*t-hollow) if surface==0 else (.006-.020*t+.003*(1-u*u))
                verts.append((x,center+side*u*half,z))
                uvs.append((i/cols,t))
    stride=cols+1;sheet=(rows+1)*stride
    for surf in (0,1):
        for j in range(rows):
            for i in range(cols):
                a=surf*sheet+j*stride+i
                quad=(a,a+1,a+stride+1,a+stride)
                faces.append(quad if surf==0 else quad[::-1])
    for j in range(rows):
        for i in (0,cols):
            a=j*stride+i;b=(j+1)*stride+i
            faces.append((a,b,b+sheet,a+sheet))
    ob=mesh_object(f"Ear_CuppedCartilage_{side}",verts,faces,BOWL,uvs)
    color=ob.data.color_attributes.new(name="BowlMix",type="FLOAT_COLOR",domain="CORNER")
    for loop in ob.data.loops:
        idx=loop.vertex_index
        if idx>=sheet:
            value=0
        else:
            j=idx//stride;i=idx%stride
            t=j/rows;u=abs(2*i/cols-1)
            value=max(0,min(1,(.83-u)/.48))*max(0,min(1,(t-.09)/.25))*(.72+.18*t)
        color.data[loop.index].color=(value,value,value,1)
    for edge in (-1,1):
        pts=[]
        for j in range(17):
            t=j/16
            z=1.752+.109*t
            center=side*(.096+.018*t+.003*math.sin(math.pi*t))
            half=.038*(1-t)**.78+.0006
            pts.append((.043-.034*t,center+side*edge*half,z))
        curve_tube(f"Ear_rolled_margin_{side}_{edge}",pts,.0014,EAR_OUT,2)
    return ob


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


ears=[ear(-1),ear(1)]


def eye(side):
    y=side*.064
    uv_sphere(f"Eye_socket_shadow_{side}",(.145,y,1.679),(.017,.027,.014),SOCKET,48,24)
    uv_sphere(f"Eye_globe_{side}",(.148,y,1.678),(.017,.020,.014),SCLERA,48,24)
    # Iris is a convex tessellated disc with centered UVs rather than an
    # untextured blue glass bead.
    verts=[(.166,y,1.678)];uvs=[(.5,.5)];faces=[]
    for ring in range(1,7):
        r=ring/6
        for i in range(48):
            a=i*2*math.pi/48
            yy=y+.013*r*math.cos(a)
            zz=1.678+.011*r*math.sin(a)
            xx=.166-.002*r*r
            verts.append((xx,yy,zz))
            uvs.append((.5+.48*r*math.cos(a),.5+.48*r*math.sin(a)))
    for i in range(48):faces.append((0,1+i,1+(i+1)%48))
    for ring in range(1,6):
        for i in range(48):
            a=1+(ring-1)*48+i;b=1+(ring-1)*48+(i+1)%48
            faces.append((a,b,b+48,a+48))
    iris_mat=material("M_Iris_BlueGrey",(.37,.53,.62),.30)
    iris_tex=iris_mat.node_tree.nodes.new("ShaderNodeTexImage")
    iris_tex.image=bpy.data.images.load(str(EYE),check_existing=True)
    iris_tex.image.pack()
    iris_mat.node_tree.links.new(iris_tex.outputs["Color"],iris_mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])
    mesh_object(f"Iris_UV0_{side}",verts,faces,iris_mat,uvs)
    uv_sphere(f"Eye_Pupil_Slit_{side}",(.168,y,1.678),(.0009,.0014,.008),PUPIL,24,16)
    uv_sphere(f"Cornea_ClearConvex_{side}",(.160,y,1.678),(.009,.014,.011),CORNEA,48,24)
    # Fur-bearing tarsal shelves occlude the globe; a narrow aperture reads
    # as a living eye rather than an exposed bead or white outlined ring.
    for upper in (True,False):
        coords=[]
        for k in range(17):
            u=-1+2*k/16
            yy=y+u*.025
            arch=math.sqrt(max(0,1-u*u))
            zz=1.678+(1 if upper else -1)*(.001+.0085*arch)
            xx=.165+.002*arch
            coords.append((xx,yy,zz))
        curve_tube(f"{'Upper' if upper else 'Lower'}_TarsalMargin_{side}",coords,.0009,LID,1)
        if upper:
            wet=[(x+.0003,yy,z-.0007) for x,yy,z in coords]
            curve_tube(f"Upper_Wetline_{side}",wet,.00025,WET,1)
    # Medial canthus partly masks the spherical endpoint.
    uv_sphere(f"Eye_medial_canthus_{side}",(.160,side*.042,1.677),(.002,.003,.002),EAR_IN,16,12)


for side in (-1,1):eye(side)

# Cartilaginous nose leather tapers ventrally rather than being a flat
# triangle stuck to the muzzle. It is deliberately small relative to the face.
nose=uv_sphere("Nose_Leather_Tapered",(.218,0,1.589),(.008,.015,.007),NOSE,48,24)
for v in nose.data.vertices:
    if v.co.z < 0:
        v.co.y *= 1+.62*v.co.z/.007
    if v.co.z > 0:
        v.co.x *= 1-.10*v.co.z/.007
for side in (-1,1):
    uv_sphere(f"Naris_{side}",(.225,side*.008,1.587),(.0005,.0028,.0012),NOSE_DARK,16,10)
curve_tube("Philtrum",[(.223,0,1.583),(.223,0,1.570),(.221,0,1.563)],.00035,NOSE_DARK,1)
curve_tube("Mouth_Left",[(.221,0,1.563),(.211,-.013,1.557),(.200,-.026,1.560)],.00032,NOSE_DARK,1)
curve_tube("Mouth_Right",[(.221,0,1.563),(.211,.013,1.557),(.200,.026,1.560)],.00032,NOSE_DARK,1)

for side in (-1,1):
    for row in range(3):
        for col in range(4):
            yy=side*(.022+.009*col)
            xx=.214-.006*col-.003*row
            zz=1.586-.008*row+.001*(col%2)
            uv_sphere(f"Follicle_{side}_{row}_{col}",(xx,yy,zz),(.00065,.00065,.00065),NOSE_DARK,12,8)
    for k in range(10):
        yy=side*(.038+.002*(k%3))
        z=1.584-.004*(k//3)
        root=(.211-.005*(k%3),yy,z)
        reach=.057+.015*random.random()
        tip=(.153-.018*random.random(),side*(.103+reach),z+.009*(k%3-1))
        mid=(.196,side*(.103+reach*.25),z+.005)
        curve_tube(f"Whisker_{side}_{k}",[root,mid,tip],.00014,WHISKER,1)

# Silhouette fur cards: original tapered meshes, rooted on the head and
# oriented along feline growth (crown caudal, cheek lateral/down, jaw ventral).
card_verts=[];card_faces=[];card_uv=[];card_mats=[]
center=Vector((.042,0,1.667))
for i in range(15000):
    theta=random.uniform(-2.55,2.55)
    z=random.uniform(1.565,1.787)
    if abs(theta)<.34 and z<1.625:continue # leave nose/muzzle legible
    ray=Vector((math.cos(theta),math.sin(theta),(z-1.667)/.12)).normalized()
    hit,point,normal,_=head.ray_cast(center,ray)
    if not hit:continue
    if point.x>.135 and abs(point.y)<.095 and 1.652<point.z<1.701:continue
    side=1 if point.y>=0 else -1
    growth=Vector((-.35,side*.40,-.72 if point.z<1.72 else .18))
    growth=(growth-normal*growth.dot(normal)).normalized()
    width_dir=growth.cross(normal).normalized()
    length=random.uniform(.0018,.0048)
    if point.z<1.615 and point.x>.12:length*=1.3
    width=random.uniform(.00018,.00044)
    base=point+normal*.00010
    tip=base+growth*length+normal*random.uniform(.00025,.0012)
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
        y=side*(.095+.029*random.random())
        z=1.766+.078*random.random()
        x=.035-.023*((z-1.766)/.078)
        curve_tube(f"Ear_guard_hair_{side}_{k}",[(x,y,z),(x+.006,y+side*.005,z+.012),
            (x+.009,y+side*.010,z+.020+random.uniform(-.004,.004))],.00012,WHISKER,1)

# Review objects are in their own collection and excluded from FBX.
geometry=[o for o in bpy.context.scene.objects if o.type=="MESH"]
for ob in geometry:
    ob["source_study_only"] = True

selected(geometry)
bpy.ops.export_scene.fbx(filepath=str(ROOT/"SM_Nyaakoto_FacialAnatomy_V2_Study.fbx"),
    use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
    add_leaf_bones=False, path_mode="STRIP", embed_textures=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE")

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.samples=32
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
    ("Front",(.72,0,1.67)),
    ("ThreeQuarter",(.57,-.46,1.72)),
    ("Profile",(.04,-.75,1.68)),
]:
    cam.location=location
    cam.rotation_euler=(Vector((.080,0,1.674))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(ROOT/f"Nyaakoto_AnatomyV2_{label}.png")
    bpy.ops.render.render(write_still=True)

bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Nyaakoto_FacialAnatomy_V2_Study.blend"))

manifest={
    "schema_version":1,
    "identity":"Nyaakoto / ニャーコト source-only feline facial anatomy revision V2",
    "scale":"meters; +X face forward, +Z up; existing character coordinates",
    "fbx":"SM_Nyaakoto_FacialAnatomy_V2_Study.fbx",
    "source_blend":"Nyaakoto_FacialAnatomy_V2_Study.blend",
    "uv_channel":"UVMap / UV0 on every mesh",
    "user_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
    "user_reference_embedded":False,
    "anatomy_reference":"https://commons.wikimedia.org/wiki/File:KATZENSCHAEDEL_LATERAL_1280x1024.jpg (CC0; visual reference only, not embedded)",
    "texture_provenance":"Project-owned generated fur swatches and iris bitmap loaded from ../Hero/PBR and packed into the Blender source; see ../Hero/PBR/Source/README.md",
    "baked_albedo":"T_Nyaakoto_HeadStudy_Albedo.png",
    "production_status":"REVIEW_ONLY; no integration, rig, game import, or photoreal qualification",
    "files_sha256":{}
}
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.suffix != ".blend1" and p.name not in {
        "manifest.json", "create_anatomy_v2.py", "validate_anatomy_v2.py", "README.md"
    }:
        manifest["files_sha256"][str(p.relative_to(ROOT))]=sha(p)
(ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAKOTO_FACIAL_ANATOMY_V2_COMPLETE",len(geometry),"mesh objects",len(head.data.polygons),"head polys")
