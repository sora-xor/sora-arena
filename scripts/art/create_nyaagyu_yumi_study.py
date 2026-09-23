"""Build an editable first-person yumi/ya study in metres.

This is a visual candidate, not a certified historical reconstruction.  The
asymmetric bow is swept from individually sampled curved rings, rather than
scaled cubes.  The bamboo face uses a hash-pinned CC0 photographic PBR scan.
Run with: blender -b --factory-startup --python scripts/art/create_nyaagyu_yumi_study.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi"
TEX = OUT / "Textures"
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "Nyaagyu_Yumi_Study.blend"
FBX = OUT / "SM_Nyaagyu_Yumi_Study.fbx"
RENDER = OUT / "Nyaagyu_Yumi_ThreeQuarter.png"
SIDE = OUT / "Nyaagyu_Yumi_Profile.png"
DETAIL = OUT / "Nyaagyu_Yumi_GripDetail.png"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
LOGO_RECORD = json.loads((LOGO.parent / "sora_logo_manifest.json").read_text())
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == LOGO_RECORD["source_sha256"]

SCAN = {
    "Albedo": ("bamboo_veneer_diff_2k.jpg", "fa0e742547faf21baa35455528d03da5"),
    "NormalDX": ("bamboo_veneer_nor_dx_2k.png", "ab51a4a010cd4d4060adf943ef29d816"),
    "ARM": ("bamboo_veneer_arm_2k.png", "3f1b621d3846f76b78ab6b23423aad77"),
}
LEATHER = {
    "Albedo": ("brown_leather_albedo_2k.jpg", "1bd381c43817743a2affdd1ce2d193c7"),
    "NormalDX": ("brown_leather_nor_dx_2k.png", "9f1c1a25da2f1b86bff92e5d0ca45257"),
    "ARM": ("brown_leather_arm_2k.png", "2889ad73bce0e089e58ee2183408f7d4"),
}
for surface in (SCAN, LEATHER):
    for channel, (filename, md5) in surface.items():
        assert hashlib.md5((TEX / filename).read_bytes()).hexdigest() == md5, channel

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
editable = bpy.data.collections.new("Yumi_Editable")
scene.collection.children.link(editable)
review = bpy.data.collections.new("Review_Only")
scene.collection.children.link(review)


def image_material(name, tint, roughness_scale=1.0, metal=0.0, source=SCAN):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    images = {}
    for channel, (filename, _) in source.items():
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(TEX / filename), check_existing=True)
        node.image.colorspace_settings.name = "sRGB" if channel == "Albedo" else "Non-Color"
        node.name = ("CC0_BambooVeneer_" if source is SCAN else "CC0_BrownLeather_") + channel
        images[channel] = node
    color = nodes.new("ShaderNodeMixRGB")
    color.blend_type = "MULTIPLY"
    color.inputs[0].default_value = 1.0
    color.inputs[2].default_value = (*tint, 1)
    links.new(images["Albedo"].outputs["Color"], color.inputs[1])
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["ARM"].outputs["Color"], split.inputs["Color"])
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = roughness_scale
    links.new(split.outputs["Green"], scale.inputs[0])
    links.new(scale.outputs[0], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = metal
    # The delivered map is DirectX. Blender needs the Y channel reversed.
    ns = nodes.new("ShaderNodeSeparateColor")
    links.new(images["NormalDX"].outputs["Color"], ns.inputs["Color"])
    inv = nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    links.new(ns.outputs["Green"], inv.inputs[1])
    comb = nodes.new("ShaderNodeCombineColor")
    links.new(ns.outputs["Red"], comb.inputs["Red"])
    links.new(inv.outputs[0], comb.inputs["Green"])
    links.new(ns.outputs["Blue"], comb.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.42
    links.new(comb.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def simple_material(name, color, roughness, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metal
    return mat


M_BAMBOO = image_material("M_Yumi_PhotographedBamboo", (0.90, 0.77, 0.62), 0.95)
M_BACK = image_material("M_Yumi_UrushiOverBamboo", (0.25, 0.11, 0.08), 0.58)
M_SIDE = image_material("M_Yumi_VisibleLamination", (0.47, 0.27, 0.15), 1.1)
M_GRIP = image_material("M_Yumi_IndigoGripLeather", (0.32, 0.44, 0.70), 0.96, source=LEATHER)
M_BIND = simple_material("M_Yumi_SmokedSilkBinding", (0.24, 0.15, 0.085), 0.79)
M_HORN = simple_material("M_Yumi_BuffaloHornNocks", (0.048, 0.042, 0.035), 0.31)
M_STRING = simple_material("M_Yumi_HempString", (0.62, 0.52, 0.35), 0.85)
M_SHAFT = image_material("M_Yumi_ArrowBamboo", (0.87, 0.76, 0.59), 1.05)
M_FEATHER = simple_material("M_Yumi_ArrowFletching", (0.48, 0.38, 0.29), 0.94)
M_IRON = simple_material("M_Yumi_ArrowIron", (0.27, 0.29, 0.30), 0.37, 0.82)


def link_editable(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    editable.objects.link(obj)
    obj["provenance"] = "Original SORA Arena project-authored yumi study"
    return obj


def curve_tube(name, points, radius, material, resolution=4):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.bevel_resolution = resolution
    curve.bevel_depth = radius
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1.0)
    obj = bpy.data.objects.new(name, curve)
    editable.objects.link(obj)
    obj.data.materials.append(material)
    obj["provenance"] = "Original SORA Arena project-authored yumi study"
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj.select_set(False)
    return bpy.data.objects[name]


# A strung bow is 2.20 m high; the grip is 0.75 m above the lower nock.
# Source points describe the outward bend in local +X. Local +X points toward
# the FPS target, +Y is lateral and +Z is vertical. The string lies behind it.
PROFILE = [
    (-0.75, 0.035), (-0.68, 0.090), (-0.52, 0.125), (-0.28, 0.075),
    (-0.04, 0.013), (0.00, 0.012), (0.20, 0.045), (0.45, 0.125),
    (0.73, 0.178), (0.96, 0.164), (1.19, 0.098), (1.35, 0.040),
    (1.45, 0.055),
]


def profile_x(z):
    if z <= PROFILE[0][0]:
        return PROFILE[0][1]
    if z >= PROFILE[-1][0]:
        return PROFILE[-1][1]
    i = next(i for i in range(len(PROFILE)-1) if PROFILE[i][0] <= z <= PROFILE[i+1][0])
    a, b = PROFILE[i], PROFILE[i+1]
    before, after = PROFILE[max(0, i-1)], PROFILE[min(len(PROFILE)-1, i+2)]
    t = (z-a[0])/(b[0]-a[0])
    m0 = (b[1]-before[1])/(b[0]-before[0])*(b[0]-a[0])
    m1 = (after[1]-a[1])/(after[0]-a[0])*(b[0]-a[0])
    return (2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*m1


def width(z):
    # The limb is widest around the working regions, with narrow horn tips.
    if z < -0.57:
        return 0.019 + 0.015 * ((z+0.75)/0.18)
    if z > 1.26:
        return 0.019 + 0.016 * ((1.45-z)/0.19)
    return 0.035 + 0.0025*math.cos(2.5*z)


def thickness(z):
    return 0.018 + 0.008*math.exp(-((z-0.04)/0.20)**2)


# Eight-sided sections create a softly beveled stave; longitudinal rings give
# the limbs a truly asymmetric silhouette and material zones remain editable.
verts, faces, face_mats, uv_faces = [], [], [], []
ring_shape = [(-0.50,-0.35), (-0.40,-0.50), (0.40,-0.50), (0.50,-0.35),
              (0.50,0.35), (0.40,0.50), (-0.40,0.50), (-0.50,0.35)]
rings = 111
for j in range(rings):
    z = -0.75 + 2.20*j/(rings-1)
    x = profile_x(z)
    w, d = width(z), thickness(z)
    for dx, dy in ring_shape:
        verts.append((x+dx*d, dy*w, z))
for j in range(rings-1):
    for k in range(8):
        nxt=(k+1)%8
        faces.append((j*8+k,j*8+nxt,(j+1)*8+nxt,(j+1)*8+k))
        # Broad exposed belly, lacquered back and visible laminated edges.
        face_mats.append(0 if k in (0,7) else 1 if k in (3,4) else 2)
        a=j/(rings-1)*2.2
        b=(j+1)/(rings-1)*2.2
        uv_faces.append(((a,k/8),(a,(k+1)/8),(b,(k+1)/8),(b,k/8)))
faces.extend([tuple(reversed(tuple(range(8)))),tuple((rings-1)*8+k for k in range(8))])
face_mats.extend([2,2])
uv_faces.extend([tuple((k/8,0.0) for k in reversed(range(8))),tuple((k/8,1.0) for k in range(8))])
mesh=bpy.data.meshes.new("Asymmetric_LaminatedStave_Mesh")
mesh.from_pydata(verts,[],faces)
mesh.update()
stave=bpy.data.objects.new("Asymmetric_LaminatedStave_220cm",mesh)
editable.objects.link(stave)
stave["provenance"]="Original SORA Arena project-authored yumi study"
for mat in (M_BAMBOO,M_BACK,M_SIDE):mesh.materials.append(mat)
uv=mesh.uv_layers.new(name="UV0")
for poly, mi, coords in zip(mesh.polygons,face_mats,uv_faces):
    poly.material_index=mi
    poly.use_smooth=True
    for li,coord in zip(poly.loop_indices,coords):uv.data[li].uv=coord

# Fine laminating glue lines have geometry depth, which survives grazing
# first-person light. The side edge line follows each curved limb.
for side in (-1,1):
    points=[]
    for i in range(90):
        z=-0.65+2.0*i/89
        points.append((profile_x(z),side*(width(z)*0.505),z))
    curve_tube(f"LaminationEdge_{side}",points,0.00075,M_SIDE,2)

# The tsuka surface is a separate close-fitting leather sleeve so its dark
# body, raised edges and braid read correctly even at first-person distance.
grip_verts,grip_faces,grip_uv=[],[],[]
for j in range(17):
    z=-.13+.26*j/16
    x=profile_x(z)
    for dx,dy in ring_shape:
        grip_verts.append((x+dx*(thickness(z)+.004),dy*(width(z)+.005),z))
for j in range(16):
    for k in range(8):
        grip_faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
        grip_uv.append(((k/8,j/16*.72),((k+1)/8,j/16*.72),
                        ((k+1)/8,(j+1)/16*.72),(k/8,(j+1)/16*.72)))
grip_mesh=bpy.data.meshes.new("LeatherGrip_Mesh")
grip_mesh.from_pydata(grip_verts,[],grip_faces)
grip_mesh.update()
grip=bpy.data.objects.new("Tsuka_LeatherSleeve",grip_mesh)
editable.objects.link(grip)
grip_mesh.materials.append(M_GRIP)
grip["provenance"]="Original SORA Arena project-authored yumi study"
guv=grip_mesh.uv_layers.new(name="UV0")
for poly, coords in zip(grip_mesh.polygons,grip_uv):
    for li,coord in zip(poly.loop_indices,coords):guv.data[li].uv=coord
for label,z0,z1 in (("Lower",-.126,-.035),("Upper",.045,.126)):
    wrap=[]
    for i in range(161):
        z=z0+(z1-z0)*i/160
        theta=2*math.pi*10*i/160
        # Project the cord onto the sleeve's rectangular circumference.
        c,s=math.cos(theta),math.sin(theta)
        norm=max(abs(c),abs(s))
        x=profile_x(z)+0.53*(thickness(z)+.004)*c/norm
        y=0.53*(width(z)+.005)*s/norm
        wrap.append((x,y,z))
    curve_tube(f"Tsuka_Grip_SilkCord_{label}",wrap,0.0012,M_BIND,3)
for side in (-1,1):
    curve_tube(f"LeatherGripSeam_{side}",
               [(profile_x(z)+0.009,side*0.018,z) for z in (-.13,-.10,0,.10,.13)],
               0.0012,M_GRIP,2)

# Small inlaid clan marker, cut from the user's exact vector rather than a
# redrawn approximated emblem. It sits on the player's near side of the grip.
before=set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(LOGO))
logo_curves=[o for o in set(bpy.data.objects)-before if o.type=="CURVE"]
assert len(logo_curves)==2,[o.name for o in logo_curves]
corners=[o.matrix_world@Vector(c) for o in logo_curves for c in o.bound_box]
lo_x,hi_x=min(v.x for v in corners),max(v.x for v in corners)
lo_y,hi_y=min(v.y for v in corners),max(v.y for v in corners)
origin=((lo_x+hi_x)/2,(lo_y+hi_y)/2)
scale=.022/max(hi_x-lo_x,hi_y-lo_y)
for index,o in enumerate(logo_curves):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target="MESH")
    o=bpy.context.object
    for vert in o.data.vertices:
        p=o.matrix_world@vert.co
        vert.co=(profile_x(.012)+(p.x-origin[0])*scale,
                 -.5*(width(.012)+.005)-.0013,.012+(p.y-origin[1])*scale)
    o.matrix_world.identity()
    link_editable(o)
    o.name=f"UserSupplied_SORAKamon_Grip_Path_{index}"
    o.data.materials.clear()
    o.data.materials.append(M_HORN)
    o["source_svg_sha256"]=LOGO_RECORD["source_sha256"]

# Horn nocks and hemp tsuru are independent geometry for later draw animation.
for label,z,sgn in (("Shimohazu",-0.75,-1),("Urahazu",1.45,1)):
    x=profile_x(z)
    curve_tube(label+"_HornCap",[(x+0.002*math.sin(t*math.pi),0,z+sgn*t*0.034)
                                for t in [i/12 for i in range(13)]],0.006,M_HORN,4)
    curve_tube(label+"_StringLoop",[(x-0.008-0.009*math.sin(t*math.pi),
                                      0.004*math.cos(t*math.pi),z+sgn*(0.007+0.013*t))
                                     for t in [i/12 for i in range(13)]],0.0014,M_STRING,3)
curve_tube("Tsuru_Hemp_Unreleased",[
    (profile_x(-.75)-0.012,0,-.75),(-.109,0,-.32),(-.120,0,0.0),
    (-.101,0,.48),(-.075,0,1.00),(profile_x(1.45)-.012,0,1.45)],
           0.0014,M_STRING,3)

# Straight ya with rear feathering and a narrow forged-iron leaf point.
shaft_z=0.055
curve_tube("Ya_BambooShaft_98cm",[(x,0.040,shaft_z) for x in [-0.27,-0.10,0.2,0.6,0.71]],
           0.0041,M_SHAFT,5)
curve_tube("Ya_NockBinding",[(-.268+0.012*i/10,0.040,shaft_z) for i in range(11)],
           0.0045,M_BIND,4)
for side in (-1,0,1):
    theta=side*2.09
    points=[]
    for i in range(17):
        x=-.22+.14*i/16
        lift=0.018*math.sin(math.pi*i/16)
        points.append((x,0.040+lift*math.cos(theta),shaft_z+lift*math.sin(theta)))
    curve_tube(f"Ya_Feather_Rachis_{side}",points,0.0009,M_FEATHER,2)
    for i in range(13):
        x=-.215+.125*i/12
        rise=.017*math.sin(math.pi*i/12)
        p0=(x,0.040+rise*.45*math.cos(theta),shaft_z+rise*.45*math.sin(theta))
        p1=(x-.007,0.040+rise*math.cos(theta),shaft_z+rise*math.sin(theta))
        curve_tube(f"Ya_Feather_Barb_{side}_{i:02d}",[p0,p1],0.00042,M_FEATHER,1)
point_mesh=bpy.data.meshes.new("Ya_IronArrowhead_Mesh")
point_mesh.from_pydata([(0.698,0.034,shaft_z),(0.698,0.046,shaft_z),
                        (0.698,0.040,shaft_z-0.006),(0.698,0.040,shaft_z+0.006),
                        (0.766,0.040,shaft_z)],[],
                       [(0,2,4),(2,1,4),(1,3,4),(3,0,4),(0,3,1,2)])
point_mesh.update()
point=bpy.data.objects.new("Ya_ForgedIronHead",point_mesh)
editable.objects.link(point)
point_mesh.materials.append(M_IRON)
point["provenance"]="Original SORA Arena project-authored yumi study"

for obj in editable.objects:
    if obj.type=="MESH":
        obj.select_set(True)
bpy.context.view_layer.objects.active=stave
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,apply_unit_scale=True,
                         object_types={"MESH"},mesh_smooth_type="FACE",use_mesh_modifiers=True,
                         bake_space_transform=False,add_leaf_bones=False,axis_forward="-Y",axis_up="Z")
bpy.ops.object.select_all(action="DESELECT")

world=bpy.data.worlds.new("Studio_RakingSoftbox")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.11,.13,.15,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.6
scene.render.engine="CYCLES"
scene.cycles.samples=48
scene.render.resolution_x=1200
scene.render.resolution_y=1500
scene.render.resolution_percentage=100
scene.view_settings.view_transform="AgX"


def area(name,loc,power,size,color):
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power
    data.shape="DISK"
    data.size=size
    data.color=color
    obj=bpy.data.objects.new(name,data)
    review.objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(Vector((0,0,.28))-obj.location).to_track_quat("-Z","Y").to_euler()


area("LargeKey",(2.0,-2.0,2.8),580,2.4,(1,.89,.77))
area("LongRim",(-1.3,1.5,1.5),340,1.7,(.76,.86,1))


def shoot(path,loc,target,lens):
    camera=bpy.data.cameras.new("StudyCamera")
    obj=bpy.data.objects.new("StudyCamera",camera)
    review.objects.link(obj)
    scene.camera=obj
    obj.location=loc
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    camera.type="ORTHO"
    camera.ortho_scale=lens
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj,do_unlink=True)


shoot(RENDER,(2.3,-3.0,1.3),(0.0,0.0,.34),2.68)
shoot(SIDE,(2.5,-0.0,.44),(0.0,0.0,.35),2.58)
shoot(DETAIL,(.65,-.90,.40),(.10,0.0,.02),.70)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest={
    "schema_version":1,
    "name":"SM_Nyaagyu_Yumi_Study",
    "status":"source_only_visual_candidate",
    "generator":"scripts/art/create_nyaagyu_yumi_study.py",
    "generator_sha256":digest(ROOT/"scripts/art/create_nyaagyu_yumi_study.py"),
    "units":"metres",
    "bow_height_m":2.20,
    "grip_height_from_lower_nock_m":0.75,
    "historic_accuracy":"shape and materials informed by living bowmaking guidance; not a replica or fitting certification",
    "source_blend":BLEND.name,"source_blend_sha256":digest(BLEND),
    "source_fbx":FBX.name,"source_fbx_sha256":digest(FBX),
    "renders":[{"file":p.name,"sha256":digest(p)} for p in (RENDER,SIDE,DETAIL)],
    "textures":[{"surface":name,"channel":ch,"file":"Textures/"+fn,"md5":md5,
                 "sha256":digest(TEX/fn),"url":f"https://dl.polyhaven.org/file/ph-assets/Textures/{Path(fn).suffix[1:]}/2k/{asset}/{fn}"}
                for name,asset,surface in (("bamboo","bamboo_veneer",SCAN),
                                           ("leather","brown_leather",LEATHER))
                for ch,(fn,md5) in surface.items()],
    "texture_sources":["https://polyhaven.com/a/bamboo_veneer",
                       "https://polyhaven.com/a/brown_leather"],
    "texture_license":"CC0-1.0",
    "texture_license_url":"https://polyhaven.com/license",
    "kamon_source":"Content/SourceArt/UI/sora_logo_NOtext2.svg",
    "kamon_source_sha256":LOGO_RECORD["source_sha256"],
    "reference_urls":["https://www.kyudo.com/kyudo-l.html","https://kyudo.com/asahiam-buybow.html"],
    "runtime_integrated":False,
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_YUMI_STUDY_READY",len(editable.objects),len(stave.data.vertices))
