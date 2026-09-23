"""Build editable, source-only Nyaakoto first-person paw and kote grip studies.

Run from the repository root:
    blender -b --factory-startup --python scripts/art/create_nyaakoto_first_person_paws.py

Metres. +Z is a weapon's handle axis in the canonical paw construction.
The actual existing sword and yumi meshes are appended into review-only
collections, so hand contact is inspected against the project's real sources.
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
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws"
TEX = OUT / "Textures"
HERO_PBR = ROOT / "Content/SourceArt/Characters/Hero/PBR"
SWORD_SOURCE = ROOT / "Content/SourceArt/Nyaagyu_HeroKatana.blend"
BOW_SOURCE = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/Nyaagyu_Yumi_Study.blend"
OUT.mkdir(parents=True, exist_ok=True)
PAD_RECORD = json.loads((TEX / "manifest.json").read_text())
for item in PAD_RECORD["maps"].values():
    assert hashlib.sha256((TEX / item["file"]).read_bytes()).hexdigest() == item["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


def collection(name):
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    return c


construction = collection("Construction_Editable_Hidden")
katana_paws = collection("Katana_Paws_Editable")
yumi_paw = collection("Yumi_Paw_Editable")
katana_prop = collection("Review_Only_ExistingKatana")
yumi_prop = collection("Review_Only_ExistingYumi")
review_rig = collection("Review_Only_CamerasAndLights")
construction.hide_render = True
construction.hide_viewport = True


def load_map(root, surface, channel):
    path = root / f"T_Nyaakoto_{surface}_{channel}.png"
    assert path.is_file(), path
    node_image = bpy.data.images.load(str(path), check_existing=True)
    node_image.colorspace_settings.name = "sRGB" if channel == "Albedo" else "Non-Color"
    return node_image


def basic_material(name, color, roughness, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    return m


def texture_material(name, root, surface, tint=(1, 1, 1), roughness_scale=1, metal=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    n, links = m.node_tree.nodes, m.node_tree.links
    bsdf = n.get("Principled BSDF")
    images = {}
    if surface.startswith("fur_"):
        # Object-space box projection avoids visible smart-UV islands on a
        # rounded remeshed paw. UV0 remains authored for later Unreal baking.
        coords=n.new("ShaderNodeTexCoord")
        scale=n.new("ShaderNodeVectorMath")
        scale.operation="SCALE"
        scale.inputs[3].default_value=10.0
        links.new(coords.outputs["Object"],scale.inputs[0])
    for channel in ("Albedo", "NormalDX", "ORM"):
        node = n.new("ShaderNodeTexImage")
        node.name = f"Source_{surface}_{channel}"
        node.image = load_map(root, surface, channel)
        if surface.startswith("fur_"):
            node.projection="BOX"
            node.projection_blend=.35
            links.new(scale.outputs["Vector"],node.inputs["Vector"])
        images[channel] = node
    multiply = n.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    multiply.inputs[2].default_value = (*tint, 1)
    links.new(images["Albedo"].outputs["Color"], multiply.inputs[1])
    links.new(multiply.outputs["Color"], bsdf.inputs["Base Color"])
    split = n.new("ShaderNodeSeparateColor")
    links.new(images["ORM"].outputs["Color"], split.inputs["Color"])
    r_scale = n.new("ShaderNodeMath")
    r_scale.operation = "MULTIPLY"
    r_scale.inputs[1].default_value = roughness_scale
    links.new(split.outputs["Green"], r_scale.inputs[0])
    links.new(r_scale.outputs[0], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = metal
    # The stored normal maps use the Unreal/DirectX green convention.
    ns = n.new("ShaderNodeSeparateColor")
    links.new(images["NormalDX"].outputs["Color"], ns.inputs["Color"])
    invert = n.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    links.new(ns.outputs["Green"], invert.inputs[1])
    combine = n.new("ShaderNodeCombineColor")
    for c in ("Red", "Blue"):
        links.new(ns.outputs[c], combine.inputs[c])
    links.new(invert.outputs[0], combine.inputs["Green"])
    normal = n.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.45
    links.new(combine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return m


M_FUR = texture_material("M_FP_Paw_FurWhite", HERO_PBR, "fur_white", (0.75, 0.74, 0.72))
M_FUR_GREY = texture_material("M_FP_Paw_FurGrey", HERO_PBR, "fur_grey", (0.78, 0.78, 0.76))
M_CLOTH = texture_material("M_FP_Kote_IndigoSilk", HERO_PBR, "silk_indigo", (.012, .018, .041), 1.15)
M_LACQUER = texture_material("M_FP_Kote_OxbloodLacquer", HERO_PBR, "lacquer_oxblood", (.090, .008, .017), .95)
M_PAD = texture_material("M_FP_PawPad_OriginalPBR", TEX, "PawPad", (1, 1, 1))
M_CLAW = basic_material("M_FP_TranslucentIvoryClaw", (.58, .52, .41), .38)
M_CORD = basic_material("M_FP_SmokedIndigoLacing", (.055, .066, .083), .68)
M_TRIM = basic_material("M_FP_WornIronFuchi", (.11, .115, .12), .5, .78)


def move_to(obj, target):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    target.objects.link(obj)
    return obj


def ellipsoid(name, position, scale, material, target=construction, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         location=position)
    obj = move_to(bpy.context.object, target)
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(material)
    return obj


def swept_tube(name, centers, radii, material, target=construction, sides=12):
    """Varying-radius closed tube, with ring frames perpendicular to tangent."""
    v, f, uv = [], [], []
    for i, point in enumerate(centers):
        t = Vector(centers[min(i + 1, len(centers)-1)]) - Vector(centers[max(0, i-1)])
        t.normalize()
        seed = Vector((0, 0, 1)) if abs(t.z) < .85 else Vector((0, 1, 0))
        n = t.cross(seed).normalized()
        b = t.cross(n).normalized()
        for s in range(sides):
            a = 2 * math.pi * s / sides
            v.append(Vector(point) + radii[i] * (math.cos(a) * n + math.sin(a) * b))
    for i in range(len(centers)-1):
        for s in range(sides):
            sn = (s+1) % sides
            f.append((i*sides+s, i*sides+sn, (i+1)*sides+sn, (i+1)*sides+s))
            uv.append(((s/sides, i/(len(centers)-1)), (sn/sides, i/(len(centers)-1)),
                       (sn/sides, (i+1)/(len(centers)-1)), (s/sides, (i+1)/(len(centers)-1))))
    f.extend([tuple(reversed(range(sides))), tuple((len(centers)-1)*sides+s for s in range(sides))])
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(v, [], f)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name="UV0")
    for poly, coords in zip(mesh.polygons, uv):
        poly.use_smooth = True
        for li, coord in zip(poly.loop_indices, coords):
            layer.data[li].uv = coord
    for poly in list(mesh.polygons)[-2:]:
        poly.use_smooth = True
    return obj


def cubic(control, steps=20):
    p0, p1, p2, p3 = [Vector(x) for x in control]
    return [tuple((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t*t*p2 + t**3*p3)
            for t in (j/steps for j in range(steps+1))]


def loft_x(name, x0, x1, ry0, ry1, rz0, rz1, material, target, rings=18, sides=24):
    v, f = [], []
    for j in range(rings):
        u = j/(rings-1)
        x = x0*(1-u)+x1*u
        ry = ry0*(1-u)+ry1*u
        rz = rz0*(1-u)+rz1*u
        for k in range(sides):
            a = 2*math.pi*k/sides
            v.append((x, ry*math.sin(a), rz*math.cos(a)))
    for j in range(rings-1):
        for k in range(sides):
            n = (k+1)%sides
            f.append((j*sides+k,j*sides+n,(j+1)*sides+n,(j+1)*sides+k))
    f.extend([tuple(reversed(range(sides))), tuple((rings-1)*sides+k for k in range(sides))])
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(v, [], f)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="UV0")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vertex_index = mesh.loops[li].vertex_index
            ring, side = divmod(vertex_index, sides)
            uv.data[li].uv = (side/sides, ring/(rings-1))
    return obj


def sculpt_paw_body():
    parts = [
        ellipsoid("Palm_AnatomicalMass", (.058, 0, 0), (.049, .038, .048), M_FUR),
        ellipsoid("Carpal_Transition", (.111, 0, -.002), (.052, .033, .037), M_FUR),
    ]
    # Each digit curls around the weapon rather than forming a mitten silhouette.
    # Distinct third-phalange tapers and contact-pad positions survive remeshing.
    z_levels = (-.032, -.011, .012, .032)
    for i, z in enumerate(z_levels):
        y = (-.014, -.020, -.018, -.010)[i]
        points = cubic(((.049,y,z),(.024,y-.015,z),(-.002,y-.022,z+.002),(-.016,-.012,z+.004)), 25)
        radii = [max(.004, .012*(1-u*.40) + .0012*math.sin(math.pi*u))
                 for u in (j/25 for j in range(26))]
        parts.append(swept_tube(f"Digit_{i+1}_ThreePhalangeSweep", points, radii, M_FUR))
    dew = cubic(((.067,.021,.045),(.046,.041,.060),(.011,.039,.054),(.002,.022,.040)), 20)
    parts.append(swept_tube("Dewclaw_OpposingDigit", dew,
                            [.011-.005*j/20 for j in range(21)], M_FUR))

    # Preserve named construction pieces; only copies are fused for the visible
    # smooth body. The cage can be adjusted and regenerated without destroying
    # the source dimensions.
    copies = []
    for obj in parts:
        o = obj.copy()
        o.data = obj.data.copy()
        katana_paws.objects.link(o)
        copies.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in copies:
        o.select_set(True)
    bpy.context.view_layer.objects.active = copies[0]
    bpy.ops.object.join()
    body = copies[0]
    body.name = "Paw_SculptedContinuousBody"
    # The first source mass retains its display scale because the hidden
    # construction collection is not transform-applied by Blender's operator.
    # Apply after joining, or a 1.6 mm voxel becomes ~0.08 mm in world space.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    remesh = body.modifiers.new("Fuse anatomical masses", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = .0016
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    print("PAW_BODY_REMESH_FACES",len(body.data.polygons),flush=True)
    smooth = body.modifiers.new("Soften remesh ridges", "SMOOTH")
    smooth.factor = 1.1
    smooth.iterations = 5
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    for p in body.data.polygons:
        p.use_smooth = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=.015)
    bpy.ops.object.mode_set(mode="OBJECT")
    body.data.uv_layers.active.name = "UV0"
    body["source_anatomy_parts"] = ",".join(o.name for o in parts)
    body["grip_axis"] = "+Z"
    body["metres_per_unit"] = 1.0
    return body


def make_kote_plate(name, x, angle0=-1.35, angle1=-.35):
    v, f = [], []
    steps=10
    for j in range(5):
        fx = j/4
        xx=x-.027+.054*fx
        sleeve_u=(xx-.116)/(.341-.116)
        ry=.035+.015*sleeve_u+.0025
        rz=.037+.014*sleeve_u+.0025
        for k in range(steps):
            a=angle0+(angle1-angle0)*k/(steps-1)
            rr=1+.015*math.sin(math.pi*fx)
            v.append((xx,ry*math.sin(a)*rr,-rz*math.cos(a)*rr))
    for j in range(4):
        for k in range(steps-1):
            f.append((j*steps+k,j*steps+k+1,(j+1)*steps+k+1,(j+1)*steps+k))
    mesh=bpy.data.meshes.new(name+"_Mesh")
    mesh.from_pydata(v,[],f)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    katana_paws.objects.link(obj)
    mesh.materials.append(M_LACQUER)
    solid=obj.modifiers.new("ForgedPlateThickness","SOLIDIFY")
    solid.thickness=.0018
    bev=obj.modifiers.new("SoftForgedEdges","BEVEL")
    bev.width=.0012
    bev.segments=2
    uv=mesh.uv_layers.new(name="UV0")
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            ix=mesh.loops[li].vertex_index
            uv.data[li].uv=((ix%steps)/(steps-1), (ix//steps)/4)
    return obj


def make_details():
    objs=[]
    sleeve=loft_x("Kote_IndigoClothSleeve",.116,.341,.035,.050,.037,.051,M_CLOTH,katana_paws)
    objs.append(sleeve)
    cuff=loft_x("Kote_FurTransitionCuff",.115,.143,.038,.040,.039,.041,M_CORD,katana_paws,8)
    objs.append(cuff)
    for i, px in enumerate((.174,.236,.298)):
        objs.append(make_kote_plate(f"Kote_LacqueredIronLamella_{i+1}",px))
        for side in (-1,1):
            # Ties pass visibly through the plates and cloth, not painted lines.
            a = -.85+side*.35
            sleeve_u=(px-.116)/(.341-.116)
            ry=.035+.015*sleeve_u+.0045
            rz=.037+.014*sleeve_u+.0045
            cord = swept_tube(f"Kote_SilkTie_{i+1}_{side}",
                [((px-.013)+.026*t/10,
                  ry*math.sin(a)+.002*math.sin(t*math.pi/10),
                  -rz*math.cos(a)-.002*math.sin(t*math.pi/10))
                 for t in range(11)],
                [.0012]*11,M_CORD,katana_paws,8)
            objs.append(cord)
    for x in (.143,.340):
        points=[(x,.041*math.sin(2*math.pi*k/40),.042*math.cos(2*math.pi*k/40))
                for k in range(41)]
        objs.append(swept_tube(f"Kote_IronHem_{x:.3f}",points,[.0018]*41,M_TRIM,katana_paws,8))

    # Distinct distal pads and subtle, partly retracted claws. They are separate
    # editable surfaces and do not inherit the furry material.
    pad_centres=[]
    for i,z in enumerate((-.028,-.007,.016,.036)):
        p=ellipsoid(f"DigitalPad_{i+1}",(-.019,-.009,z+.004),(.008,.007,.008),M_PAD,katana_paws)
        pad_centres.append(tuple(p.location))
        objs.append(p)
        claw=swept_tube(f"RetractileClaw_{i+1}",
            [(-.019,-.007,z+.004),(-.022,-.004,z+.006),(-.024,-.002,z+.005),(-.025,.001,z+.003)],
            [.0024,.0020,.0011,.00024],M_CLAW,katana_paws,10)
        objs.append(claw)
    pad=ellipsoid("CentralMetacarpalPad",(.014,-.034,-.005),(.018,.004,.023),M_PAD,katana_paws)
    objs.append(pad)
    dewpad=ellipsoid("DewclawContactPad",(.004,.024,.041),(.006,.004,.007),M_PAD,katana_paws)
    objs.append(dewpad)

    rng=random.Random(741823)
    # Geometry tufts interrupt the glove-like sleeve/paw boundary. A successor
    # needs a groom/card atlas and authored LODs for production use.
    for i in range(48):
        a=2*math.pi*(i+rng.random()*.35)/48
        d=rng.uniform(.005,.010)
        yy=.037*math.sin(a)
        zz=.039*math.cos(a)
        points=[(.129,yy,zz),(.123-d*.4,yy*1.045,zz*1.045),(.125-d,yy*1.11,zz*1.11)]
        tuft=swept_tube(f"FurWristTuft_{i:02d}",points,[.0010,.0007,.00010],
                         M_FUR_GREY if i%4==0 else M_FUR,katana_paws,5)
        objs.append(tuft)
    return objs, pad_centres


body=sculpt_paw_body()
details, pad_centres=make_details()
canonical=[body,*details]
for obj in canonical:
    obj["provenance"]="Original SORA Arena editable first-person Nyaakoto paw/kote study"
    obj["runtime_status"]="source-only; photoreal gate failed pending packaged A/B"


def duplicate_paw(prefix, target, transform):
    output=[]
    for src in canonical:
        obj=src.copy()
        obj.data=src.data.copy()
        target.objects.link(obj)
        obj.name=prefix+"_"+src.name
        obj.matrix_world=transform @ src.matrix_world
        output.append(obj)
    return output


# Local +Z grip axis rotates to the actual sword's +X tsuka axis.
rot=Matrix.Rotation(math.pi/2,4,"Y")
right=Matrix.Translation(Vector((-.095,-.012,0))) @ Matrix.Rotation(math.radians(-9),4,"X") @ rot
left=Matrix.Translation(Vector((-.215,.028,0))) @ Matrix.Rotation(math.radians(14),4,"X") @ rot
left_objects=duplicate_paw("LeftSupport",katana_paws,left)
# Bow's grip is 1.2 cm forward of stave origin and 75 cm above its lower tip.
bow_transform=Matrix.Translation(Vector((2.012,0,0)))
bow_objects=duplicate_paw("BowLeft",yumi_paw,bow_transform)
for obj in canonical:
    obj.matrix_world=right @ obj.matrix_world


def append_review_objects(path, target, select):
    with bpy.data.libraries.load(str(path), link=False) as (source, dest):
        dest.objects=[name for name in source.objects if select(name)]
    objs=[]
    for obj in dest.objects:
        if obj is None or obj.type!="MESH":
            continue
        target.objects.link(obj)
        obj.name="ReviewOnly_"+obj.name
        obj["review_only"] = True
        objs.append(obj)
    return objs


sword_objects=append_review_objects(
    SWORD_SOURCE,katana_prop,
    lambda n: not n.startswith(("Preview_","Saya_","Koiguchi_","Kojiri_","Kurikata_","Sageo_")))
bow_props=append_review_objects(
    BOW_SOURCE,yumi_prop,
    lambda n: any(s in n for s in ("Stave","Lamination","Tsuka_","LeatherGrip","Kamon","String","Nocked","Arrow","Ya_","Shimohazu","Urahazu")))
for obj in bow_props:
    obj.location.x+=2.0


def aim(obj, point):
    obj.rotation_euler=(Vector(point)-obj.location).to_track_quat("-Z","Y").to_euler()


def camera(name, loc, target, ortho):
    data=bpy.data.cameras.new(name)
    obj=bpy.data.objects.new(name,data)
    review_rig.objects.link(obj)
    obj.location=loc
    aim(obj,target)
    data.type="ORTHO"
    data.ortho_scale=ortho
    data.lens=55
    return obj


cam_sword=camera("Camera_KatanaFirstPerson",(-.27,-.52,.205),(-.105,0,-.105),.65)
cam_sword_detail=camera("Camera_KatanaContact",(-.18,-.29,.14),(-.15,0,-.005),.31)
cam_bow=camera("Camera_YumiFirstPerson",(2.45,-.45,.13),(2.012,0,0),.49)
cam_bow_detail=camera("Camera_YumiContact",(2.21,-.29,.11),(2.012,0,0),.28)


def area(name, location, target, energy, size, color):
    data=bpy.data.lights.new(name,"AREA")
    obj=bpy.data.objects.new(name,data)
    review_rig.objects.link(obj)
    obj.location=location
    aim(obj,target)
    data.energy=energy
    data.shape="DISK"
    data.size=size
    data.color=color
    return obj


area("LargeWarmKey",(-.2,-.4,.7),(.8,0,0),125,1.2,(1,.91,.80))
area("CoolLongFill",(1.0,.45,.50),(.8,0,0),85,1.7,(.68,.80,1))
area("WarmRim",(1.1,.05,.75),(.8,0,0),145,.9,(1,.82,.72))
scene.world.color=(.075,.08,.09)
scene.render.engine="CYCLES"
scene.cycles.samples=28
scene.cycles.use_denoising=True
scene.render.resolution_x=1280
scene.render.resolution_y=960
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"


def save_render(path,camera_obj,hide):
    katana_paws.hide_render = hide=="katana"
    katana_prop.hide_render = hide=="katana"
    yumi_paw.hide_render = hide=="yumi"
    yumi_prop.hide_render = hide=="yumi"
    scene.camera=camera_obj
    scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


blend=OUT/"Nyaakoto_FirstPersonPaws_GripStudy.blend"
scene.camera=cam_sword
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
save_render(OUT/"Nyaakoto_KatanaGrip_FirstPerson.png",cam_sword,"yumi")
save_render(OUT/"Nyaakoto_KatanaGrip_Contact.png",cam_sword_detail,"yumi")
save_render(OUT/"Nyaakoto_YumiGrip_FirstPerson.png",cam_bow,"katana")
save_render(OUT/"Nyaakoto_YumiGrip_Contact.png",cam_bow_detail,"katana")


def export_meshes(path, objects, offset):
    old_matrices=[obj.matrix_world.copy() for obj in objects]
    if offset:
        for obj in objects:
            obj.matrix_world=Matrix.Translation(Vector((offset,0,0))) @ obj.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={"MESH"},
        global_scale=1.0,apply_unit_scale=True,axis_forward="-Y",axis_up="Z",
        bake_space_transform=False,path_mode="RELATIVE",add_leaf_bones=False)
    for obj in objects:
        obj.select_set(False)
    for obj,matrix in zip(objects,old_matrices):
        obj.matrix_world=matrix


export_meshes(OUT/"SM_Nyaakoto_KatanaPaws_GripStudy.fbx",canonical+left_objects,0)
export_meshes(OUT/"SM_Nyaakoto_YumiPaw_GripStudy.fbx",bow_objects,-2)

manifest={
    "schema_version":1,
    "status":"source-only art candidate; no runtime binding",
    "units":"metres",
    "generator":"scripts/art/create_nyaakoto_first_person_paws.py",
    "mesh_sources":"Project-authored parametric/voxel sculpt; no third-party mesh",
    "existing_review_props":[str(SWORD_SOURCE.relative_to(ROOT)),str(BOW_SOURCE.relative_to(ROOT))],
    "source_sha256":{
        str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (SWORD_SOURCE,BOW_SOURCE)
    },
    "original_paw_pad_maps":str((TEX/"manifest.json").relative_to(ROOT)),
    "reused_project_pbr":str(HERO_PBR.relative_to(ROOT)),
    "reused_project_pbr_sha256":{
        p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for surface in ("fur_white","fur_grey","silk_indigo","lacquer_oxblood")
        for channel in ("Albedo","NormalDX","ORM")
        for p in (HERO_PBR/f"T_Nyaakoto_{surface}_{channel}.png",)
    },
    "weapon_contact":{
        "katana_handle_centres_m":[-.095,-.215],
        "katana_handle_axis":"+X",
        "yumi_grip_centre_m":[.012,0,0],
        "yumi_grip_axis":"+Z",
        "canonical_digital_pad_centres_m":pad_centres,
        "nominal_handle_radius_m":.022,
    },
    "outputs":{},
}
for p in (blend,OUT/"SM_Nyaakoto_KatanaPaws_GripStudy.fbx",
          OUT/"SM_Nyaakoto_YumiPaw_GripStudy.fbx",
          *sorted(OUT.glob("Nyaakoto_*Grip_*.png"))):
    manifest["outputs"][p.name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps({"blend":str(blend),"paw_objects":len(canonical)+len(left_objects)+len(bow_objects),
                  "review_props":len(sword_objects)+len(bow_props)}))
