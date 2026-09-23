"""Author an original compact Japanese horse and Edo-inspired tack study.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_horse_tack.py

Source geometry is editable and independently exported as a static FBX. +X is
the horse's forward direction, +Z is up, meters are used throughout. This is
not a rigged, animated, photoreal, or historical-reconstruction claim.
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
OUT = ROOT / "Content/SourceArt/Horses/Nyaagyu"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_HorseAndTack"
BLEND = OUT / "Nyaagyu_HorseAndTack.blend"
FBX = OUT / f"{NAME}.fbx"
PREVIEW = OUT / "Nyaagyu_HorseAndTack_Blender.png"
MANIFEST = OUT / "manifest.json"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
LOGO_RECORD = json.loads((LOGO.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == LOGO_RECORD["source_sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
parts = bpy.data.collections.new("NyaagyuHorse_Editable")
scene.collection.children.link(parts)


def material(name, color, roughness, metallic=0, noise=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 3
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .11
        bump.inputs["Distance"].default_value = .00025
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


COAT = material("M_Horse_SealBrownCoat", (.16, .082, .044), .86, noise=185)
COAT_DARK = material("M_Horse_DarkPoints", (.062, .037, .025), .89, noise=210)
COAT_LIGHT = material("M_Horse_Muzzle", (.085, .050, .035), .86, noise=200)
MANE = material("M_Horse_BlackMane", (.027, .025, .022), .90, noise=160)
HOOF = material("M_Horse_HoofHorn", (.028, .022, .018), .82, noise=140)
EYE = material("M_Horse_Eye", (.012, .010, .008), .13)
EYE_RIM = material("M_Horse_EyeRim", (.032, .017, .011), .77)
LACQUER = material("M_Tack_BlackUrushi", (.021, .017, .015), .38, noise=75)
RED_LACQUER = material("M_Tack_OxbloodUrushi", (.105, .018, .016), .35, noise=71)
WOOD = material("M_Tack_StainedWood", (.17, .095, .044), .63, noise=190)
LEATHER = material("M_Tack_DarkLeather", (.095, .046, .026), .69, noise=160)
SILK = material("M_Tack_IndigoSilk", (.026, .044, .082), .79, noise=215)
SILK_TRIM = material("M_Tack_CrimsonSilk", (.35, .024, .031), .71, noise=210)
IRON = material("M_Tack_BlackenedIron", (.067, .071, .073), .39, .87, noise=100)
SILVER = material("M_Tack_SilverInlay", (.56, .57, .54), .28, .89, noise=90)
GOLD = material("M_Tack_AgedGold", (.45, .27, .082), .35, .85, noise=92)
SORA_RED = material("M_Tack_SORA_Red", (.76, .026, .043), .28)


def move(obj, name, mat=None):
    obj.name = name
    for collection in tuple(obj.users_collection):
        collection.objects.unlink(obj)
    parts.objects.link(obj)
    if mat is not None:
        obj.data.materials.append(mat)
    obj["provenance"] = "Original SORA Arena project geometry"
    return obj


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def sphere(name, center, radii, mat, segments=28, rings=18):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = move(bpy.context.object, name, mat)
    obj.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return smooth(obj)


def mesh(name, vertices, faces, mat, thickness=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    parts.objects.link(obj)
    data.materials.append(mat)
    obj["provenance"] = "Original SORA Arena project geometry"
    if thickness:
        modifier = obj.modifiers.new("Physical_thickness", "SOLIDIFY")
        modifier.thickness = thickness
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def tube(name, points, radius, mat, resolution=3):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 16
    data.bevel_depth = radius
    data.bevel_resolution = resolution
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, xyz in zip(spline.bezier_points, points):
        point.co = xyz
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    parts.objects.link(obj)
    data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return smooth(move(bpy.context.object, name))


def tapered_hair(name, points, radius, mat):
    """Lightweight source strands; static review fibers, not a groom or sim."""
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 7
    data.bevel_depth = radius
    data.bevel_resolution = 1
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for index, (point, xyz) in enumerate(zip(spline.bezier_points, points)):
        point.co = xyz
        point.radius = max(.05, 1-index/(len(points)-1))
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    parts.objects.link(obj)
    data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return smooth(move(bpy.context.object, name))


def cone_between(name, a, b, radius_a, radius_b, mat, vertices=20):
    a, b = Vector(a), Vector(b)
    vector = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius_a, radius2=radius_b,
                                    depth=vector.length, location=(a + b) / 2)
    obj = move(bpy.context.object, name, mat)
    obj.rotation_euler = vector.to_track_quat("Z", "Y").to_euler()
    return smooth(obj)


def box(name, center, size, mat, edge=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = move(bpy.context.object, name, mat)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if edge:
        modifier = obj.modifiers.new("Softened_edge", "BEVEL")
        modifier.width = edge
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return smooth(obj)


def xz_loft(name, rings, mat, facets=28):
    """Closed, softly tapered mass following an anatomical X/Z center line.

    Rings contain (x, z, vertical-half-depth, lateral-half-width). A local
    normal to the center line shapes the dorsal and ventral contours rather
    than stacking spheres, which previously made the horse's neck bulbous.
    """
    vertices=[]
    for index,(x,z,depth,width) in enumerate(rings):
        prior=Vector(rings[max(index-1,0)][:2])
        following=Vector(rings[min(index+1,len(rings)-1)][:2])
        tangent=(following-prior).normalized()
        perpendicular=Vector((-tangent.y,tangent.x))
        for step in range(facets):
            angle=math.tau*step/facets
            c=math.cos(angle)
            vertices.append((x+perpendicular.x*depth*c,
                             width*math.sin(angle),
                             z+perpendicular.y*depth*c))
    faces=[]
    faces.append(tuple(reversed(range(facets))))
    for ring in range(len(rings)-1):
        for step in range(facets):
            next_step=(step+1)%facets
            faces.append((ring*facets+step,ring*facets+next_step,
                          (ring+1)*facets+next_step,(ring+1)*facets+step))
    faces.append(tuple((len(rings)-1)*facets+step for step in range(facets)))
    return smooth(mesh(name,vertices,faces,mat))


# Approximate 1.32 m at the withers: a compact Japanese-type mount, not a
# breed-level reconstruction. One continuous torso replaces the overlapping
# barrel/chest/haunch spheres and gives the shoulder and rump a shared surface.
xz_loft("Horse_torso_continuous",
        [(-.84,1.045,.052,.09),(-.75,1.04,.235,.255),
         (-.59,1.035,.300,.305),(-.38,1.03,.296,.292),
         (-.14,1.025,.288,.280),(.10,1.035,.306,.296),
         (.32,1.055,.321,.310),(.48,1.085,.280,.258),
         (.62,1.115,.120,.145)],COAT,facets=48)
xz_loft("Horse_neck",[(.33,1.16,.225,.223),(.405,1.25,.222,.215),
                      (.505,1.375,.185,.184),(.625,1.505,.139,.151),
                      (.735,1.59,.103,.132),(.795,1.625,.086,.121)],COAT)
sphere("Horse_jowl", (.812, 0, 1.492), (.112, .143, .108), COAT, 32, 20)
xz_loft("Horse_long_head",[(.755,1.635,.065,.102),(.814,1.615,.097,.123),
                           (.864,1.574,.110,.137),(.925,1.511,.108,.135),
                           (.992,1.452,.092,.123),(1.052,1.401,.074,.108),
                           (1.105,1.357,.068,.108)],COAT)
sphere("Horse_muzzle", (1.112, 0, 1.341), (.090, .111, .059), COAT_LIGHT, 32, 20)
sphere("Horse_lower_lip", (1.101, 0, 1.302), (.076, .103, .026), COAT_DARK)
for side in (-1, 1):
    y = side * .103
    sphere(f"Horse_nostril_rim_{side}", (1.145, y, 1.374), (.023, .012, .021), COAT_DARK)
    sphere(f"Horse_nostril_{side}", (1.149, side * .110, 1.376), (.012, .007, .013), MANE)
    sphere(f"Horse_eye_rim_{side}", (.854, side * .124, 1.588), (.040, .012, .025), EYE_RIM)
    sphere(f"Horse_eye_{side}", (.863, side * .134, 1.591), (.028, .009, .017), EYE)
    sphere(f"Horse_eye_reflection_{side}", (.871, side * .141, 1.598), (.005, .002, .004), SILVER, 12, 8)
    cone_between(f"Horse_ear_{side}", (.777, side * .092, 1.674),
                 (.762, side * .112, 1.820), .047, .006, COAT, 18)
    cone_between(f"Horse_inner_ear_{side}", (.791, side * .129, 1.695),
                 (.766, side * .132, 1.797), .025, .005, COAT_DARK, 16)


def leg(name, side, rings, dark_from):
    """One continuous tapered limb per leg, with anatomical bend landmarks."""
    y=side*.215
    facets=20
    vertices=[]
    for x,z,front_back,lateral in rings:
        for step in range(facets):
            angle=math.tau*step/facets
            vertices.append((x+front_back*math.cos(angle),
                             y+lateral*math.sin(angle),z))
    faces=[tuple(reversed(range(facets)))]
    for ring in range(len(rings)-1):
        for step in range(facets):
            following=(step+1)%facets
            faces.append((ring*facets+step,ring*facets+following,
                          (ring+1)*facets+following,(ring+1)*facets+step))
    faces.append(tuple((len(rings)-1)*facets+step for step in range(facets)))
    limb=smooth(mesh(f"Horse_{name}_{side}_continuous_limb",vertices,faces,COAT))
    limb.data.materials.append(COAT_DARK)
    for ring in range(len(rings)-1):
        if ring>=dark_from:
            for polygon in limb.data.polygons[1+ring*facets:1+(ring+1)*facets]:
                polygon.material_index=1
    limb.data.polygons[-1].material_index=1

    # A 20-sided shell follows the fetlock and gently flares into a rounded
    # toe. It replaces the earlier six-faced, box-like hoof while retaining
    # the same ground-contact plane and original named object identity.
    hoof_x=rings[-1][0]+.018
    hoof=[]
    for height,cx,rx,ry in ((.119,hoof_x-.020,.048,.045),
                           (.058,hoof_x+.004,.074,.061),
                           (.006,hoof_x+.035,.102,.074)):
        for step in range(facets):
            angle=math.tau*step/facets
            hoof.append((cx+rx*math.cos(angle),y+ry*math.sin(angle),height))
    hoof_faces=[tuple(reversed(range(facets)))]
    for ring in range(2):
        for step in range(facets):
            following=(step+1)%facets
            hoof_faces.append((ring*facets+step,ring*facets+following,
                               (ring+1)*facets+following,(ring+1)*facets+step))
    hoof_faces.append(tuple(2*facets+step for step in range(facets)))
    smooth(mesh(f"Horse_{name}_{side}_hoof",hoof,hoof_faces,HOOF))
    tube(f"Horse_{name}_{side}_coronet",
         [(hoof_x-.067,y-.051,.116),(hoof_x,y-.057,.119),
          (hoof_x+.061,y-.050,.116)],.003,COAT_DARK)


for side in (-1, 1):
    leg("fore",side,[(.39,1.11,.146,.128),(.447,.89,.124,.105),
                     (.485,.70,.090,.078),(.475,.49,.061,.054),
                     (.503,.285,.044,.041),(.520,.166,.049,.044),
                     (.524,.114,.052,.048)],dark_from=3)
    leg("hind",side,[(-.57,1.09,.175,.151),(-.655,.85,.151,.126),
                     (-.764,.69,.108,.092),(-.714,.52,.071,.064),
                     (-.817,.37,.048,.045),(-.759,.165,.051,.046),
                     (-.750,.114,.053,.049)],dark_from=3)

# Voxel-weld the overlapping torso, neck, head, and four limbs into one shell.
# This removes hard intersection lines at the shoulders and haunches while
# preserving the distinct dark distal coat below the knees/hocks. It remains
# static sculpt topology, not a deformation-ready equine rig.
anatomical_names=("Horse_torso_continuous","Horse_neck","Horse_jowl","Horse_long_head")
anatomical_names+=tuple(f"Horse_{kind}_{side}_continuous_limb"
                        for side in (-1,1) for kind in ("fore","hind"))
bpy.ops.object.select_all(action="DESELECT")
for target in anatomical_names:
    parts.objects[target].select_set(True)
bpy.context.view_layer.objects.active=parts.objects["Horse_torso_continuous"]
bpy.ops.object.join()
anatomical=bpy.context.object
anatomical.name="Horse_anatomical_core"
anatomical.data.remesh_voxel_size=.014
bpy.ops.object.voxel_remesh()
relax=anatomical.modifiers.new("Organic_joint_relaxation","SMOOTH")
relax.factor=.62
relax.iterations=3
bpy.ops.object.modifier_apply(modifier=relax.name)
smooth(anatomical)
coat_slot=next(i for i,m in enumerate(anatomical.data.materials) if m.name==COAT.name)
dark_slot=next(i for i,m in enumerate(anatomical.data.materials) if m.name==COAT_DARK.name)
for polygon in anatomical.data.polygons:
    polygon.material_index=dark_slot if polygon.center.z < .69 else coat_slot

rng = random.Random(0xAB001)
for side in (-1,1):
    for index in range(52):
        t=(index+.42*rng.random())/52
        x=.37+.39*t
        z=1.355+.335*t-.020*math.sin(math.pi*t)
        y=side*rng.uniform(.025,.070)
        drop=rng.uniform(.043,.105)
        tapered_hair(f"Horse_mane_strand_{side}_{index:02}",
                     [(x,y,z),(x-.018,side*(abs(y)+.025),z+.012),
                      (x-.054,side*(abs(y)+.082),z-drop)],
                     rng.uniform(.0025,.0050),MANE)
for index in range(18):
    y=rng.uniform(-.058,.058)
    tapered_hair(f"Horse_forelock_strand_{index:02}",
                 [(.766,y,1.753),(.806,y*1.3,1.713),
                  (.845,y*1.65,1.653-rng.uniform(0,.025))],
                 rng.uniform(.0025,.0045),MANE)
tube("Horse_tail_root", [(-.78, 0, 1.08), (-.87, .012, .99),
                         (-.975, .028, .83)], .037, MANE)
for index in range(54):
    angle=math.tau*index/54
    y=.030+.046*math.sin(angle)
    x=-.985+.028*math.cos(angle)
    tapered_hair(f"Horse_tail_strand_{index:02}",
                 [(-.91,y*.50,.94),(x,y,.78),
                  (x-.075,y*1.5,.58),
                  (x-.095+rng.uniform(-.035,.035),y*1.85+rng.uniform(-.025,.025),
                   .33+rng.uniform(-.07,.06))],
                 rng.uniform(.0035,.0075),MANE)


# Kura: a black-lacquered wooden tree with raised maewa/shizuwa over a silk
# saddlecloth. The cloth's side panels deliberately leave the legs clear.
for side in (-1, 1):
    y = side * .285
    mesh(f"Saddlecloth_aori_{side}",
         [(-.35, y, 1.30), (.32, y, 1.31), (.33, side*.330, 1.06),
          (.13, side*.355, .995), (-.26, side*.355, 1.035),
          (-.37, side*.320, 1.12)],
         [(0,1,2,3,4,5)], SILK, thickness=.008)
    tube(f"Saddlecloth_crimson_edge_{side}",
         [(-.35,y,1.30),(-.37,side*.320,1.12),(-.26,side*.355,1.035),
          (.13,side*.355,.995),(.33,side*.330,1.06),(.32,y,1.31)],
         .004, SILK_TRIM, 2)
box("Kura_wooden_tree", (-.03,0,1.348), (.48,.46,.055), WOOD, .015)
box("Kura_lacquered_seat", (-.03,0,1.386), (.43,.38,.031), LACQUER, .012)
for label, x, z, height in (("maewa",.210,1.432,.236),("shizuwa",-.263,1.434,.211)):
    # Arched panels rather than a Western continuous saddle horn.
    verts = [(x, -.229, z), (x, -.195, z+height*.75),
             (x, -.11, z+height), (x, .11, z+height),
             (x, .195, z+height*.75), (x,.229,z),
             (x+.020,.229,z),(x+.020,.195,z+height*.75),
             (x+.020,.11,z+height),(x+.020,-.11,z+height),
             (x+.020,-.195,z+height*.75),(x+.020,-.229,z)]
    mesh(f"Kura_{label}_high_lacquer_panel",verts,
         [(0,1,2,3,4,5),(6,7,8,9,10,11),(0,5,6,11),
          (1,0,11,10),(2,1,10,9),(3,2,9,8),(4,3,8,7),(5,4,7,6)],
         RED_LACQUER)
    tube(f"Kura_{label}_metal_edge",
         [(x,-.229,z),(x,-.195,z+height*.75),(x,-.11,z+height),
          (x,.11,z+height),(x,.195,z+height*.75),(x,.229,z)],
         .004, GOLD, 2)

# Girth, front collar, and crupper share attachment points with the tree.
tube("Kura_girth_under_belly", [(-.02,-.252,1.342),(-.02,-.326,.94),
                                 (-.02,-.265,.735),(-.02,0,.680),
                                 (-.02,.265,.735),(-.02,.326,.94),
                                 (-.02,.252,1.342)], .014, LEATHER)
tube("Tack_breaststrap", [(.213,-.242,1.35),(.47,-.290,1.18),
                           (.60,0,1.03),(.47,.290,1.18),(.213,.242,1.35)],
     .010, LEATHER)
tube("Tack_crupper", [(-.261,0,1.40),(-.50,0,1.34),(-.77,0,1.17),
                       (-.83,0,1.045)], .014, LEATHER)


def stirrup(side):
    y = side * .432
    # Met 2016.205a/b hato-mune pair: about 27 x 13 x 25 cm, made in Kashu.
    # Here those dimensions refer to the individual hoof-facing foot enclosure,
    # not a modern open D-ring stirrup. Heel entry is open toward -X.
    foot_z = .855
    x0 = -.155
    x1 = .116
    half_width = .064
    # Tread has an iron bowl profile with a wooden inset and rises at its toe.
    verts = []
    for x, z, width in ((x0,foot_z,.047),(-.07,foot_z-.012,.062),
                        (.018,foot_z-.006,.065),(x1,foot_z+.024,.035)):
        verts.extend([(x,y-width,z),(x,y+width,z)])
    mesh(f"Abumi_{side}_broad_iron_footplate",verts,
         [(0,1,3,2),(2,3,5,4),(4,5,7,6)], IRON, thickness=.013)
    box(f"Abumi_{side}_wooden_tread",(-.035,y,foot_z+.009),
        (.190,.111,.015), WOOD, .004)
    # Curved protective toe shell: diagonal fore wall and open heel.
    profile = [(-.085,.058,.044),(-.045,.164,.059),(.012,.222,.062),
               (.062,.225,.056),(.113,.176,.041),(.142,.103,.017)]
    verts=[]
    for x,height,width in profile:
        verts.extend([(x,y-width,foot_z+height),
                      (x,y,foot_z+height+.014),
                      (x,y+width,foot_z+height)])
    faces=[]
    for i in range(len(profile)-1):
        a=i*3;b=(i+1)*3
        faces.extend([(a,b,b+1,a+1),(a+1,b+1,b+2,a+2)])
    mesh(f"Abumi_{side}_hato_mune_iron_toe_shell",verts,faces,
         IRON,thickness=.006)
    for sy in (-1,1):
        tube(f"Abumi_{side}_iron_side_{sy}",
             [(-.14,y+sy*.048,foot_z),(-.11,y+sy*.055,foot_z+.110),
              (-.055,y+sy*.060,foot_z+.210),(.012,y+sy*.060,foot_z+.246),
              (.082,y+sy*.048,foot_z+.180),(.140,y+sy*.013,foot_z+.10)],
             .006,IRON)
    # Suspension loop and leather stirrup strap must connect to the kura.
    tube(f"Abumi_{side}_strap", [(-.045,side*.261,1.35),
                                  (-.055,side*.321,1.22),
                                  (-.065,y,1.095)], .016, LEATHER)
    tube(f"Abumi_{side}_suspension_loop",
         [(-.090,y,1.083),(-.076,y-.028,1.127),
          (-.036,y,1.134),(-.076,y+.028,1.127),(-.090,y,1.083)],
         .007,IRON)
    # Exterior surface inlay, intentionally small, keeps functional iron clear.
    tube(f"Abumi_{side}_silver_toe_inlay",
         [(.124,y-.032,foot_z+.119),(.131,y,foot_z+.142),
          (.124,y+.032,foot_z+.119)], .0025,SILVER,2)


for side in (-1,1):
    stirrup(side)

# Omogai (headstall) and kutsuwa/ham(i) connect each tazuna to the mouth.
# This is a neutral standing pose. The rein ends are loose attachment points,
# not fake taut lines to an absent rider's hand.
for side in (-1,1):
    sy=side
    tube(f"Omogai_cheekpiece_{side}",
         [(.820,sy*.135,1.715),(.795,sy*.171,1.604),
          (.945,sy*.166,1.470),(1.100,sy*.144,1.330)],
         .009,LEATHER)
    tube(f"Omogai_noseband_{side}",
         [(1.039,sy*.121,1.417),(1.095,sy*.148,1.403),
          (1.155,sy*.130,1.383)], .011,LEATHER)
    sphere(f"Kutsuwa_bit_ring_{side}",(1.104,sy*.154,1.328),
           (.028,.009,.028),IRON,22,14)
    tube(f"Tazuna_rein_{side}",
         [(1.113,sy*.156,1.323),(.945,sy*.224,1.205),
          (.672,sy*.29,1.183),(.316,sy*.202,1.255),
          (.183,sy*.125,1.352)],.006,LEATHER,3)
    sphere(f"Tazuna_free_end_{side}",(.183,sy*.125,1.352),
           (.011,.011,.011),GOLD,12,8)
tube("Omogai_browband",[(.791,-.143,1.698),(.862,0,1.704),
                          (.791,.143,1.698)],.010,LEATHER)
tube("Omogai_throatlatch",[(.790,-.158,1.609),(.716,-.175,1.507),
                             (.718,0,1.457),(.716,.175,1.507),
                             (.790,.158,1.609)],.008,LEATHER)
cone_between("Kutsuwa_hami_bar",(1.104,-.146,1.328),
             (1.104,.146,1.328),.006,.006,IRON,12)


def add_exact_sora_mon(label, position, plane, diameter):
    """Place two unmodified SVG paths as a relief on an X- or Y-facing plate."""
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(LOGO))
    curves=[o for o in set(bpy.data.objects)-before if o.type=="CURVE"]
    assert len(curves)==2,[o.name for o in curves]
    corners=[o.matrix_world @ Vector(c) for o in curves for c in o.bound_box]
    low_x=min(p.x for p in corners); high_x=max(p.x for p in corners)
    low_y=min(p.y for p in corners); high_y=max(p.y for p in corners)
    cx=(low_x+high_x)/2;cy=(low_y+high_y)/2
    scale=diameter/max(high_x-low_x,high_y-low_y)
    for index,obj in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        obj=bpy.context.object
        for vert in obj.data.vertices:
            p=obj.matrix_world @ vert.co
            u=(p.x-cx)*scale;v=(p.y-cy)*scale
            if plane=="X":
                vert.co=(position[0],position[1]+u,position[2]+v)
            elif plane=="Y":
                vert.co=(position[0]+u,position[1],position[2]+v)
            else:
                raise ValueError(plane)
        obj.matrix_world.identity()
        move(obj,f"SORA_kamon_exact_svg_{label}_{index}")
        obj.data.materials.clear()
        obj.data.materials.append(SORA_RED)
        obj["source_svg_sha256"]=LOGO_RECORD["source_sha256"]


# Real late-16th/early-17th-century abumi in the Met have a clan mon at the
# front (Met 2008.120.1/.2). The game's newly founded resistance substitutes
# its supplied exact SORA mon; this is fictional insignia, not an Edo emblem.
for side in (-1,1):
    add_exact_sora_mon(f"abumi_{side}",(.149,side*.432,.967),"X",.050)
    add_exact_sora_mon(f"aori_{side}",(-.030,side*.365,1.117),"Y",.090)

# Named attachment anchors in the editable .blend for a future horse rig.
anchors={
    "Horse_Root":(0,0,0),"Saddle_RiderSeat":(-.03,0,1.43),
    "Tazuna_LeftGrip":(.183,-.125,1.352),
    "Tazuna_RightGrip":(.183,.125,1.352),
    "Abumi_LeftFoot":(-.035,-.432,.867),
    "Abumi_RightFoot":(-.035,.432,.867),
}
for name,location in anchors.items():
    empty=bpy.data.objects.new(name,None)
    parts.objects.link(empty)
    empty.location=location
    empty.empty_display_type="SPHERE"
    empty.empty_display_size=.035

source_meshes=[o for o in parts.objects if o.type=="MESH"]
triangles=sum(len(p.vertices)-2 for o in source_meshes for p in o.data.polygons)
verts_world=[o.matrix_world @ v.co for o in source_meshes for v in o.data.vertices]
bounds={"min":[round(min(p[i] for p in verts_world),4) for i in range(3)],
        "max":[round(max(p[i] for p in verts_world),4) for i in range(3)]}

# Export a single static review mesh. Editable, independently named components
# and attachment empties remain in the Blender source.
bpy.ops.object.select_all(action="DESELECT")
for obj in source_meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active=source_meshes[0]
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active=bpy.context.selected_objects[0]
bpy.ops.object.join()
export=bpy.context.object
export.name=NAME
for coll in tuple(export.users_collection):
    coll.objects.unlink(export)
export_collection=bpy.data.collections.new("Unreal_Export_Only")
scene.collection.children.link(export_collection)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,
                         object_types={"MESH"},add_leaf_bones=False,
                         apply_unit_scale=True,axis_forward="-Y",axis_up="Z")
export.hide_render=True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")

studio=bpy.data.collections.new("Blender_Review_Only")
scene.collection.children.link(studio)
floor=box("Review_ground",(0,0,-.024),(200,200,.040),
          material("M_Review_Ground",(.029,.038,.048),.85))
for collection in tuple(floor.users_collection):
    collection.objects.unlink(floor)
studio.objects.link(floor)
def area(name, location, power, size, color):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power;data.shape="DISK";data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data)
    studio.objects.link(obj);obj.location=location
    obj.rotation_euler=(Vector((0,0,.9))-obj.location).to_track_quat("-Z","Y").to_euler()
area("Lantern_key",(2.7,-3.3,3.9),720,3.4,(1,.79,.58))
area("Moon_rim",(-2.8,2.0,2.8),650,2.8,(.45,.67,1))
area("Soft_fill",(2.0,2.7,2.3),470,3.0,(.85,.90,1))
world=bpy.data.worlds.new("Overcast_review")
scene.world=world;world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.12,.14,.18,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.45
scene.render.engine="CYCLES"
scene.cycles.samples=32
scene.render.resolution_x=1400
scene.render.resolution_y=1060
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
cam_data=bpy.data.cameras.new("Review_camera")
cam=bpy.data.objects.new("Review_camera",cam_data)
studio.objects.link(cam);scene.camera=cam
cam_data.type="ORTHO";cam_data.ortho_scale=3.12
cam.location=(3.0,-4.7,2.25)
cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath=str(PREVIEW)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest={
    "schema_version":1,"name":NAME,
    "generator":"scripts/art/create_nyaagyu_horse_tack.py",
    "validator":"scripts/art/validate_nyaagyu_horse_tack.py",
    "source_blend":BLEND.name,"blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "preview":PREVIEW.name,"preview_sha256":sha(PREVIEW),
    "unreal_asset":f"/Game/ArtReview/Horses/{NAME}.{NAME}",
    "local_forward":"+X horse-forward; +Z up",
    "world_origin_m":[0,0,0],"units":"meters",
    "source_parts":len(source_meshes),"source_triangles":triangles,
    "bounds_m":bounds,"rigged":False,"external_images":[],
    "anchors_m":anchors,
    "insignia_source":"../../UI/sora_logo_NOtext2.svg",
    "insignia_sha256":LOGO_RECORD["source_sha256"],
    "license":"Original project-owned horse/tack geometry, shaders, and review render. Exact user-supplied SORA SVG paths retain user-provided provenance and are used for this game. No purchased models or textures.",
    "limitations":"Static, unrigged anatomy and tack study, not a photoreal shipping horse. No measured horse gait, rein dynamics, riding physics, deformation, UE 5.8.2 import, or gameplay validation. Historical object forms inform this fictional equipment but are not claimed as exact replica.",
}
MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_HORSE_TACK_SOURCE_CREATED",len(source_meshes),triangles,bounds)
