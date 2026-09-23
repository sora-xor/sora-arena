"""Author an original, editable Nyaagyu feline-samurai world-character study.

Run with Blender 5.2.2: blender -b --factory-startup --python
scripts/art/create_nyaagyu_hero_character.py

This is an unrigged source-art prototype. +X is the character's facing direction,
+Z is up, and the feet stand at Z=0. The Blender render is a review image, not
an Unreal screenshot. Geometry, materials, and lighting are authored here; no
stock, purchased, or downloaded model/texture is used.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/Hero"
NAME = "SM_Nyaagyu_HeroCharacter"
BLEND = OUT / "Nyaagyu_HeroCharacter.blend"
FBX = OUT / f"{NAME}.fbx"
PREVIEW = OUT / "Nyaagyu_HeroCharacter_Blender.png"
DETAIL = OUT / "Nyaagyu_HeroFace_Blender.png"
MANIFEST = OUT / "manifest.json"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
parts = bpy.data.collections.new("NyaagyuHero_Editable")
scene.collection.children.link(parts)


def mat(name, rgb, *, rough=.65, metal=0.0, coat=0.0, noise=0.0, bump=.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    n, links = m.node_tree.nodes, m.node_tree.links
    bsdf = n.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    if noise:
        tex = n.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 3
        variance = n.new("ShaderNodeMapRange")
        variance.inputs["To Min"].default_value = max(.04, rough * .74)
        variance.inputs["To Max"].default_value = min(.98, rough * 1.19)
        links.new(tex.outputs["Fac"], variance.inputs["Value"])
        links.new(variance.outputs["Result"], bsdf.inputs["Roughness"])
        broad=n.new("ShaderNodeTexNoise")
        broad.inputs["Scale"].default_value=max(3,noise/27)
        broad.inputs["Detail"].default_value=4
        colors=n.new("ShaderNodeValToRGB")
        colors.color_ramp.elements[0].position=.23
        colors.color_ramp.elements[1].position=.79
        colors.color_ramp.elements[0].color=(*[max(0,c*.77) for c in rgb],1)
        colors.color_ramp.elements[1].color=(*[min(1,c*1.12) for c in rgb],1)
        links.new(broad.outputs["Fac"],colors.inputs["Fac"])
        links.new(colors.outputs["Color"],bsdf.inputs["Base Color"])
        if bump:
            b = n.new("ShaderNodeBump")
            b.inputs["Strength"].default_value = .20
            b.inputs["Distance"].default_value = bump
            links.new(tex.outputs["Fac"], b.inputs["Height"])
            links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


FUR = mat("M_Hero_AmberFur", (.39,.19,.079), rough=.93, noise=125, bump=.00025)
FUR_DARK = mat("M_Hero_UmberFur", (.094,.051,.032), rough=.92, noise=132, bump=.00019)
FUR_LIGHT = mat("M_Hero_CreamFur", (.68,.55,.39), rough=.91, noise=112, bump=.00018)
EAR_INNER = mat("M_Hero_EarSkin", (.30,.096,.089), rough=.82, noise=83, bump=.00006)
NOSE = mat("M_Hero_RoseNose", (.23,.086,.082), rough=.47)
EYE = mat("M_Hero_AmberEye", (.73,.34,.043), rough=.15, coat=.42)
EYE_DARK = mat("M_Hero_EyePupil", (.008,.012,.013), rough=.19, coat=.28)
EYE_WHITE = mat("M_Hero_EyeGlint", (.83,.78,.61), rough=.15)
INDIGO = mat("M_Hero_IndigoSilk", (.019,.039,.063), rough=.80, noise=185, bump=.00013)
INDIGO_LIGHT = mat("M_Hero_FoldedIndigo", (.043,.071,.096), rough=.84, noise=190, bump=.00013)
KIMONO = mat("M_Hero_UndyedLinen", (.46,.39,.30), rough=.91, noise=185, bump=.00017)
LACQUER = mat("M_Hero_OxbloodUrushi", (.072,.016,.014), rough=.25, coat=.65, noise=58, bump=.00006)
LACQUER_DARK = mat("M_Hero_BlackUrushi", (.015,.014,.014), rough=.28, coat=.57, noise=62, bump=.00006)
IRON = mat("M_Hero_BlackenedIron", (.052,.057,.060), rough=.35, metal=.90, noise=107, bump=.00009)
BRASS = mat("M_Hero_AgedBrass", (.43,.25,.093), rough=.32, metal=.89, noise=89, bump=.00008)
SILVER = mat("M_Hero_BurnishedSteel", (.45,.51,.53), rough=.22, metal=.96, noise=109, bump=.00004)
CLAW = mat("M_Hero_IvoryClaw", (.63,.59,.48), rough=.43, noise=65)
TEAL = mat("M_Hero_JadeCircuit", (.016,.40,.34), rough=.25, metal=.19, emission=.35)
RESISTANCE_RED = mat("M_Hero_SORAResistanceRed", (.72,.036,.065), rough=.48)


def keep(obj, name, material):
    obj.name = name
    for c in tuple(obj.users_collection):
        c.objects.unlink(obj)
    parts.objects.link(obj)
    if material:
        obj.data.materials.append(material)
    obj["provenance"] = "Original SORA Arena source geometry"
    return obj


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def bevel(obj, amount=.003, segments=2):
    if amount:
        m = obj.modifiers.new("Hand_forged_edge", "BEVEL")
        m.width = amount
        m.segments = segments
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=m.name)
    return obj


def sphere(name, center, radii, material, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    o = keep(bpy.context.object, name, material)
    o.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return smooth(o)


def box(name, center, size, material, edge=.003):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = keep(bpy.context.object, name, material)
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return smooth(bevel(o, edge))


def line(name, points, radius, material, resolution=3):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for p, xyz in zip(spline.bezier_points, points):
        p.co = xyz
        p.handle_left_type = "AUTO"
        p.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, curve)
    parts.objects.link(o)
    curve.materials.append(material)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target="MESH")
    return smooth(bpy.context.object)


def bone(name, a, b, radius_a, radius_b, material, sides=18):
    a, b = Vector(a), Vector(b)
    d = b-a
    bpy.ops.mesh.primitive_cone_add(vertices=sides, radius1=radius_a, radius2=radius_b,
                                    depth=d.length, location=(a+b)/2)
    o = keep(bpy.context.object, name, material)
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return smooth(o)


def surface(name, vertices, faces, material, thickness=.0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    o = bpy.data.objects.new(name, mesh)
    parts.objects.link(o)
    mesh.materials.append(material)
    if thickness:
        mod = o.modifiers.new("Fabric_depth", "SOLIDIFY")
        mod.thickness = thickness
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return o


def ring_loft(name, rings, material, sides=32, pleats=0):
    vertices=[]; faces=[]
    for z, x0, rx, ry in rings:
        for i in range(sides):
            a=math.tau*i/sides
            p=1+pleats*math.cos(a*10)
            vertices.append((x0+rx*math.cos(a)*p, ry*math.sin(a)*p, z))
    for r in range(len(rings)-1):
        for i in range(sides):
            j=(i+1)%sides
            faces.append((r*sides+i,r*sides+j,(r+1)*sides+j,(r+1)*sides+i))
    return smooth(surface(name, vertices, faces, material, thickness=.004))


def short_fur_cards(name, center, radii, material, count, seed, skip_face=True):
    """Tiny authored mesh fibers for a first visual pass, not a strand groom."""
    rng=random.Random(seed)
    center=Vector(center);radii=Vector(radii)
    vertices=[];faces=[]
    for _ in range(count):
        z=rng.uniform(-1,1);theta=rng.uniform(0,math.tau)
        r=math.sqrt(max(0,1-z*z))
        n=Vector((r*math.cos(theta),r*math.sin(theta),z))
        if skip_face and n.x>.38 and abs(n.y)<.74:
            continue
        pos=center+Vector((n.x*radii.x,n.y*radii.y,n.z*radii.z))
        tangent=n.cross(Vector((0,0,1)))
        if tangent.length<.01:tangent=Vector((0,1,0))
        tangent.normalize()
        width=rng.uniform(.00022,.00065)
        tip=pos+(n*.48+Vector((-.25,0,-.18))).normalized()*rng.uniform(.003,.009)
        base=len(vertices)
        vertices.extend((pos-tangent*width,pos+tangent*width,tip))
        faces.append((base,base+1,base+2))
    return surface(name,vertices,faces,material)


def ear(sign):
    y=sign*.151
    base=[(-.055,y-sign*.075,1.661),(-.045,y+sign*.075,1.658),(.085,y+sign*.064,1.685),(.092,y-sign*.060,1.685)]
    tip=(.012,y+sign*.016,1.883)
    o=surface(f"Ear_outer_{sign}",base+[tip],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(0,3,2,1)],FUR_DARK,thickness=.006)
    # The asymmetrical pinna's forward inside is visibly recessed from the rim.
    q=[(.092,y-sign*.047,1.705),(.088,y+sign*.047,1.705),(.023,y+sign*.013,1.846)]
    surface(f"Ear_inner_{sign}",q,[(0,1,2)],EAR_INNER,thickness=.002)
    line(f"Ear_cream_edge_{sign}",[q[0],(.065,y-sign*.028,1.785),q[2]],.002,FUR_LIGHT)
    return o


# A grounded bipedal feline body, with separate jacket, neck and hakama panels.
ring_loft("Linen_under_kimono",[(.80,-.015,.16,.18),(.94,-.018,.19,.225),(1.15,-.02,.19,.24),(1.34,-.01,.145,.18)],KIMONO)
ring_loft("Indigo_samurai_haori",[(.85,-.024,.205,.255),(.99,-.024,.23,.29),(1.20,-.02,.225,.28),(1.38,-.01,.16,.20)],INDIGO_LIGHT)
ring_loft("Layered_hakama_waist",[(.68,-.015,.19,.245),(.77,-.015,.19,.245),(.87,-.015,.205,.26)],INDIGO,pleats=.035)
sphere("Fur_neck",(.02,0,1.413),(.105,.122,.135),FUR)

# Legs are actually split; visible paws and digitigrade lower-leg transitions.
for sign in (-1,1):
    y=sign*.143
    bone(f"Hakama_upper_leg_{sign}",(-.015,y,.795),(-.025,y,.435),.135,.11,INDIGO,24)
    bone(f"Hakama_shin_{sign}",(-.022,y,.445),(.025,y,.160),.105,.072,INDIGO,24)
    for fold in range(5):
        off=(fold-2)*.035
        line(f"Hakama_fold_{sign}_{fold}",[(.106,y+sign*off,.78),(.103,y+sign*off,.58),(.088,y+sign*off,.34)],.0015,INDIGO_LIGHT)
    sphere(f"Heel_paw_{sign}",(.042,y,.075),(.120,.105,.072),FUR_DARK)
    sphere(f"Tabi_toe_paw_{sign}",(.125,y,.052),(.126,.115,.053),FUR_LIGHT)
    for toe in range(4):
        ty=y+(toe-1.5)*.043
        sphere(f"Toe_{sign}_{toe}",(.218,ty,.047),(.038,.027,.035),FUR_LIGHT,16,12)
        bone(f"Claw_{sign}_{toe}",(.244,ty,.044),(.271,ty,.037),.008,.001,CLAW,8)
    box(f"Kyahan_greave_{sign}",(.063,y,.251),(.047,.162,.183),LACQUER_DARK,.013)
    for lace_z in (.19,.245,.30):
        line(f"Greave_braid_{sign}_{lace_z}",[(.09,y-sign*.08,lace_z),(.103,y,lace_z+.005),(.09,y+sign*.08,lace_z)],.0027,BRASS)

# Upper limbs deliberately stay in a broad neutral A-pose; no skinning claim.
for sign in (-1,1):
    sy=sign
    sphere(f"Shoulder_joint_{sign}",(.0,sy*.272,1.273),(.131,.125,.128),INDIGO)
    bone(f"Linen_sleeve_{sign}",(-.006,sy*.285,1.275),(.026,sy*.405,1.075),.124,.105,INDIGO_LIGHT,24)
    bone(f"Fur_forearm_{sign}",(.025,sy*.414,1.077),(.092,sy*.467,.887),.078,.064,FUR,20)
    sphere(f"Paw_hand_{sign}",(.091,sy*.474,.84),(.069,.078,.090),FUR,20,14)
    for digit in range(4):
        dy=(digit-1.5)*.033
        bone(f"Finger_{sign}_{digit}",(.132,sy*.474+dy,.807),(.148,sy*.474+dy,.734),.016,.010,FUR_LIGHT,8)
        sphere(f"Finger_knuckle_{sign}_{digit}",(.140,sy*.474+dy,.768),(.014,.013,.016),FUR,12,8)
        bone(f"Finger_claw_{sign}_{digit}",(.149,sy*.474+dy,.735),(.155,sy*.474+dy,.713),.006,.001,CLAW,8)
    bone(f"Thumb_{sign}",(.149,sy*.415,.854),(.191,sy*.419,.789),.025,.012,FUR_LIGHT,10)
    # Segmented shoulder sode and lacquer forearm guards communicate silhouette.
    for row in range(4):
        z=1.326-row*.047
        o=box(f"Sode_lamella_{sign}_{row}",(.027,sy*(.322+row*.025),z),(.155,.117,.035),LACQUER,.010)
        o.rotation_euler[0]=sy*.18
        for stud in (-1,1):
            sphere(f"Sode_rivet_{sign}_{row}_{stud}",(.111,sy*(.322+row*.025)+stud*.034,z+.006),(.006,.007,.007),BRASS,10,8)
    box(f"Kote_guard_{sign}",(.074,sy*.449,.994),(.095,.128,.160),LACQUER_DARK,.016)
    for z in (.94,.98,1.02):
        line(f"Kote_binding_{sign}_{z}",[(.133,sy*.385,z),(.135,sy*.453,z+.008),(.132,sy*.51,z)],.003,INDIGO)

# Chest plates are tailored over the actual volume rather than covering the face.
for row in range(6):
    z=.955+row*.060
    half_width=.212 if row<4 else .175
    for sign in (-1,1):
        y=sign*.108
        o=box(f"Do_lamellar_{row}_{sign}",(.188,y,z),(.037,half_width,.052),LACQUER,.008)
        o.rotation_euler[0]=sign*.055
        for j in (-1,1):
            sphere(f"Do_rivet_{row}_{sign}_{j}",(.210,y+j*.077,z),(.003,.004,.005),BRASS,8,6)
        line(f"Do_indigo_lacing_{row}_{sign}",[(.214,y-sign*.066,z+.016),(.215,y,z-.015),(.214,y+sign*.066,z+.016)],.0021,INDIGO)
box("Obi_waist",(.003,0,.858),(.39,.53,.085),INDIGO,.013)
box("Obi_burnished_plate",(.215,0,.858),(.023,.146,.091),BRASS,.009)
sphere("Clan_mon_roundel",(.230,0,.858),(.010,.051,.046),LACQUER_DARK,24,16)
for angle in range(6):
    a=math.tau*angle/6
    line(f"Clan_mon_ray_{angle}",[(.24,0,.858),(.242,.026*math.cos(a),.858+.024*math.sin(a))],.0028,BRASS)
line("Under_kimono_cross_collar_a",[(.163,-.14,1.356),(.188,.04,1.20),(.192,.129,1.102)],.020,KIMONO)
line("Under_kimono_cross_collar_b",[(.165,.14,1.355),(.193,-.025,1.205),(.197,-.110,1.13)],.018,INDIGO)

# Use the user's exact SVG paths as a small raised resistance insignia. The
# vector source is read byte-for-byte; this is not a redrawn approximation.
logo_svg=ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
logo_record=json.loads((logo_svg.parent/"sora_logo_manifest.json").read_text())
assert hashlib.sha256(logo_svg.read_bytes()).hexdigest()==logo_record["source_sha256"]
bone("Resistance_insignia_backing",(.222,-.108,1.207),(.230,-.108,1.207),.044,.044,LACQUER_DARK,32)
before=set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(logo_svg))
logo_curves=[o for o in set(bpy.data.objects)-before if o.type=="CURVE"]
assert len(logo_curves)==2, [o.name for o in logo_curves]
corners=[o.matrix_world @ Vector(c) for o in logo_curves for c in o.bound_box]
low_x=min(v.x for v in corners);high_x=max(v.x for v in corners)
low_y=min(v.y for v in corners);high_y=max(v.y for v in corners)
logo_center=((low_x+high_x)/2,(low_y+high_y)/2)
logo_scale=.069/max(high_x-low_x,high_y-low_y)
for index,o in enumerate(logo_curves):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target="MESH")
    o=bpy.context.object
    for vert in o.data.vertices:
        p=o.matrix_world @ vert.co
        vert.co=(.235, -.108+(p.x-logo_center[0])*logo_scale,
                 1.207+(p.y-logo_center[1])*logo_scale)
    o.matrix_world.identity()
    for c in tuple(o.users_collection):
        c.objects.unlink(o)
    parts.objects.link(o)
    o.name=f"UserSupplied_SORAInsignia_Path_{index}"
    o.data.materials.clear()
    o.data.materials.append(RESISTANCE_RED)
    o["source_svg_sha256"]=logo_record["source_sha256"]

# Head: short-furred broad cheeks, raised brow and correctly separated muzzle.
head_start=set(parts.objects)
sphere("Skull",(.04,0,1.644),(.193,.202,.196),FUR,48,32)
short_fur_cards("Head_short_mesh_fur",(.04,0,1.644),(.194,.203,.197),FUR,3800,781)
sphere("Lower_jaw",(.18,0,1.535),(.081,.099,.065),FUR_LIGHT,32,20)
for sign in (-1,1):
    ear(sign)
    sphere(f"Cheek_ruff_{sign}",(.070,sign*.153,1.576),(.065,.065,.071),FUR_LIGHT,28,20)
    short_fur_cards(f"Cheek_mesh_fur_{sign}",(.070,sign*.153,1.576),(.066,.066,.072),FUR_LIGHT,650,sign+234,False)
    sphere(f"Muzzle_pad_{sign}",(.218,sign*.051,1.568),(.057,.051,.036),FUR_LIGHT,30,20)
    sphere(f"Eye_socket_{sign}",(.193,sign*.089,1.672),(.018,.043,.032),FUR_DARK,30,20)
    sphere(f"Eye_iris_{sign}",(.208,sign*.089,1.672),(.008,.029,.024),EYE,32,20)
    sphere(f"Vertical_pupil_{sign}",(.215,sign*.089,1.672),(.004,.006,.021),EYE_DARK,16,12)
    sphere(f"Corneal_glint_{sign}",(.219,sign*.077,1.684),(.002,.004,.005),EYE_WHITE,12,8)
    line(f"Angular_brow_{sign}",[(.184,sign*.044,1.713),(.196,sign*.088,1.721),(.174,sign*.131,1.710)],.006,FUR_DARK)
    for dot in range(3):
        sphere(f"Muzzle_follicle_{sign}_{dot}",(.275,sign*(.042+dot*.014),1.567-dot*.010),(.0018,.002,.0018),FUR_DARK,8,6)
    for w in range(4):
        line(f"Whisker_{sign}_{w}",[(.270,sign*.051,1.57+w*.006),(.307,sign*.16,1.573+(w-2)*.018),(.285,sign*.32,1.57+(w-2)*.035)],.0007,FUR_LIGHT,2)
    for stripe in range(3):
        z=1.596+stripe*.042
        line(f"Tiger_cheek_stripe_{sign}_{stripe}",[(.103,sign*.196,z+.018),(.132,sign*.181,z+.001),(.157,sign*.159,z-.019)],.0044,FUR_DARK,2)
    for whisker in range(24):
        rng=random.Random(240+sign*100+whisker)
        a=rng.uniform(-.55,.55)
        y=sign*(.155+rng.uniform(-.025,.025))
        z=1.55+rng.uniform(-.06,.07)
        line(f"Guard_hair_{sign}_{whisker}",[(.075,y,z),(.026,y+sign*.040,z+a*.035)],.0006,FUR_LIGHT,1)
sphere("Soft_nose_bridge",(.202,0,1.626),(.060,.060,.035),FUR)
for sign in (-1,1):
    for stripe in range(2):
        y0=sign*(.022+stripe*.043)
        line(f"Forehead_tabby_mark_{sign}_{stripe}",[(.173,y0,1.762),(.158,y0+sign*.019,1.790),(.127,y0+sign*.045,1.813)],.004,FUR_DARK,2)
sphere("Triangular_nose",(.280,0,1.586),(.022,.027,.014),NOSE,24,14)
line("Philtrum",[(.297,0,1.58),(.29,0,1.547)],.0017,FUR_DARK)
line("Mouth_right",[(.29,0,1.547),(.28,.054,1.541)],.0014,FUR_DARK)
line("Mouth_left",[(.29,0,1.547),(.28,-.054,1.541)],.0014,FUR_DARK)

# Knotted head cloth and ear-clear helmet brim, without enclosing the cat face.
line("Hachimaki_headband",[(.16,-.172,1.762),(.065,-.202,1.784),(-.118,-.143,1.781),(-.150,0,1.779),(-.118,.143,1.781),(.066,.202,1.783),(.16,.171,1.762)],.010,INDIGO)
sphere("Hachimaki_knot",(-.166,-.138,1.77),(.043,.045,.041),INDIGO_LIGHT)
surface("Hachimaki_trailing_cloth",[(-.17,-.148,1.77),(-.23,-.19,1.72),(-.29,-.21,1.55),(-.27,-.16,1.56)],[(0,1,2,3)],INDIGO,thickness=.002)

# A restrained head-to-shoulder ratio avoids a mascot silhouette. Apply the
# same transform to all facial parts, ears, whiskers and the hachimaki.
head_anchor=Vector((.04,0,1.620))
head_reduction=.85
head_transform=(Matrix.Translation(head_anchor)
                @ Matrix.Scale(head_reduction,4)
                @ Matrix.Translation(-head_anchor))
for o in set(parts.objects)-head_start:
    o.matrix_world=head_transform @ o.matrix_world

# Lively, raised tail with dark rings and a tapered cream tip.
tail=[(-.16,0,.80),(-.33,.04,.76),(-.44,.105,.82),(-.50,.15,.98),(-.60,.18,1.07)]
line("Tail_arched",tail,.052,FUR,5)
for i,p in enumerate(((-.345,.048,.785),(-.43,.095,.84),(-.49,.14,.94),(-.535,.162,1.025))):
    sphere(f"Tail_dark_ring_{i}",p,(.046,.051,.028),FUR_DARK,18,12)
sphere("Tail_white_tip",(-.60,.18,1.07),(.055,.055,.063),FUR_LIGHT,18,12)

# Side-carried lacquer saya and modest sci-fi circuitry sit behind the silhouette.
line("Saya_lacquer",[(-.11,-.304,.91),(-.30,-.32,.72),(-.47,-.33,.43),(-.54,-.32,.27)],.032,LACQUER_DARK)
for p in ((-.125,-.306,.89),(-.49,-.33,.39)):
    sphere("Saya_brass_collar",p,(.035,.035,.026),BRASS,16,12)
line("Sageo_silk_cord",[(-.14,-.31,.91),(-.20,-.38,.72),(-.11,-.35,.57)],.005,INDIGO_LIGHT)
box("Karakuri_wrist_cell",(.062,-.461,1.00),(.052,.040,.092),IRON,.008)
for z in (.971,.990,1.009):
    line(f"Wrist_cell_trace_{z}",[(.092,-.482,z),(.105,-.490,z+.010)],.003,TEAL)

# Export a separate joined static mesh; editable source parts remain untouched.
source_parts=[o for o in parts.objects if o.type=="MESH"]
source_tris=sum(len(p.vertices)-2 for o in source_parts for p in o.data.polygons)
bpy.ops.object.select_all(action="DESELECT")
for o in source_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active=source_parts[0]
bpy.ops.object.duplicate()
duplicates=list(bpy.context.selected_objects)
for o in duplicates:
    for c in tuple(o.users_collection):
        c.objects.unlink(o)
    scene.collection.objects.link(o)
bpy.context.view_layer.objects.active=duplicates[0]
bpy.ops.object.join()
joined=bpy.context.object
joined.name=NAME
scene.cursor.location=(0,0,0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={"MESH"},
                         apply_unit_scale=True,global_scale=1.0,axis_forward="-Y",
                         axis_up="Z",add_leaf_bones=False,bake_anim=False)
corners=[joined.matrix_world @ Vector(v) for v in joined.bound_box]
bounds={"min":[round(min(p[a] for p in corners),4) for a in range(3)],
        "max":[round(max(p[a] for p in corners),4) for a in range(3)]}
bpy.data.objects.remove(joined,do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")

# Review studio is a separate collection and is deliberately not exported.
studio=bpy.data.collections.new("ReviewStudio_NotExported")
scene.collection.children.link(studio)
def studio_link(o):
    for c in tuple(o.users_collection):
        c.objects.unlink(o)
    studio.objects.link(o)
    return o

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.011))
ground=studio_link(bpy.context.object)
ground.name="Studio_floor"
ground.data.materials.append(mat("M_Review_SlateFloor",(.031,.040,.049),rough=.76))
def area(name, at, power, size, color, target=(0,0,1.05)):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power;data.shape="DISK";data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data)
    studio.objects.link(obj);obj.location=at
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    return obj
area("Warm_lantern_key",(2.7,-3.1,3.5),720,3.1,(1,.70,.43))
area("Cool_rim",(-1.8,1.5,3.0),820,2.2,(.42,.68,1))
area("Front_fill",(3.8,2.5,2.3),400,2.7,(.80,.87,1))
world=bpy.data.worlds.new("Blue_hour_review_world")
scene.world=world;world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.09,.13,.20,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.36
scene.render.engine="CYCLES"
scene.cycles.samples=64
scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
camera_data=bpy.data.cameras.new("Review_camera")
camera=bpy.data.objects.new("Review_camera",camera_data)
studio.objects.link(camera);scene.camera=camera
camera_data.type="ORTHO";camera_data.ortho_scale=2.45
camera.location=(3.0,-4.4,2.44)
camera.rotation_euler=(Vector((0,0,1.02))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath=str(PREVIEW)
bpy.ops.render.render(write_still=True)
camera.location=(1.40,-1.82,2.13)
camera.rotation_euler=(Vector((.08,0,1.64))-camera.location).to_track_quat("-Z","Y").to_euler()
camera_data.ortho_scale=.75
scene.render.resolution_x=1250;scene.render.resolution_y=1000
scene.render.filepath=str(DETAIL)
bpy.ops.render.render(write_still=True)
camera_data.ortho_scale=2.45
camera.location=(3.0,-4.4,2.44)
camera.rotation_euler=(Vector((0,0,1.02))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.resolution_x=1200;scene.render.resolution_y=1400
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest={
    "schema_version":1,
    "name":NAME,
    "generator":"scripts/art/create_nyaagyu_hero_character.py",
    "validator":"scripts/art/validate_nyaagyu_hero_character.py",
    "source_blend":BLEND.name,"blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "preview":PREVIEW.name,"preview_sha256":sha(PREVIEW),
    "detail_preview":DETAIL.name,"detail_preview_sha256":sha(DETAIL),
    "unreal_asset":f"/Game/ArtReview/Characters/{NAME}.{NAME}",
    "source_parts":len(source_parts),"source_triangles":source_tris,
    "bounds_m":bounds,"local_forward":"+X face-forward; +Z up",
    "world_origin_m":[0,0,0],"rigged":False,"external_images":[],
    "insignia_source":"../../UI/sora_logo_NOtext2.svg",
    "insignia_sha256":logo_record["source_sha256"],
    "license":"Original project-owned character geometry, shaders and review renders; exact user-supplied SORA insignia paths retain their user-provided provenance and are licensed only for this game. No purchased or external models/textures",
    "limitations":"Stylized concept/blockout, not the photoreal shipping character. Unrigged static mesh. Blender procedural shaders and fur geometry have not been evaluated in UE 5.8.2. No animation, cloth simulation, groom, UE import, or in-game performance claim.",
}
MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_HERO_SOURCE_CREATED",len(source_parts),source_tris,bounds)
