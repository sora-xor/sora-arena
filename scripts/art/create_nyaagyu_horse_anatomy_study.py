"""Isolated, editable anatomy/coat/tack art study for the Nyaagyu horse.

Run after create_nyaagyu_horse_anatomy_textures.py:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_anatomy_study.py

This static review model replaces the earlier horse shell in a NEW source
file only. +X is horse-forward, +Z is up, and all dimensions are metres.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Horses/Nyaagyu"
OUT = BASE / "AnatomyStudy"
OUT.mkdir(parents=True, exist_ok=True)
BASE_MANIFEST = json.loads((BASE / "PBR/variant_manifest.json").read_text())
TEX_MANIFEST = json.loads((OUT / "textures_manifest.json").read_text())
SOURCE = BASE / "PBR" / BASE_MANIFEST["blend"]
BLEND = OUT / "Nyaagyu_Horse_AnatomyStudy.blend"
FBX = OUT / "SM_Nyaagyu_Horse_AnatomyStudy.fbx"
MANIFEST = OUT / "manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(SOURCE) == BASE_MANIFEST["blend_sha256"]
for entries in TEX_MANIFEST["sets"].values():
    for entry in entries:
        assert sha(OUT / entry["file"]) == entry["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
original = bpy.data.collections["NyaagyuHorse_Editable"]
exact_mon = sorted((o for o in original.objects if o.name.startswith("SORA_kamon_exact_svg_")),
                   key=lambda o: o.name)
assert len(exact_mon) == 8
for obj in exact_mon:
    assert obj["source_svg_sha256"] == BASE_MANIFEST["sora_logo_sha256"]

# Remove only the previous equine sculpt and hair in this in-memory copy.
# Measured tack and exact SVG relief remain present and unchanged in the base.
for obj in list(original.objects):
    if obj.type == "MESH" and obj.name.startswith("Horse_"):
        bpy.data.objects.remove(obj, do_unlink=True)

anatomy = bpy.data.collections.new("AnatomyStudy_Editable")
scene.collection.children.link(anatomy)


def relocate(obj, name: str, material=None):
    obj.name = name
    for coll in tuple(obj.users_collection):
        coll.objects.unlink(obj)
    anatomy.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    obj["source_art_pass"] = "Nyaagyu horse isolated anatomy study v1"
    return obj


def smooth(obj):
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def mesh(name: str, vertices, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    anatomy.objects.link(obj)
    data.materials.append(material)
    obj["source_art_pass"] = "Nyaagyu horse isolated anatomy study v1"
    return smooth(obj)


def ellipsoid(name, center, size, material, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = relocate(bpy.context.object, name, material)
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return smooth(obj)


def axial_loft(name, rings, material, facets=48):
    """x, z, vertical depth, lateral half-width; continuous trunk contour."""
    vertices = []
    for idx, (x, z, depth, width) in enumerate(rings):
        prev = Vector(rings[max(0, idx - 1)][:2])
        nxt = Vector(rings[min(len(rings) - 1, idx + 1)][:2])
        tangent = (nxt - prev).normalized()
        normal = Vector((-tangent.y, tangent.x))
        for sector in range(facets):
            angle = math.tau * sector / facets
            c, s = math.cos(angle), math.sin(angle)
            vertices.append((x + normal.x * depth * c, width * s,
                             z + normal.y * depth * c))
    faces = [tuple(reversed(range(facets)))]
    for ring in range(len(rings) - 1):
        for j in range(facets):
            k = (j + 1) % facets
            faces.append((ring*facets+j, ring*facets+k,
                          (ring+1)*facets+k, (ring+1)*facets+j))
    faces.append(tuple((len(rings)-1)*facets+j for j in range(facets)))
    return mesh(name, vertices, faces, material)


def limb_loft(name, y, rings, material, facets=32):
    """x/z center and front-back/lateral radii at each joint landmark."""
    vertices = []
    for x, z, fore_aft, lateral in rings:
        for j in range(facets):
            angle = math.tau*j/facets
            vertices.append((x+fore_aft*math.cos(angle),
                             y+lateral*math.sin(angle), z))
    faces=[tuple(reversed(range(facets)))]
    for ring in range(len(rings)-1):
        for j in range(facets):
            k=(j+1)%facets
            faces.append((ring*facets+j,ring*facets+k,
                          (ring+1)*facets+k,(ring+1)*facets+j))
    faces.append(tuple((len(rings)-1)*facets+j for j in range(facets)))
    return mesh(name,vertices,faces,material)


def tube(name, points, radius, material, resolution=2):
    data=bpy.data.curves.new(name,"CURVE")
    data.dimensions="3D"
    data.resolution_u=12
    data.bevel_depth=radius
    data.bevel_resolution=resolution
    spline=data.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for b, point in zip(spline.bezier_points,points):
        b.co=point
        b.handle_left_type=b.handle_right_type="AUTO"
    obj=bpy.data.objects.new(name,data)
    anatomy.objects.link(obj)
    data.materials.append(material)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.convert(target="MESH")
    return relocate(bpy.context.object,name)


COAT=bpy.data.materials["M_Horse_SealBrownCoat"]
MANE=bpy.data.materials["M_Horse_BlackMane"]
DARK=bpy.data.materials["M_Horse_DarkPoints"]
HOOF=bpy.data.materials["M_Horse_HoofHorn"]
MUZZLE=bpy.data.materials["M_Horse_Muzzle"]
EYE=bpy.data.materials["M_Horse_Eye"]
EYE_RIM=bpy.data.materials["M_Horse_EyeRim"]
IRON=bpy.data.materials["M_Tack_BlackenedIron"]
LEATHER=bpy.data.materials["M_Tack_DarkLeather"]
WOOD=bpy.data.materials["M_Tack_StainedWood"]
LACQUER=bpy.data.materials["M_Tack_OxbloodUrushi"]
BLACK_LACQUER=bpy.data.materials["M_Tack_BlackUrushi"]
GOLD=bpy.data.materials["M_Tack_AgedGold"]
black_bsdf=BLACK_LACQUER.node_tree.nodes.get("Principled BSDF")
black_bsdf.inputs["Base Color"].default_value=(.008,.006,.005,1)
black_bsdf.inputs["Roughness"].default_value=.57

# The previous single rectangular tree and full-height upright plates read as
# furniture. In this variant the four-piece principle is visible: two shaped
# longitudinal members joined to two arched crosspieces. The Met's 1658 kura
# is 36.8 x 38.1 x 27.3 cm overall; this remains a proportion study because
# cat-rider fit and the full trappings have not been measured together.
for name in ("Kura_wooden_tree","Kura_lacquered_seat",
             "Kura_maewa_high_lacquer_panel","Kura_shizuwa_high_lacquer_panel",
             "Kura_maewa_metal_edge","Kura_shizuwa_metal_edge"):
    obj=original.objects.get(name)
    assert obj is not None,name
    bpy.data.objects.remove(obj,do_unlink=True)


def arched_crosspiece(label,x):
    y_values=(-.188,-.168,-.115,-.060,0,.060,.115,.168,.188)
    top=(1.434,1.499,1.586,1.632,1.644,1.632,1.586,1.499,1.434)
    bottom=(1.425,1.457,1.522,1.563,1.576,1.563,1.522,1.457,1.425)
    n=len(y_values)
    verts=[]
    for depth in (-.012,.012):
        for ys,zs in ((y_values,top),(y_values,bottom)):
            verts.extend((x+depth,y,z) for y,z in zip(ys,zs))
    faces=[]
    for i in range(n-1):
        faces.append((i,i+1,n+i+1,n+i))
        faces.append((2*n+i,3*n+i,3*n+i+1,2*n+i+1))
        for band in (0,n):
            faces.append((band+i,2*n+band+i,2*n+band+i+1,band+i+1))
    faces.extend(((0,n,3*n,2*n),(n-1,2*n-1,4*n-1,3*n-1)))
    arch=mesh(f"HorseStudy_kura_{label}_arched_crosspiece",verts,faces,BLACK_LACQUER)
    bevel=arch.modifiers.new("Soft_lacquer_edge","BEVEL")
    bevel.width=.0035
    bevel.segments=2
    bpy.context.view_layer.objects.active=arch
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    smooth(arch)
    tube(f"HorseStudy_kura_{label}_gilt_edge",
         [(x-.014,y,z+.002) for y,z in zip(y_values,top)],.0018,GOLD)
    return arch


arched_crosspiece("maewa",.158)
arched_crosspiece("shizuwa",-.214)
for side in (-1,1):
    y=side*.173
    tube(f"HorseStudy_kura_side_tree_{side}",[
         (-.214,y,1.436),(-.145,y,1.383),(-.025,y,1.375),
         (.085,y,1.385),(.158,y,1.436)],.014,WOOD)
    tube(f"HorseStudy_kura_leather_seat_edge_{side}",[
         (-.193,side*.155,1.404),(-.070,side*.155,1.390),
         (.075,side*.155,1.391),(.138,side*.155,1.413)],.003,LEATHER)

seat_verts=[]
for x in (-.195,-.120,-.045,.030,.100,.148):
    for y in (-.148,-.074,0,.074,.148):
        edge=(abs(y)/.148)**2
        z=1.389+.015*edge+.004*((x+.02)/.17)**2
        seat_verts.append((x,y,z))
seat_faces=[]
for i in range(5):
    for j in range(4):
        a=i*5+j
        seat_faces.append((a,a+5,a+6,a+1))
seat=mesh("HorseStudy_kura_shaped_seat",seat_verts,seat_faces,LEATHER)
solid=seat.modifiers.new("Tensioned_seat_thickness","SOLIDIFY")
solid.thickness=.010
bpy.context.view_layer.objects.active=seat
bpy.ops.object.modifier_apply(modifier=solid.name)

# A compact horse, approximately 1.4 m at the withers. Shoulder volume,
# abdominal lift, flank tuck and rounded croup are distinct on the sculpt.
# Positions are an authored proportions study, not a breed reconstruction.
core_parts=[]
core_parts.append(axial_loft("HorseStudy_trunk",[
    (-.91,1.092,.035,.060),(-.84,1.075,.160,.190),
    (-.72,1.035,.264,.286),(-.56,1.016,.292,.310),
    (-.37,1.020,.272,.292),(-.17,1.032,.257,.273),
    (.035,1.047,.274,.290),(.230,1.072,.300,.314),
    (.398,1.098,.286,.293),(.525,1.125,.219,.227),
    (.603,1.146,.080,.105)],COAT,64))
core_parts.append(axial_loft("HorseStudy_neck",[
    (.360,1.191,.194,.206),(.420,1.257,.191,.196),
    (.490,1.346,.176,.177),(.560,1.434,.150,.158),
    (.640,1.522,.122,.137),(.725,1.608,.100,.119),
    (.795,1.651,.058,.091)],COAT,48))
core_parts.append(axial_loft("HorseStudy_head",[
    (.772,1.648,.065,.095),(.809,1.625,.087,.111),
    (.860,1.583,.095,.116),(.912,1.530,.098,.117),
    (.974,1.465,.080,.105),(1.038,1.404,.065,.088),
    (1.104,1.350,.056,.085),(1.152,1.329,.027,.066)],COAT,48))
core_parts.append(ellipsoid("HorseStudy_masseter",(.823,0,1.492),(.105,.131,.115),COAT))
core_parts.append(ellipsoid("HorseStudy_muzzle_bridge",(1.095,0,1.379),(.084,.105,.062),COAT))
for side in (-1,1):
    y=side*.215
    core_parts.append(ellipsoid(f"HorseStudy_scapular_mass_{side}",
                                (.380,side*.183,1.060),(.202,.116,.235),COAT))
    core_parts.append(ellipsoid(f"HorseStudy_gluteal_mass_{side}",
                                (-.685,side*.170,1.029),(.177,.143,.238),COAT))
    core_parts.append(limb_loft(f"HorseStudy_forelimb_{side}",y,[
        (.390,1.090,.134,.119),(.422,.941,.122,.106),
        (.455,.804,.094,.084),(.482,.660,.071,.065),
        (.481,.578,.074,.065),(.486,.509,.058,.054),
        (.494,.398,.047,.043),(.504,.286,.039,.037),
        (.523,.194,.048,.047),(.543,.137,.054,.049),
        (.560,.095,.053,.047)],COAT))
    core_parts.append(limb_loft(f"HorseStudy_hindlimb_{side}",y,[
        (-.635,1.069,.155,.139),(-.692,.937,.149,.130),
        (-.743,.804,.117,.099),(-.791,.678,.085,.072),
        (-.837,.575,.071,.062),(-.840,.525,.065,.060),
        (-.807,.441,.049,.048),(-.776,.330,.039,.037),
        (-.751,.216,.043,.042),(-.735,.155,.052,.048),
        (-.713,.101,.053,.047)],COAT))
    # Narrow muscle masses are welded to the body rather than represented as
    # armour-like separate ovals. They give the stifle and brachial region form.
    core_parts.append(ellipsoid(f"HorseStudy_brachial_{side}",
                                (.432,side*.212,.865),(.103,.073,.185),COAT,24,16))
    core_parts.append(ellipsoid(f"HorseStudy_hamstring_{side}",
                                (-.731,side*.210,.837),(.097,.080,.183),COAT,24,16))

bpy.ops.object.select_all(action="DESELECT")
for obj in core_parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active=core_parts[0]
bpy.ops.object.join()
core=bpy.context.object
core.name="HorseStudy_anatomical_core"
core.data.remesh_voxel_size=.0095
bpy.ops.object.voxel_remesh()
modifier=core.modifiers.new("Soften_skin_transitions","SMOOTH")
modifier.factor=.75
modifier.iterations=4
bpy.context.view_layer.objects.active=core
bpy.ops.object.modifier_apply(modifier=modifier.name)
smooth(core)
assert len(core.data.vertices)>20000

# Continuous bay-point transition on the lower legs; avoids the old straight
# color cutoff through the shoulder/haunch. UV0 remains explicit on export.
color=core.data.vertex_colors.new(name="CoatVariation")
for face in core.data.polygons:
    for loop_index in face.loop_indices:
        point=core.data.vertices[core.data.loops[loop_index].vertex_index].co
        z=point.z
        leg_factor=max(0,min(1,(.78-z)/.43))
        muzzle_factor=max(0,min(1,(point.x-1.04)/.14))*max(0,min(1,(1.47-z)/.13))
        flank= .035*math.sin(point.x*13.1+point.z*7.3)*math.sin(point.y*19.7)
        value=max(.55,min(1.04,1-.39*leg_factor-.24*muzzle_factor+flank))
        color.data[loop_index].color=(value,value*.985,value*.97,1)


def hoof(name, center_x, side):
    y=side*.215
    # Crown/pastern narrows to a distinct coronet; the shell slopes toward
    # the toe and flares at the ground plane, unlike a truncated cone.
    rings=((.122,center_x-.017,.048,.046),
           (.096,center_x-.012,.055,.049),
           (.047,center_x+.008,.082,.060),
           (.005,center_x+.034,.106,.075))
    facets=32
    vertices=[]
    for z,cx,rx,ry in rings:
        for j in range(facets):
            a=math.tau*j/facets
            vertices.append((cx+rx*math.cos(a),y+ry*math.sin(a),z))
    faces=[tuple(reversed(range(facets)))]
    for ring in range(len(rings)-1):
        for j in range(facets):
            k=(j+1)%facets
            faces.append((ring*facets+j,ring*facets+k,
                          (ring+1)*facets+k,(ring+1)*facets+j))
    faces.append(tuple((len(rings)-1)*facets+j for j in range(facets)))
    obj=mesh(name,vertices,faces,HOOF)
    obj["hoof_sole_z_m"]=.005
    # The coronary band is skin over hoof horn, not a metal horseshoe.
    for j in range(2):
        tube(f"{name}_coronet_{j}",[
            (center_x-.061,y+side*(j-.5)*.044,.122),
            (center_x-.009,y+side*(j-.5)*.053,.117),
            (center_x+.052,y+side*(j-.5)*.046,.110)],.0035,DARK)
    return obj


for side in (-1,1):
    hoof(f"HorseStudy_fore_hoof_{side}",.554,side)
    hoof(f"HorseStudy_hind_hoof_{side}",-.719,side)

# Eye set into an orbital fold rather than a separate toy-like glossy bead.
for side in (-1,1):
    ellipsoid(f"HorseStudy_orbital_fold_{side}",(.866,side*.117,1.585),
              (.049,.013,.033),COAT,32,18)
    ellipsoid(f"HorseStudy_eye_{side}",(.871,side*.128,1.587),
              (.028,.008,.017),EYE,32,18)
    tube(f"HorseStudy_upper_lid_{side}",[(.839,side*.135,1.588),
         (.857,side*.139,1.606),(.881,side*.140,1.605),
         (.902,side*.133,1.584)],.0035,EYE_RIM)
    ellipsoid(f"HorseStudy_nostril_shadow_{side}",
              (1.143,side*.091,1.360),(.027,.005,.018),DARK,32,16)
    tube(f"HorseStudy_nostril_lip_{side}",[
        (1.118,side*.096,1.350),(1.133,side*.099,1.378),
        (1.157,side*.089,1.374)],.0037,MUZZLE)
    tube(f"HorseStudy_muzzle_line_{side}",[
        (1.083,side*.080,1.310),(1.125,side*.079,1.305),
        (1.159,side*.062,1.315)],.0018,DARK)
    # A folded tapered pinna has thickness, unlike the old pointed cone.
    ys=side
    ear_verts=[(.744,ys*.071,1.663),(.788,ys*.091,1.663),
                (.778,ys*.112,1.758),(.766,ys*.106,1.827),
                (.745,ys*.077,1.806),(.741,ys*.080,1.733),
                (.759,ys*.111,1.692),(.767,ys*.120,1.765)]
    ear_faces=[(0,1,2,3,4,5),(1,6,7,2),(0,5,4,3,7,6)]
    ear=mesh(f"HorseStudy_ear_{side}",ear_verts,ear_faces,COAT)
    ear.data.materials.append(DARK)
    ear.data.polygons[1].material_index=1
    solid=ear.modifiers.new("Pinna_cartilage_thickness","SOLIDIFY")
    solid.thickness=.005
    bpy.context.view_layer.objects.active=ear
    bpy.ops.object.modifier_apply(modifier=solid.name)


def hair_ribbons(name, seeds, material):
    """One mesh of thin tapered 3D strands; far from a validated groom."""
    verts=[];faces=[]
    for p0,p1,p2,p3,width in seeds:
        base=len(verts)
        for i,p in enumerate((p0,p1,p2,p3)):
            radius=width*(1-.22*i)
            if i==3:radius*=.18
            for j in range(4):
                a=math.tau*j/4
                verts.append((p[0]+radius*math.cos(a),
                              p[1]+radius*math.sin(a),p[2]))
        for i in range(3):
            for j in range(4):
                k=(j+1)%4
                faces.append((base+i*4+j,base+i*4+k,
                              base+(i+1)*4+k,base+(i+1)*4+j))
    return mesh(name,verts,faces,material)


rng=random.Random(0xC0A7026)
mane=[]
for i in range(650):
    t=rng.random()
    x=.365+.40*t
    z=1.335+.347*t-.021*math.sin(math.pi*t)
    side=1 if rng.random()>.5 else -1
    y=side*rng.uniform(.006,.060)
    length=rng.uniform(.050,.160)
    width=rng.uniform(.00065,.00145)
    mane.append(((x,y,z),(x-.015,side*(abs(y)+.018),z+.012),
                 (x-.041,side*(abs(y)+.052),z-length*.40),
                 (x-.079,side*(abs(y)+.070),z-length),width))
hair_ribbons("HorseStudy_mane_fine_fibres",mane,MANE)
# A sparse outer tier gives the mane a readable broken silhouette at normal
# review distance; the fine fibres above still carry the close-up breakup.
outer_mane=[]
for i in range(138):
    t=(i+.35*rng.random())/138
    x=.386+.363*t
    z=1.358+.320*t
    side=1 if i%2 else -1
    y=side*rng.uniform(.030,.065)
    length=rng.uniform(.085,.175)
    outer_mane.append(((x,y,z),(x-.016,side*(abs(y)+.028),z+.009),
                       (x-.050,side*(abs(y)+.075),z-length*.47),
                       (x-.081,side*(abs(y)+.090),z-length),
                       rng.uniform(.0020,.0033)))
hair_ribbons("HorseStudy_mane_silhouette_fibres",outer_mane,MANE)
tail=[]
for i in range(440):
    a=math.tau*i/440
    x=-.890+.026*math.cos(a)
    y=.035*math.sin(a)
    width=rng.uniform(.0008,.0017)
    tail.append(((x,y,1.025),(-.952,y*1.2,.850),
                 (-1.000+rng.uniform(-.012,.012),y*1.7,.58),
                 (-1.045+rng.uniform(-.028,.028),y*2.3,.30+rng.uniform(-.05,.05)),
                 width))
hair_ribbons("HorseStudy_tail_fine_fibres",tail,MANE)

# Exposed lacing identifies the joints; rider reach and load paths remain
# unvalidated.
for side in (-1,1):
    for i,x in enumerate((-.148,-.022,.106)):
        tube(f"HorseStudy_kura_hemp_lacing_{side}_{i}",[
             (x,side*.168,1.383),(x+.018,side*.199,1.394),
             (x+.033,side*.211,1.378)],.0024,LEATHER)

# First-party texture hookups. The vertex-color layer also survives FBX and
# must multiply, in linear space, against the supplied coat albedo in Unreal.
texture_paths={name:{entry["channel"]:OUT/entry["file"] for entry in entries}
               for name,entries in TEX_MANIFEST["sets"].items()}


def apply_maps(material, key, vertex_color=False):
    tree=material.node_tree
    nodes,links=tree.nodes,tree.links
    bsdf=nodes.get("Principled BSDF")
    assert bsdf
    for node in list(nodes):
        if node not in (bsdf,) and node.type!="OUTPUT_MATERIAL":
            nodes.remove(node)
    entries=texture_paths[key]
    albedo=nodes.new("ShaderNodeTexImage")
    albedo.name="AnatomyStudy_Albedo"
    albedo.image=bpy.data.images.load(str(entries["Albedo"]),check_existing=True)
    base_output=albedo.outputs["Color"]
    if vertex_color:
        vc=nodes.new("ShaderNodeVertexColor")
        vc.layer_name="CoatVariation"
        multiply=nodes.new("ShaderNodeMixRGB")
        multiply.blend_type="MULTIPLY"
        multiply.inputs[0].default_value=1
        links.new(albedo.outputs["Color"],multiply.inputs[1])
        links.new(vc.outputs["Color"],multiply.inputs[2])
        base_output=multiply.outputs["Color"]
    links.new(base_output,bsdf.inputs["Base Color"])
    packed=nodes.new("ShaderNodeTexImage")
    packed.name="AnatomyStudy_ORM"
    packed.image=bpy.data.images.load(str(entries["ORM"]),check_existing=True)
    packed.image.colorspace_settings.name="Non-Color"
    channels=nodes.new("ShaderNodeSeparateColor")
    channels.mode="RGB"
    links.new(packed.outputs["Color"],channels.inputs["Color"])
    links.new(channels.outputs["Green"],bsdf.inputs["Roughness"])
    links.new(channels.outputs["Blue"],bsdf.inputs["Metallic"])
    ntex=nodes.new("ShaderNodeTexImage")
    ntex.name="AnatomyStudy_NormalDX"
    ntex.image=bpy.data.images.load(str(entries["NormalDX"]),check_existing=True)
    ntex.image.colorspace_settings.name="Non-Color"
    rgb=nodes.new("ShaderNodeSeparateColor")
    rgb.mode="RGB"
    links.new(ntex.outputs["Color"],rgb.inputs["Color"])
    flip=nodes.new("ShaderNodeMath")
    flip.operation="SUBTRACT"
    flip.inputs[0].default_value=1
    links.new(rgb.outputs["Green"],flip.inputs[1])
    merged=nodes.new("ShaderNodeCombineColor")
    merged.mode="RGB"
    links.new(rgb.outputs["Red"],merged.inputs["Red"])
    links.new(flip.outputs[0],merged.inputs["Green"])
    links.new(rgb.outputs["Blue"],merged.inputs["Blue"])
    normal=nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value=.45 if key=="coat_study" else .30
    links.new(merged.outputs["Color"],normal.inputs["Color"])
    links.new(normal.outputs["Normal"],bsdf.inputs["Normal"])


apply_maps(COAT,"coat_study",True)
apply_maps(HOOF,"hoof_horn_study")
apply_maps(LACQUER,"oxblood_urushi_study")

# Explicit UV0 on every editable mesh, including the retained tack. World
# planar alignment gives consistent texel scale; no runtime triplanar shader.
editable=sorted((o for o in (*original.objects,*anatomy.objects) if o.type=="MESH"),
                key=lambda o:o.name)
for obj in editable:
    old_uv=obj.data.uv_layers.get("Nyaagyu_PBR_UV")
    if old_uv is not None:
        old_uv.name="UV0"
    uv=obj.data.uv_layers.get("UV0") or obj.data.uv_layers.new(name="UV0",do_init=False)
    for face in obj.data.polygons:
        mat=obj.data.materials[face.material_index].name
        scale=10.5 if mat.startswith("M_Horse_") else 8.0
        normal=obj.matrix_world.to_3x3()@face.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for loop_index in face.loop_indices:
            point=obj.matrix_world@obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            if obj==core or axis==1: u,v=point.x,point.z
            elif axis==0: u,v=point.y,point.z
            else: u,v=point.x,point.y
            uv.data[loop_index].uv=(u*scale,v*scale)
    obj.data.uv_layers.active=uv
    for old in tuple(obj.data.uv_layers):
        if old!=uv:
            obj.data.uv_layers.remove(old)

# Export static source review. The Blender file retains independent anatomy,
# tack, and all six original attachment anchors for future rig work.
bpy.ops.object.select_all(action="DESELECT")
for obj in editable:obj.select_set(True)
bpy.context.view_layer.objects.active=editable[0]
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active=bpy.context.selected_objects[0]
bpy.ops.object.join()
export=bpy.context.object
export.name="SM_Nyaagyu_Horse_AnatomyStudy"
for coll in tuple(export.users_collection):coll.objects.unlink(export)
export_collection=bpy.data.collections.new("AnatomyStudy_Export_Only")
scene.collection.children.link(export_collection)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,
                         object_types={"MESH"},add_leaf_bones=False,
                         apply_unit_scale=True,axis_forward="-Y",axis_up="Z",
                         path_mode="STRIP")
export.hide_render=True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")

camera=scene.camera
assert camera
scene.render.engine="CYCLES"
scene.cycles.samples=24
scene.render.resolution_x=1400
scene.render.resolution_y=960
scene.render.resolution_percentage=100


def review(name, location, target, lens):
    camera.data.type="PERSP"
    camera.location=location
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.lens=lens
    scene.render.filepath=str(OUT/name)
    bpy.ops.render.render(write_still=True)


review("Nyaagyu_Horse_Anatomy_ThreeQuarter.png",(2.9,-3.7,2.06),(.035,0,1.02),56)
review("Nyaagyu_Horse_Anatomy_Profile.png",(.0,-4.1,1.55),(.035,0,1.01),53)
review("Nyaagyu_Horse_Tack_Detail.png",(.02,-1.55,1.70),(-.025,-.12,1.43),82)

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

verts_world=[o.matrix_world@v.co for o in editable for v in o.data.vertices]
triangles=sum(len(face.vertices)-2 for o in editable for face in o.data.polygons)
dimensions={"min":[round(min(p[i] for p in verts_world),4) for i in range(3)],
            "max":[round(max(p[i] for p in verts_world),4) for i in range(3)]}
record={
    "schema_version":1,
    "generator":"scripts/art/create_nyaagyu_horse_anatomy_study.py",
    "validator":"scripts/art/validate_nyaagyu_horse_anatomy_study.py",
    "baseline_blend":"Content/SourceArt/Horses/Nyaagyu/PBR/"+SOURCE.name,
    "baseline_blend_sha256":sha(SOURCE),
    "texture_manifest_sha256":sha(OUT/"textures_manifest.json"),
    "source_blend":BLEND.name,"source_blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "preview_files":[{"file":p.name,"sha256":sha(p)} for p in (
        OUT/"Nyaagyu_Horse_Anatomy_ThreeQuarter.png",
        OUT/"Nyaagyu_Horse_Anatomy_Profile.png",
        OUT/"Nyaagyu_Horse_Tack_Detail.png")],
    "editable_mesh_parts":len(editable),"triangles":triangles,
    "anatomical_core_vertices":len(core.data.vertices),
    "source_dimensions_m":dimensions,
    "withers_visual_estimate_m":round(max(v.co.z for v in core.data.vertices
                                           if .28<=v.co.x<=.32 and abs(v.co.y)<.04),3),
    "hoof_ground_z_m":.005,
    "sora_logo_sha256":BASE_MANIFEST["sora_logo_sha256"],
    "exact_sora_kamon_objects":[o.name for o in exact_mon],
    "texture_slots":{"M_Horse_SealBrownCoat":"coat_study",
                     "M_Horse_HoofHorn":"hoof_horn_study",
                     "M_Tack_OxbloodUrushi":"oxblood_urushi_study"},
    "base_tack_preserved_except_kura":True,
    "kura_crosspiece_reference":"https://www.metmuseum.org/art/collection/search/26572",
    "source_only":True,
    "license":"Original project-owned modeling and procedural texture variation over project-owned source; no third-party source mesh or museum image used.",
    "limitations":"Static anatomical and PBR study, not a production horse. No scanned hide, calibrated groom, facial rig, correct tack load path, rider-fit test, gait biomechanics signoff, UE import or in-game performance qualification.",
}
MANIFEST.write_text(json.dumps(record,indent=2)+"\n")
print("NYAAGYU_HORSE_ANATOMY_STUDY_COMPLETE",len(editable),triangles,len(core.data.vertices))
