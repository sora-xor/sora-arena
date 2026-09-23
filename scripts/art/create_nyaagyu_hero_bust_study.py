"""Build an original higher-detail feline samurai head and upper-body study.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_hero_bust_study.py
The separate, unrigged art-review source does not replace the existing hero.
All geometry, vertex colors, fur cards, procedural PBR shaders and lighting are
authored here. No stock/purchased/external model or texture is sampled. The
Blender renders are reviews, not Unreal screenshots or photoreal validation.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/HeroBustStudy"
NAME = "SM_Nyaagyu_HeroBustStudy"
BLEND = OUT / "Nyaagyu_HeroBustStudy.blend"
FBX = OUT / (NAME + ".fbx")
PORTRAIT = OUT / "Nyaagyu_HeroBust_Portrait_Blender.png"
DETAIL = OUT / "Nyaagyu_HeroBust_Face_Blender.png"
MANIFEST = OUT / "manifest.json"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
asset = bpy.data.collections.new("NyaagyuHeroBust_Editable")
scene.collection.children.link(asset)


def shader(name, rgb, rough, metal=0, coat=0, noise=0, bump=0, emit=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    n, links = m.node_tree.nodes, m.node_tree.links
    bsdf = n.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
        bsdf.inputs["Emission Strength"].default_value = emit
    if noise:
        tex = n.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise
        tex.inputs["Detail"].default_value = 3
        tex.inputs["Roughness"].default_value = .65
        ramp = n.new("ShaderNodeMapRange")
        ramp.inputs["To Min"].default_value = rough * .72
        ramp.inputs["To Max"].default_value = min(.98, rough * 1.22)
        links.new(tex.outputs["Fac"], ramp.inputs["Value"])
        links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])
        coarse = n.new("ShaderNodeTexNoise")
        coarse.inputs["Scale"].default_value = max(4,noise/22)
        coarse.inputs["Detail"].default_value = 4
        wear = n.new("ShaderNodeValToRGB")
        wear.color_ramp.elements[0].position = .24
        wear.color_ramp.elements[1].position = .79
        wear.color_ramp.elements[0].color = (*[c*.58 for c in rgb],1)
        wear.color_ramp.elements[1].color = (*[min(1,c*1.23) for c in rgb],1)
        links.new(coarse.outputs["Fac"],wear.inputs["Fac"])
        links.new(wear.outputs["Color"],bsdf.inputs["Base Color"])
        if bump:
            b = n.new("ShaderNodeBump")
            b.inputs["Strength"].default_value = .18
            b.inputs["Distance"].default_value = bump
            links.new(tex.outputs["Fac"], b.inputs["Height"])
            links.new(b.outputs["Normal"], bsdf.inputs["Normal"])
    return m


COAT = shader("M_Bust_CoatVertexColor", (.20,.16,.12), .89, noise=190, bump=.00008)
coat_nodes = COAT.node_tree.nodes
coat_links = COAT.node_tree.links
coat_attribute = coat_nodes.new("ShaderNodeVertexColor")
coat_attribute.layer_name = "CoatColor"
coat_links.new(coat_attribute.outputs["Color"], coat_nodes.get("Principled BSDF").inputs["Base Color"])
FUR_BROWN = shader("M_Bust_FurBrownCards", (.10,.079,.061), .9)
FUR_DARK = shader("M_Bust_FurDarkCards", (.024,.021,.020), .93)
FUR_LIGHT = shader("M_Bust_FurLightCards", (.32,.27,.21), .93)
FUR_WHITE = shader("M_Bust_FurWhiteCards", (.45,.40,.32), .95)
PINK = shader("M_Bust_EarSkin", (.25,.12,.105), .72, noise=120, bump=.000035)
NOSE = shader("M_Bust_RoseBrownNose", (.23,.12,.105), .42, coat=.25, noise=85, bump=.00003)
MOUTH = shader("M_Bust_MouthShadow", (.020,.017,.016), .75)
EYE_SCLERA = shader("M_Bust_DarkEyeBed", (.022,.023,.020), .26, coat=.5)
IRIS = shader("M_Bust_GoldGreenIris", (.31,.34,.12), .21, coat=.4, noise=160, bump=.00001)
PUPIL = shader("M_Bust_VerticalPupil", (.004,.005,.004), .09, coat=.6)
EYE_GLINT = shader("M_Bust_CorneaGlint", (.89,.91,.85), .08)
INDIGO = shader("M_Bust_WeatheredIndigoLinen", (.021,.027,.033), .81, noise=205, bump=.00017)
INDIGO_EDGE = shader("M_Bust_IndigoSeam", (.047,.051,.055), .88, noise=185, bump=.00012)
LINEN = shader("M_Bust_NaturalLinen", (.43,.36,.28), .89, noise=210, bump=.00018)
LACQUER = shader("M_Bust_SmokedUrushi", (.052,.029,.023), .32, coat=.4, noise=85, bump=.00007)
LACQUER_WEAR = shader("M_Bust_WornUrushiEdge", (.13,.072,.041), .48, coat=.12, noise=110, bump=.00008)
IRON = shader("M_Bust_BurnishedIron", (.075,.080,.076), .38, metal=.86, noise=100, bump=.00006)
BRONZE = shader("M_Bust_DarkBronze", (.32,.20,.095), .39, metal=.86, noise=105, bump=.00006)
TEAL = shader("M_Bust_InductionGlass", (.020,.23,.24), .18, metal=.12, coat=.5, emit=.4)


def keep(obj, name, mat=None):
    obj.name = name
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    asset.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    obj["authorship"] = "Original SORA Arena higher-detail hero bust study"
    return obj


def smooth(obj):
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def ellipsoid(name, center, radii, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = keep(bpy.context.object, name, mat)
    obj.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return smooth(obj)


def bevel(obj, width=.002, segments=2):
    if width:
        m = obj.modifiers.new("SoftHandmadeEdges", "BEVEL")
        m.width = width
        m.segments = segments
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=m.name)
    return smooth(obj)


def box(name, center, dims, mat, edge=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return bevel(obj, edge)


def curve_mesh(name, points, radius, mat, resolution=2):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for point, pos in zip(spline.bezier_points, points):
        point.co = pos
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    asset.objects.link(obj)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj["authorship"] = "Original SORA Arena higher-detail hero bust study"
    return obj


def surface(name, verts, faces, mat, thickness=0):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    mesh.materials.append(mat)
    obj["authorship"] = "Original SORA Arena higher-detail hero bust study"
    if thickness:
        mod = obj.modifiers.new("ClothDepth", "SOLIDIFY")
        mod.thickness = thickness
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def coat_color(pos):
    x, y, z = pos
    # Anatomical cream underside and muzzle, irregular tabby saddle/forehead.
    if (x > .115 and z < 1.525) or (z < 1.456 and x > .045):
        base = (.32,.27,.21)
    elif z < 1.45:
        base = (.16,.125,.095)
    else:
        base = (.112,.083,.061)
    stripe = math.sin(47*y + 28*z + 13*x + 2.4*math.sin(18*z-22*x))
    stripe *= .55+.45*math.sin(10*x+6*z)
    if z > 1.54 and stripe > .45:
        base = (.020,.018,.017)
    elif abs(y) > .10 and z < 1.58 and math.sin(38*z+13*x+22*abs(y)) > .69:
        base = (.026,.022,.019)
    grain = .95+.05*math.sin(173*x+157*y+133*z)
    return tuple(max(.008,min(1,c*grain)) for c in base)


def fuse_head():
    # A continuous remeshed skin eliminates the obvious stacked-sphere seams
    # of the existing concept. Anatomical masses form cranium, zygomatic cheek,
    # bridge, whisker pads, jaw and brows before voxel fusion.
    ingredients = []
    for name, center, radii in (
        ("Cranium",(-.020,0,1.590),(.163,.159,.173)),
        ("TaperedFace",(.064,0,1.566),(.118,.129,.138)),
        ("NasalBridge",(.137,0,1.557),(.068,.060,.061)),
        ("Mandible",(.120,0,1.462),(.104,.111,.055)),
    ):
        ingredients.append(ellipsoid(name,center,radii,COAT,40,28))
    for side in (-1,1):
        ingredients.append(ellipsoid(f"CheekBone_{side}",(.033,side*.106,1.534),(.097,.087,.095),COAT,32,22))
        ingredients.append(ellipsoid(f"WhiskerPad_{side}",(.163,side*.048,1.484),(.069,.060,.045),COAT,32,22))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in ingredients:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = ingredients[0]
    bpy.ops.object.join()
    head = bpy.context.object
    head.name = "FusedAnatomicalHead"
    head.data.remesh_voxel_size = .006
    bpy.ops.object.voxel_remesh()
    modifier = head.modifiers.new("SoftenVoxelTransitions", "SMOOTH")
    modifier.factor = 1.2
    modifier.iterations = 4
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    smooth(head)
    color = head.data.color_attributes.new(name="CoatColor", type="FLOAT_COLOR", domain="CORNER")
    for polygon in head.data.polygons:
        for loop_id in polygon.loop_indices:
            v = head.data.vertices[head.data.loops[loop_id].vertex_index]
            rgb = coat_color(head.matrix_world @ v.co)
            color.data[loop_id].color = (*rgb,1)
    head["method"] = "Original merged feline anatomy, 6 mm voxel remesh, vertex-color tabby coat"
    return head


head = fuse_head()


def front_skin_x(y, z):
    """Find the actual fused skin, so eyes cannot float off the face."""
    inverse = head.matrix_world.inverted()
    origin = inverse @ Vector((.5,y,z))
    direction = (inverse.to_3x3() @ Vector((-1,0,0))).normalized()
    hit, local_point, _normal, _index = head.ray_cast(origin,direction)
    if not hit:
        raise RuntimeError(f"No fused head under facial feature at {(y,z)}")
    return (head.matrix_world @ local_point).x


def skin_almond(name, cy, cz, ry, rz, mat, lift):
    verts=[];faces=[]
    verts.append((front_skin_x(cy,cz)+lift,cy,cz))
    for i in range(20):
        a=math.tau*i/20
        y=cy+ry*math.cos(a)
        z=cz+rz*math.sin(a)*(1-.20*abs(math.cos(a)))
        verts.append((front_skin_x(y,z)+lift,y,z))
    for i in range(20):
        faces.append((0,1+i,1+(i+1)%20))
    obj=smooth(surface(name,verts,faces,mat))
    obj["fit"]="Ray cast onto the continuous face skin; no free-floating eyeball"
    return obj


def fur_cards(name, source, count, seed, length, skip_eyes=False):
    """Sample source triangles by area; root each tapered card on real skin."""
    rng = random.Random(seed)
    mesh = source.data
    mesh.calc_loop_triangles()
    triangles = mesh.loop_triangles
    areas = []
    cumulative = []
    total = 0.0
    for tri in triangles:
        a,b,c = (source.matrix_world @ mesh.vertices[i].co for i in tri.vertices)
        area = (b-a).cross(c-a).length*.5
        total += area
        cumulative.append(total)
        areas.append((a,b,c))
    verts, faces, indices = [], [], []
    used = 0
    for _ in range(count):
        index = min(len(triangles)-1,bisect.bisect_left(cumulative,rng.random()*total))
        a,b,c = areas[index]
        u,v = rng.random(),rng.random()
        if u+v>1:
            u,v=1-u,1-v
        point=a+u*(b-a)+v*(c-a)
        normal=(b-a).cross(c-a).normalized()
        if skip_eyes and point.x>.105 and 1.61<point.z<1.71 and abs(point.y)<.15:
            continue
        if point.x>.20 and point.z<1.51 and abs(point.y)<.05:
            continue
        tangent=normal.cross(Vector((0,0,1)))
        if tangent.length<.015:
            tangent=normal.cross(Vector((0,1,0)))
        tangent.normalize()
        drift=(normal*.38+Vector((-.29,rng.uniform(-.06,.06),-.42))).normalized()
        reach=rng.uniform(length*.55,length*1.3)
        root=point+normal*.0007
        tip=root+drift*reach
        width=rng.uniform(.00013,.00036)
        base=len(verts)
        verts.extend((root-tangent*width,root+tangent*width,tip))
        faces.append((base,base+1,base+2))
        rgb=coat_color(point)
        indices.append(1 if rgb[0]<.040 else (3 if rgb[0]>.29 else (2 if rgb[0]>.15 else 0)))
        used+=1
    obj=surface(name,verts,faces,FUR_BROWN)
    for mat in (FUR_DARK,FUR_LIGHT,FUR_WHITE):
        obj.data.materials.append(mat)
    for polygon, material_index in zip(obj.data.polygons,indices):
        polygon.material_index=material_index
    obj["card_count"] = used
    obj["card_topology"] = "single tapered opaque triangle, rooted on sampled source surface"
    return obj


scalp_cards=fur_cards("FurCards_ShortScalpAndCheeks",head,32000,14081,.009,True)


def ear(sign):
    # Rounded multi-section pinna, dark outer rim and recessed skin concavity.
    y=sign*.116
    z_levels=(1.690,1.730,1.775,1.830,1.858)
    half=(.072,.069,.050,.025,.004)
    centers=((-.045,y),(-.051,y+sign*.008),(-.061,y+sign*.013),(-.071,y+sign*.023),(-.079,y+sign*.029))
    verts=[];faces=[]
    for z,w,(x,cy) in zip(z_levels,half,centers):
        for j in range(8):
            t=math.tau*j/8
            verts.append((x+.020*math.cos(t),cy+w*math.sin(t),z))
    for row in range(4):
        for j in range(8):
            k=(j+1)%8
            faces.append((row*8+j,row*8+k,(row+1)*8+k,(row+1)*8+j))
    faces += [tuple(reversed(range(8))),tuple(range(32,40))]
    shell=smooth(surface(f"PinnaOuter_{sign}",verts,faces,FUR_DARK))
    shell["anatomy"]="rounded multi-section pinna, not flat triangular ear"
    skin_verts=[];skin_faces=[]
    # Three vertices across each level form a concave bowl: its center lies
    # behind the rim in +X facing space, so the skin is not a pasted-on plane.
    for z,w,edge_x,mid_x in ((1.708,.046,-.026,-.041),
                              (1.755,.040,-.033,-.053),
                              (1.803,.022,-.050,-.067),
                              (1.836,.004,-.066,-.076)):
        skin_verts.extend(((edge_x,y-sign*w,z),(mid_x,y,z-.003),
                           (edge_x,y+sign*w,z)))
    for row in range(3):
        q=row*3
        skin_faces.extend(((q,q+1,q+4,q+3),(q+1,q+2,q+5,q+4)))
    smooth(surface(f"ConcavePinnaSkin_{sign}",skin_verts,skin_faces,PINK,.001))
    curve_mesh(f"PinnaRim_{sign}",[(-.025,y-sign*.046,1.708),(-.035,y-sign*.039,1.758),
                                 (-.068,y+sign*.004,1.837),(-.035,y+sign*.040,1.758)],.0015,FUR_BROWN,1)
    fur_cards(f"FurCards_Pinna_{sign}",shell,1200,14251+sign,.005,False)
    for i in range(9):
        dy=sign*(-.028+i*.007)
        curve_mesh(f"InnerEarGuardHair_{sign}_{i}",[(.001,y+dy,1.725),(-.036,y+dy*.55,1.782)],
                   .00024,FUR_WHITE,1)


for side in (-1,1):
    ear(side)
    # Eye patches are projected onto fused anatomy, with overlapping lids. A
    # shallow iris/pupil relief survives FBX without cartoon-sphere protrusion.
    cy=side*.079
    skin_almond(f"SeatedEyeBed_{side}",cy,1.630,.033,.017,EYE_SCLERA,.0011)
    skin_almond(f"SeatedIris_{side}",cy,1.630,.017,.014,IRIS,.0018)
    skin_almond(f"SeatedVerticalSlit_{side}",cy,1.630,.0035,.0125,PUPIL,.0024)
    skin_almond(f"CornealCatchlight_{side}",cy-side*.007,1.638,.002,.0023,EYE_GLINT,.0027)
    upper=[];lower=[]
    for step in range(7):
        t=step/6
        y=side*(.045+.067*t)
        z_up=1.630+.017*math.sin(math.pi*t)
        z_lo=1.630-.014*math.sin(math.pi*t)
        upper.append((front_skin_x(y,z_up)+.003,y,z_up))
        lower.append((front_skin_x(y,z_lo)+.0026,y,z_lo))
    curve_mesh(f"UpperLid_{side}",upper,.0027,FUR_DARK)
    curve_mesh(f"LowerLid_{side}",lower,.0017,FUR_LIGHT)
    for dot in range(6):
        y=side*(.032+dot*.011)
        z=1.486+(dot%3-1)*.011
        ellipsoid(f"WhiskerFollicle_{side}_{dot}",(.236-abs(dot-2)*.002,y,z),
                  (.0016,.002,.0015),FUR_DARK,10,7)
    for strand in range(5):
        z=1.473+strand*.006
        curve_mesh(f"Whisker_{side}_{strand}",[(.225,side*.045,z),
                   (.254,side*(.128+strand*.006),z+(strand-2)*.008),
                   (.232+(strand%3)*.011,side*(.194+strand*.012),z+(strand-2)*.016)],
                   .00016,FUR_LIGHT,1)

# A sculpted triangular leathery nose, philtrum, and understated mouth.
nose_vertices=[(.247,-.030,1.511),(.247,.030,1.511),(.271,0,1.491),
               (.247,-.016,1.500),(.247,.016,1.500)]
smooth(surface("CartilageNose",nose_vertices,[(0,1,2),(0,2,3),(1,4,2),(3,2,4)],NOSE,.001))
curve_mesh("Philtrum",[(.263,0,1.491),(.257,0,1.469)],.0012,MOUTH,1)
for side in (-1,1):
    curve_mesh(f"MouthCorner_{side}",[(.257,0,1.469),(.240,side*.043,1.459),
                                     (.213,side*.059,1.467)],.0012,MOUTH,1)


# Upper-body silhouette: layered linen/indigo kimono, shoulder cloth, a
# restrained lamellar cuirass, real stitched seams and a small induction device.
ellipsoid("NeckCoat",(-.047,0,1.374),(.112,.113,.173),COAT,36,24)
ellipsoid("UpperTorsoUnderlayer",(-.047,0,1.128),(.188,.241,.250),LINEN,40,26)
ellipsoid("IndigoHaoriBody",(-.065,0,1.112),(.205,.262,.212),INDIGO,40,26)
for side in (-1,1):
    ellipsoid(f"ShoulderFold_{side}",(-.064,side*.249,1.244),(.124,.114,.121),INDIGO,32,20)
    ellipsoid(f"SleeveFall_{side}",(-.067,side*.296,1.113),(.116,.100,.172),INDIGO,28,20)
    curve_mesh(f"HaoriSeam_{side}",[(.024,side*.309,1.315),(.045,side*.352,1.177),
                                   (.036,side*.335,.997)],.0017,INDIGO_EDGE,1)
    # Armor plates sit over the fabric with readable raised lacquer edges.
    for row in range(5):
        z=1.239-row*.055
        x=.092+row*.008
        plate=box(f"LamellarSode_{side}_{row}",(x,side*(.253+row*.005),z),
                  (.080,.122,.044),LACQUER,.008)
        plate.rotation_euler[0]=side*.12
        curve_mesh(f"SodeLace_{side}_{row}",[(x+.043,side*.214,z+.012),
                    (x+.044,side*.252,z-.014),(x+.043,side*.294,z+.011)],
                    .0015,INDIGO_EDGE,1)
    for row in range(3):
        z=1.347-row*.043
        curve_mesh(f"CollarStitch_{side}_{row}",[(.058,side*.091,z),
                   (.109,side*.128,z-.054)],.00075,LINEN,1)

for side in (-1,1):
    curve_mesh(f"CrossKimonoCollar_{side}",[(.055,side*.120,1.383),
               (.150,side*.049,1.269),(.167,-side*.084,1.145)],
               .012,LINEN if side<0 else INDIGO_EDGE,2)
for row in range(6):
    z=1.245-row*.052
    half_width=.187 if row<4 else .206
    for side in (-1,1):
        y=side*.091
        plate=box(f"DoPlate_{side}_{row}",(.162,y,z),(.031,half_width,.047),
                  LACQUER if row%3 else LACQUER_WEAR,.004)
        plate.rotation_euler[0]=side*.055
        for dot in (-1,1):
            ellipsoid(f"BronzeRivet_{side}_{row}_{dot}",(.181,y+dot*.069,z),
                      (.0025,.0035,.0035),BRONZE,10,8)
        curve_mesh(f"ArmorBinding_{side}_{row}",[(.183,y-side*.058,z+.012),
                   (.184,y,z-.015),(.183,y+side*.058,z+.012)],.0015,INDIGO_EDGE,1)
box("WaistSash",(-.042,0,.944),(.364,.491,.070),INDIGO,.015)
for stripe in range(4):
    curve_mesh(f"WaistSashTwist_{stripe}",[(.15,-.198+stripe*.13,.960),
               (.155,-.172+stripe*.13,.925)],.002,INDIGO_EDGE,1)
box("InductionHousing",(-.135,-.266,1.096),(.097,.035,.115),IRON,.008)
box("InductionGlass",(-.128,-.290,1.100),(.055,.004,.064),TEAL,.003)
for side in (-1,1):
    box(f"InductionBolt_{side}",(-.133,-.286,1.100+side*.043),(.012,.007,.009),BRONZE,.001)


pieces=[obj for obj in asset.objects if obj.type=="MESH"]
source_triangles=sum(len(poly.vertices)-2 for obj in pieces for poly in obj.data.polygons)
cards=sum(obj.get("card_count",0) for obj in pieces)
assert 10000<source_triangles<160000, source_triangles
assert 25000<cards<36000, cards
corners=[obj.matrix_world @ Vector(c) for obj in pieces for c in obj.bound_box]
bounds={key:[round(fn(p[axis] for p in corners),4) for axis in range(3)]
        for key,fn in (("min",min),("max",max))}

# Export one joined static review mesh, retaining every source part editable.
# Fur cards use opaque tapered triangle geometry; UE will need double-sided
# shader evaluation and LOD/groom qualification before any runtime use.
bpy.ops.object.select_all(action="DESELECT")
for obj in pieces:
    obj.select_set(True)
bpy.context.view_layer.objects.active=pieces[0]
bpy.ops.object.duplicate()
copies=list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active=copies[0]
bpy.ops.object.join()
export=bpy.context.object
export.name=NAME
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={"MESH"},
                         apply_unit_scale=True,global_scale=1,axis_forward="-Y",axis_up="Z",
                         add_leaf_bones=False,bake_anim=False,path_mode="STRIP")
bpy.data.objects.remove(export,do_unlink=True)


# Neutral low-key review set; excluded from export but retained in the blend.
review=bpy.data.collections.new("ReviewStage_NotForExport")
scene.collection.children.link(review)
floor_mat=shader("M_Review_Charcoal",(.019,.022,.023),.86)
bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,.875))
floor=bpy.context.object
floor.name="Review_Floor"
floor.data.materials.append(floor_mat)
for col in tuple(floor.users_collection):
    col.objects.unlink(floor)
review.objects.link(floor)


def light(name,location,color,power,size):
    bpy.ops.object.light_add(type="AREA",location=location)
    obj=bpy.context.object
    obj.name=name
    obj.data.energy=power
    obj.data.color=color
    obj.data.shape="DISK"
    obj.data.size=size
    obj.rotation_euler=(Vector((.04,0,1.51))-obj.location).to_track_quat("-Z","Y").to_euler()
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    review.objects.link(obj)


light("WarmLanternKey",(.62,-.75,2.37),(1,.72,.47),42,.9)
light("CoolMoonRim",(-.75,.44,2.08),(.49,.71,1),58,.85)
light("SoftFrontFill",(.74,.28,1.66),(.87,.90,1),27,.85)
bpy.ops.object.camera_add(location=(1.17,-.68,1.73))
camera=bpy.context.object
camera.name="PortraitCamera"
camera.rotation_euler=(Vector((.025,0,1.42))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO"
camera.data.ortho_scale=.90
scene.camera=camera
scene.render.engine="CYCLES"
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1200
scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.world.color=(.022,.025,.029)
scene.view_settings.view_transform="AgX"
scene.view_settings.exposure=-.45
scene.render.image_settings.file_format="PNG"
scene.render.filepath=str(PORTRAIT)
bpy.ops.render.render(write_still=True)
camera.location=(.87,-.38,1.69)
camera.rotation_euler=(Vector((.075,0,1.605))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=.50
scene.render.filepath=str(DETAIL)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

record={
    "schema_version":1,
    "name":NAME,
    "generator":"scripts/art/create_nyaagyu_hero_bust_study.py",
    "generator_blender":bpy.app.version_string,
    "source_blend":BLEND.name,
    "fbx":FBX.name,
    "portrait_preview":PORTRAIT.name,
    "face_preview":DETAIL.name,
    "source_parts":len(pieces),
    "source_triangles":source_triangles,
    "fur_cards":cards,
    "head_voxel_m":.006,
    "bounds_m":bounds,
    "local_forward":"+X face-forward; +Z up",
    "materials":[m.name for m in bpy.data.materials if m.name.startswith("M_Bust_")],
    "review_render":{"renderer":"Blender Cycles","resolution_px":[1200,1200],"samples":32,"denoising":True},
    "runtime_performance":f"Unmeasured. {source_triangles:,}-triangle source with {cards:,} opaque triangular fur cards requires LOD, two-sided shader and UE 5.8/target-hardware profiling before any gameplay use.",
    "license":"Original project-owned geometry, vertex colors, procedurally authored shaders, fur cards and review renders; no paid or third-party mesh/texture",
    "external_images":[],
    "scope":"Unrigged static head/upper-body visual study; excluded from runtime and authored as a separate variant of the existing hero",
    "limitations":"No Unreal import, animation, groom, cloth simulation, LOD, cross-platform performance or photoreal certification. Hair cards need two-sided material and LOD review. Blender shader graphs require deliberate Unreal equivalents.",
    "blend_sha256":hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    "fbx_sha256":hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "portrait_preview_sha256":hashlib.sha256(PORTRAIT.read_bytes()).hexdigest(),
    "face_preview_sha256":hashlib.sha256(DETAIL.read_bytes()).hexdigest(),
}
MANIFEST.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print("NYAAGYU_BUST_STUDY_READY",len(pieces),source_triangles,cards,bounds)
