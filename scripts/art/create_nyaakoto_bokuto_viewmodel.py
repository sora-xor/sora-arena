"""Build a source-only, articulated Nyaakoto paw study around the real bokuto.

Run from the repository root with Blender 5.2.2 LTS. All model coordinates are
metres in the playable weapon's local frame: +X is the bokuto axis, +Z is up.
The review cameras use the *unchanged* idle WeaponRoot transform. The normal
view is an approximation of Unreal's native first-person projection, not a
substitute for a packaged game capture.
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
OUT = ROOT / "Content/SourceArt/Characters/NyaakotoBokutoViewmodel"
HERO = ROOT / "Content/SourceArt/Characters/Hero/PBR"
PAD = ROOT / "Content/SourceArt/Characters/NyaakotoFirstPersonPaws/Textures"
BOKUTO = ROOT / "Content/SourceArt/Weapons/DojoBokutoForm"
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "Nyaakoto_BokutoPaws.blend"
FBX = OUT / "SK_Nyaakoto_BokutoPaws_SourceOnly.fbx"
MANIFEST = OUT / "manifest.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


hero_record = json.loads((HERO / "manifest.json").read_text())
pad_record = json.loads((PAD / "manifest.json").read_text())
bokuto_record = json.loads((BOKUTO / "manifest.json").read_text())
assert pad_record["license"].startswith("Original project-owned")
assert bokuto_record["fbx_sha256"] == sha(BOKUTO / bokuto_record["fbx"])
assert bokuto_record["source_texture_manifest_sha256"] == sha(BOKUTO / "texture_manifest.json")
hero_maps = {s["name"]: {m["channel"]: m for m in s["maps"]}
             for s in hero_record["maps"]}
for surface in ("fur_white", "fur_grey", "silk_indigo", "lacquer_oxblood"):
    for item in hero_maps[surface].values():
        assert sha(HERO / item["file"]) == item["sha256"]
for item in pad_record["maps"].values():
    assert sha(PAD / item["file"]) == item["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


def collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


MODEL = collection("Nyaakoto_BokutoPaws_Editable")
PROP = collection("ReviewOnly_RealBokuto")
STUDIO = collection("ReviewOnly_CamerasAndLights")
all_meshes = []
mesh_bones = {}


def load_image(path, color):
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if color else "Non-Color"
    return img


def pbr(name, root, entries, tint=(1, 1, 1), roughness_scale=1.0,
        normal_strength=.48):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*tint, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"
    images = {}
    for channel in ("Albedo", "NormalDX", "ORM"):
        path = root / entries[channel]["file"]
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = f"{channel}_UV0"
        tex.image = load_image(path, channel == "Albedo")
        tex.interpolation = "Linear"
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
        images[channel] = tex
    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    multiply.inputs[2].default_value = (*tint, 1)
    links.new(images["Albedo"].outputs["Color"], multiply.inputs[1])
    links.new(multiply.outputs["Color"], bsdf.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["ORM"].outputs["Color"], split.inputs["Color"])
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = roughness_scale
    links.new(split.outputs["Green"], scale.inputs[0])
    links.new(scale.outputs[0], bsdf.inputs["Roughness"])
    # Existing maps are DirectX convention; Blender's normal node needs +Y.
    nsplit = nodes.new("ShaderNodeSeparateColor")
    links.new(images["NormalDX"].outputs["Color"], nsplit.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    links.new(nsplit.outputs["Green"], invert.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(nsplit.outputs["Red"], combine.inputs["Red"])
    links.new(invert.outputs[0], combine.inputs["Green"])
    links.new(nsplit.outputs["Blue"], combine.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = normal_strength
    links.new(combine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


FUR = pbr("M_Paw_ShortWhiteFur_UV0", HERO, hero_maps["fur_white"],
          (.70, .69, .67), 1.08)
GREY = pbr("M_Paw_GreyGuardFur_UV0", HERO, hero_maps["fur_grey"],
           (.76, .74, .72), 1.04)
SILK = pbr("M_Kote_WornIndigoSilk_UV0", HERO, hero_maps["silk_indigo"],
           (.055, .075, .14), 1.25)
LACQUER = pbr("M_Kote_OxbloodPlate_UV0", HERO, hero_maps["lacquer_oxblood"],
              (.14, .085, .09), 1.02)
PADS = pbr("M_Paw_OriginalPad_UV0", PAD, pad_record["maps"],
           (.48, .43, .42), 1.08)


def solid(name, color, roughness=.65, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


CORD = solid("M_Kote_IndigoLacing", (.040, .051, .073), .75)
IRON = solid("M_Kote_BlackenedIron", (.095, .095, .10), .56, .76)
CLAW = solid("M_Paw_IvoryClaw", (.52, .46, .38), .52)

SORA_LOGO = ROOT / "Content/SourceArt/UI/SORA_Resistance_Logo.png"
SORA_SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SORA_RECORD = json.loads((ROOT / "Content/SourceArt/UI/sora_logo_manifest.json").read_text())
assert sha(SORA_LOGO) == SORA_RECORD["runtime_sha256"]
assert sha(SORA_SVG) == SORA_RECORD["source_sha256"]
KAMON = bpy.data.materials.new("M_Kote_ExactSORAKamon_Enamel")
KAMON.use_nodes = True
kamon_nodes, kamon_links = KAMON.node_tree.nodes, KAMON.node_tree.links
kamon_nodes.clear()
kamon_out = kamon_nodes.new("ShaderNodeOutputMaterial")
kamon_bsdf = kamon_nodes.new("ShaderNodeBsdfPrincipled")
kamon_bsdf.inputs["Roughness"].default_value = .42
kamon_bsdf.inputs["Metallic"].default_value = .18
kamon_links.new(kamon_bsdf.outputs["BSDF"],kamon_out.inputs["Surface"])
kamon_uv = kamon_nodes.new("ShaderNodeUVMap")
kamon_uv.uv_map = "UV0"
kamon_image = kamon_nodes.new("ShaderNodeTexImage")
kamon_image.image = load_image(SORA_LOGO, True)
kamon_links.new(kamon_uv.outputs["UV"],kamon_image.inputs["Vector"])
kamon_mix = kamon_nodes.new("ShaderNodeMixRGB")
kamon_mix.blend_type = "MIX"
kamon_mix.inputs[1].default_value = (.035,.038,.043,1)
kamon_links.new(kamon_image.outputs["Alpha"],kamon_mix.inputs[0])
kamon_links.new(kamon_image.outputs["Color"],kamon_mix.inputs[2])
kamon_links.new(kamon_mix.outputs["Color"],kamon_bsdf.inputs["Base Color"])


def register(obj, bone, anatomical_role):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    MODEL.objects.link(obj)
    obj["anatomical_role"] = anatomical_role
    obj["rig_bone"] = bone
    obj["runtime_status"] = "source-only; not admitted to Unreal gameplay"
    all_meshes.append(obj)
    mesh_bones[obj.name] = bone
    for face in obj.data.polygons:
        face.use_smooth = True
    assert len(obj.data.uv_layers) == 1
    obj.data.uv_layers[0].name = "UV0"
    return obj


def ellipsoid(name, centre, scale, material, bone, role,
              segments=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings,
                                         location=centre)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.data.materials.append(material)
    return register(obj, bone, role)


def sweep(name, points, widths, heights, material, bone, role, sides=12):
    """Editable variable-ellipse sweep with a seam-safe authored UV0."""
    assert len(points) == len(widths) == len(heights) and len(points) > 2
    verts, faces, uv_faces = [], [], []
    for index, point in enumerate(points):
        prev = Vector(points[max(0, index-1)])
        nex = Vector(points[min(len(points)-1, index+1)])
        tangent = (nex-prev).normalized()
        seed = Vector((1, 0, 0)) if abs(tangent.x) < .86 else Vector((0, 0, 1))
        u = tangent.cross(seed).normalized()
        v = tangent.cross(u).normalized()
        for k in range(sides):
            a = math.tau*k/sides
            verts.append(Vector(point) + widths[index]*math.cos(a)*u
                         + heights[index]*math.sin(a)*v)
    count = len(points)
    for i in range(count-1):
        for k in range(sides):
            kn = (k+1) % sides
            faces.append((i*sides+k, i*sides+kn, (i+1)*sides+kn,
                          (i+1)*sides+k))
            uv_faces.append(((k/sides, i/(count-1)),
                             ((k+1)/sides, i/(count-1)),
                             ((k+1)/sides, (i+1)/(count-1)),
                             (k/sides, (i+1)/(count-1))))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((count-1)*sides+k for k in range(sides)))
    for _ in range(2):
        uv_faces.append(tuple((.5+.48*math.cos(math.tau*k/sides),
                               .5+.48*math.sin(math.tau*k/sides))
                              for k in range(sides)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name="UV0")
    for poly, uvs in zip(mesh.polygons, uv_faces):
        for li, uv in zip(poly.loop_indices, uvs):
            layer.data[li].uv = uv
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    MODEL.objects.link(obj)
    return register(obj, bone, role)


def plate(name, h, sign, start, end, bone):
    """One small curved, overlapping lacquer scale over a cloth kote."""
    vertices, faces, coords = [], [], []
    for j in range(4):
        t = j/3
        y = sign*(start*(1-t)+end*t)
        for k in range(7):
            a = (k/6-.5)*math.pi*.63
            x = h + .038*math.sin(a)
            z = -.080 - .39*(abs(y)-.10) + .028*math.cos(a)
            z += .0015*math.sin(math.pi*t)
            vertices.append((x, y, z))
    for j in range(3):
        for k in range(6):
            faces.append((j*7+k, (j+1)*7+k,
                          (j+1)*7+k+1, j*7+k+1))
            coords.append(((k/6,j/3),(k/6,(j+1)/3),
                           ((k+1)/6,(j+1)/3),((k+1)/6,j/3)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(LACQUER)
    uv = mesh.uv_layers.new(name="UV0")
    for poly, face_uv in zip(mesh.polygons, coords):
        for li, coord in zip(poly.loop_indices, face_uv):
            uv.data[li].uv = coord
    obj = bpy.data.objects.new(name, mesh)
    MODEL.objects.link(obj)
    obj = register(obj, bone, "segmented lacquer kote scale")
    solidify = obj.modifiers.new("Scale thickness", "SOLIDIFY")
    solidify.thickness = .0017
    bevel = obj.modifiers.new("Worn scale edges", "BEVEL")
    bevel.width = .0008
    bevel.segments = 2
    return obj


def mounted_kamon(name, centre, bone, radius=.014):
    """A raised iron/enamel disk sewn onto a kote plate, never a screen decal."""
    count = 32
    centre = Vector(centre)
    # The medallion follows the cylindrical sleeve, not a camera-facing plane.
    # At this position its normal is the upper/inner forearm radial direction.
    normal = Vector((0,-.65,.76)).normalized()
    uaxis = Vector((1,0,0))
    vaxis = normal.cross(uaxis).normalized()
    top = centre + .0018*normal
    bottom = centre - .0007*normal
    verts = [top]
    verts.extend(top+radius*(math.cos(math.tau*i/count)*uaxis+
                             math.sin(math.tau*i/count)*vaxis)
                 for i in range(count))
    verts.extend(bottom+radius*(math.cos(math.tau*i/count)*uaxis+
                                math.sin(math.tau*i/count)*vaxis)
                 for i in range(count))
    verts.append(bottom)
    faces, uv_faces = [], []
    for i in range(count):
        nxt = (i+1)%count
        a,b = math.tau*i/count,math.tau*nxt/count
        faces.append((0,1+i,1+nxt))
        uv_faces.append(((.5,.5),(.5+.48*math.cos(a),.5+.48*math.sin(a)),
                         (.5+.48*math.cos(b),.5+.48*math.sin(b))))
        faces.append((1+i,1+count+i,1+count+nxt,1+nxt))
        uv_faces.append(((i/count,1),(i/count,0),((i+1)/count,0),
                         ((i+1)/count,1)))
        faces.append((1+2*count,1+count+nxt,1+count+i))
        uv_faces.append(((.5,.5),(.5+.48*math.cos(b),.5+.48*math.sin(b)),
                         (.5+.48*math.cos(a),.5+.48*math.sin(a))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(KAMON)
    mesh.materials.append(IRON)
    uv = mesh.uv_layers.new(name="UV0")
    for face, face_uv in zip(mesh.polygons,uv_faces):
        face.material_index = 0 if face.index%3 == 0 else 1
        for li,coord in zip(face.loop_indices,face_uv):
            uv.data[li].uv = coord
    obj = bpy.data.objects.new(name,mesh)
    MODEL.objects.link(obj)
    return register(obj,bone,"exact SORA kamon on raised kote medallion")


hands = (
    {"prefix":"R", "h":-.057, "sign":1},
    {"prefix":"L", "h":-.172, "sign":-1},
)
pad_centres = []
rng = random.Random(20260924)
for hand in hands:
    prefix, h, sign = hand["prefix"], hand["h"], hand["sign"]
    forearm, wrist = f"{prefix}_Forearm", f"{prefix}_Wrist"
    # The forearm lies below the tsuka and enters from its own side. Two hands
    # are longitudinally separated, with the near hand closest to the guard.
    centres = [(h-.015,sign*y,z) for y,z in
               ((.078,-.066),(.098,-.078),(.122,-.094),(.151,-.111),
                (.181,-.127),(.211,-.144),(.246,-.158))]
    widths = [.032,.034,.037,.039,.041,.042,.044]
    sweep(f"{prefix}_Kote_ClothSleeve", centres, widths,
          [.031,.033,.035,.037,.039,.041,.042], SILK, forearm,
          "tailored indigo sleeve")
    # Offset ribbing and a narrow wrist border make this layered cloth, rather
    # than a cylindrical glove. The scales remain separate editable geometry.
    for j in range(4):
        start = .125+j*.028
        plate(f"{prefix}_Kote_LacquerScale_{j+1}", h-.015, sign,
              start, start+.033, forearm)
        for side in (-1,1):
            x = h-.015+side*.021
            sweep(f"{prefix}_Kote_ScaleLace_{j+1}_{side}",
                  [(x,sign*(start+.007+t*.004),
                    -.080-.39*(start+.007+t*.004-.10)+.024)
                   for t in range(5)], [.00125]*5,[.00125]*5,
                  CORD, forearm, "scale lacing", 8)
    if prefix == "R":
        mounted_kamon(f"{prefix}_Kote_MountedSORA_Kamon",
                      (h-.015,sign*.142,-.090),forearm)
    # Distinct tapered wrist and carpal masses preserve the digit separation.
    sweep(f"{prefix}_Wrist_FurTransition",
          [(h-.013,sign*.116,-.084),(h-.010,sign*.095,-.066),
           (h-.004,sign*.077,-.051)],
          [.028,.027,.029],[.030,.029,.027],FUR,wrist,"furred wrist")
    ellipsoid(f"{prefix}_Carpal_FurBridge",
              (h-.008,sign*.077,-.052),(.027,.033,.028),FUR,wrist,
              "continuous carpal-to-kote fur transition",18,12)
    ellipsoid(f"{prefix}_Palm_DorsalMetacarpals",
              (h,sign*.057,-.028),(.039,.027,.018),FUR,wrist,
              "palm with separate knuckle masses")
    ellipsoid(f"{prefix}_Palm_ContactPad",
              (h,sign*.030,-.031),(.018,.004,.010),PADS,wrist,
              "central feline palm pad",18,12)
    xs = [h+v for v in (-.030,-.010,.010,.030)]
    for index, x in enumerate(xs,1):
        digit_bone = f"{prefix}_Digit_{index}"
        spread = (-.0024,-.0007,.0010,.0022)[index-1]
        ellipsoid(f"{prefix}_Knuckle_{index}",
                  (x,sign*(.044+spread),-.011),(.0095,.0115,.0125),
                  FUR,wrist,"individual metacarpal knuckle",16,10)
        points = [(x, sign*y, z) for y,z in
                  ((.047+spread,-.008),(.036+spread,.002),
                   (.025+spread,.011),(.010+spread,.016),
                   (-.006+spread,.013),(-.018+spread,.007),
                   (-.022+spread,-.002))]
        # Slightly different digit lengths and knuckle rhythm break the
        # repetitive mitten arc while keeping pads in contact with the wood.
        widths = [.0078,.0080,.0075,.0071,.0068,.0063,.0051]
        heights = [.0080,.0082,.0076,.0070,.0065,.0059,.0048]
        sweep(f"{prefix}_Digit_{index}_Phalanges", points, widths,
              heights,FUR,digit_bone,"separate articulated feline digit",16)
        pad_center = (x,-sign*(.020-spread),.000)
        ellipsoid(f"{prefix}_Digit_{index}_ContactPad",pad_center,
                  (.0063,.0034,.0055),PADS,digit_bone,
                  "separate digital contact pad",16,10)
        pad_centres.append(pad_center)
        sweep(f"{prefix}_Digit_{index}_PartlyRetractedClaw",
              [(x,-sign*.022,-.001),(x+.0004,-sign*.024,-.002),
               (x+.0008,-sign*.025,-.0025)],
              [.0010,.0007,.00020],[.0010,.0007,.00020],
              CLAW,digit_bone,"short retracted claw",8)
    thumb = f"{prefix}_Thumb"
    thumb_points = [(h+.032,sign*.052,-.028),
                    (h+.041,sign*.037,-.017),
                    (h+.039,sign*.023,-.008),
                    (h+.034,sign*.015,-.012)]
    sweep(f"{prefix}_OpposingThumb",thumb_points,
          [.011,.010,.008,.005],[.010,.009,.007,.0045],FUR,thumb,
          "opposing articulated thumb",14)
    ellipsoid(f"{prefix}_Thumb_ContactPad",(h+.034,sign*.017,-.014),
              (.006,.003,.006),PADS,thumb,"opposing thumb pad",14,10)
    # Small fur wedges interrupt the glove-like sleeve seam. They are low-
    # volume geometry; this is not a strand groom or final fur simulation.
    for j in range(10):
        a = math.tau*(j+rng.uniform(-.18,.18))/10
        x = h+.023*math.sin(a)
        z = -.047+.020*math.cos(a)
        y0 = sign*.082
        length = rng.uniform(.002,.004)
        sweep(f"{prefix}_WristGuardHair_{j:02d}",
              [(x,y0,z),(x+.0015,sign*(.077-length*.4),z+.002),
               (x+.0025,sign*(.077-length),z+.003)],
              [.0008,.0005,.00012],[.0007,.0004,.00010],
              GREY if j%7==0 else FUR,wrist,"short sculpted guard-hair tuft",5)


# A compact, editable control rig: each digit and thumb has its own pose bone.
# The rigid weights are intentional for this shape study; production needs
# interpolated skinning and range-reviewed combat animations.
arm_data = bpy.data.armatures.new("Nyaakoto_BokutoPaws_ControlRig")
armature = bpy.data.objects.new("RIG_Nyaakoto_BokutoPaws", arm_data)
MODEL.objects.link(armature)
armature.show_in_front = True
bpy.context.view_layer.objects.active = armature
armature.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
root = arm_data.edit_bones.new("WeaponRoot")
root.head = (-.12, 0, -.04)
root.tail = (-.10, 0, -.04)
for hand in hands:
    prefix,h,sign = hand["prefix"],hand["h"],hand["sign"]
    f = arm_data.edit_bones.new(f"{prefix}_Forearm")
    f.head = (h-.015,sign*.245,-.158)
    f.tail = (h-.015,sign*.101,-.073)
    f.parent = root
    w = arm_data.edit_bones.new(f"{prefix}_Wrist")
    w.head = f.tail
    w.tail = (h,sign*.048,-.028)
    w.parent = f
    for index,x in enumerate((h-.030,h-.010,h+.010,h+.030),1):
        d = arm_data.edit_bones.new(f"{prefix}_Digit_{index}")
        d.head = (x,sign*.047,-.008)
        d.tail = (x,sign*.008,.016)
        d.parent = w
    t = arm_data.edit_bones.new(f"{prefix}_Thumb")
    t.head = (h+.032,sign*.052,-.028)
    t.tail = (h+.039,sign*.023,-.008)
    t.parent = w
bpy.ops.object.mode_set(mode="OBJECT")
armature.select_set(False)
for obj in all_meshes:
    group = obj.vertex_groups.new(name=mesh_bones[obj.name])
    group.add(list(range(len(obj.data.vertices))),1.0,"REPLACE")
    modifier = obj.modifiers.new("Articulated paw controls", "ARMATURE")
    modifier.object = armature
    obj["uv_contract"] = "single UV0 channel; PBR material explicitly samples UV0"


with bpy.data.libraries.load(str(BOKUTO / "Nyaagyu_BokutoForm.blend"),
                             link=False) as (source,dest):
    dest.objects = [name for name in source.objects
                    if name in {"Tsuka_HandPlanedOvalWhiteOak",
                                "Tachi_MuneShinogiBluntHaWhiteOak",
                                "Tsuba_HandCutDarkLeather",
                                "Tsubadome_LeatherRetainingCollar"}]
for obj in dest.objects:
    if obj is None or obj.type != "MESH":
        continue
    PROP.objects.link(obj)
    obj["review_only"] = True
    obj.name = "ReviewOnly_" + obj.name
assert len(PROP.objects) == 4, [o.name for o in PROP.objects]


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def camera(name, position, target, horizontal_fov=None, lens=None):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    STUDIO.objects.link(obj)
    obj.location = position
    aim(obj,target)
    if horizontal_fov is not None:
        data.type = "PERSP"
        data.sensor_fit = "HORIZONTAL"
        data.angle = math.radians(horizontal_fov)
    else:
        data.lens = lens
    return obj


normal_cam = camera("Camera_NormalIdlePose_FOV70",(0,0,0),(1,0,0),70)
detail_cam = camera("Camera_GripAndDigitDetail",
                    (.11,-.36,.28),(.302,.18,-.185),lens=52)


def area(name, position, target, power, size, color):
    light = bpy.data.lights.new(name,"AREA")
    obj = bpy.data.objects.new(name,light)
    STUDIO.objects.link(obj)
    obj.location = position
    aim(obj,target)
    light.energy = power
    light.shape = "DISK"
    light.size = size
    light.color = color


area("LargeNeutralSoftbox",(.13,-.4,.55),(.34,.16,-.16),48,1.1,(1,.95,.88))
area("CoolBounce",(.68,.45,.34),(.34,.16,-.16),24,1.2,(.78,.84,1))
area("WarmRim",(.64,-.16,.17),(.34,.16,-.16),16,.8,(1,.88,.75))
scene.world.color = (.072,.075,.083)
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"

# Export and save the weapon-local model. Source textures stay relative to the
# repository and their exact hashes are pinned in the manifest below.
bpy.ops.object.select_all(action="DESELECT")
for obj in [armature,*all_meshes]:
    obj.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.export_scene.fbx(
    filepath=str(FBX),use_selection=True,object_types={"MESH","ARMATURE"},
    apply_unit_scale=True,axis_forward="-Y",axis_up="Z",path_mode="RELATIVE",
    add_leaf_bones=False,bake_anim=False,use_armature_deform_only=True,
    use_mesh_modifiers=True)
bpy.ops.object.select_all(action="DESELECT")
scene.camera = normal_cam
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

# Review uses the actual idle root (40,18,-18) cm and the actual authored-mesh
# 0.75 scale. The native UE first-person reprojection is not emulated here.
review_transform = Matrix.Translation(Vector((.40,.18,-.18))) @ Matrix.Scale(.75,4)
model_matrices = {obj:obj.matrix_world.copy() for obj in [armature,*all_meshes]}
prop_matrices = {obj:obj.matrix_world.copy() for obj in PROP.objects}
for obj,original in model_matrices.items():
    obj.matrix_world = review_transform @ original
for obj,original in prop_matrices.items():
    obj.matrix_world = review_transform @ original


def render(filename, camera_obj, with_paws):
    MODEL.hide_render = not with_paws
    scene.camera = camera_obj
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)


render("IdlePose_BokutoOnly.png",normal_cam,False)
render("IdlePose_BokutoAndPaws.png",normal_cam,True)
render("GripDetail_BokutoOnly.png",detail_cam,False)
render("GripDetail_BokutoAndPaws.png",detail_cam,True)

for obj,original in model_matrices.items():
    obj.matrix_world = original
for obj,original in prop_matrices.items():
    obj.matrix_world = original
MODEL.hide_render = False

record = {
    "schema_version":1,
    "name":"SK_Nyaakoto_BokutoPaws_SourceOnly",
    "status":"source-only; no gameplay component, animation, or runtime admission",
    "generator":"scripts/art/create_nyaakoto_bokuto_viewmodel.py",
    "units":"metres",
    "rig_bones":sorted(b.name for b in arm_data.bones),
    "mesh_count":len(all_meshes),
    "mesh_triangles":sum(len(p.vertices)-2 for o in all_meshes for p in o.data.polygons),
    "digit_mesh_count":len([o for o in all_meshes if o.name.endswith("_Phalanges")]),
    "digital_pad_count":len([o for o in all_meshes if "Digit_" in o.name and "ContactPad" in o.name]),
    "grip_axis":"+X",
    "contact_pad_centres_m":pad_centres,
    "idle_review_transform":{"weapon_root_location_cm":[40,18,-18],"mesh_scale":.75,
                             "camera_horizontal_fov_degrees":70},
    "review_prop":str((BOKUTO / bokuto_record["source_blend"]).relative_to(ROOT)),
    "review_prop_sha256":sha(BOKUTO / bokuto_record["source_blend"]),
    "material_rights":{
        "fur_cloth_lacquer":"Project-owned OpenAI image-generation output and procedural maps; source and terms in Content/SourceArt/Characters/Hero/PBR/manifest.json",
        "paw_pads":pad_record["license"],
        "solid_lacing_iron_claws":"Original procedural material parameters",
        "bokuto_review_only":"Poly Haven white_oak_veneer CC0 maps and original mesh, pinned in Content/SourceArt/Weapons/DojoBokutoForm/manifest.json",
        "SORA_kamon":"Exact project-held SORA SVG raster from Content/SourceArt/UI/sora_logo_manifest.json, mounted on a raised kote disk",
        "user_character_image":"Visual design reference only; not copied into mesh or texture"},
    "user_character_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
    "source_manifests":{
        str((HERO / "manifest.json").relative_to(ROOT)):sha(HERO / "manifest.json"),
        str((PAD / "manifest.json").relative_to(ROOT)):sha(PAD / "manifest.json"),
        str((BOKUTO / "manifest.json").relative_to(ROOT)):sha(BOKUTO / "manifest.json")},
    "sora_logo_svg_sha256":sha(SORA_SVG),
    "sora_logo_png_sha256":sha(SORA_LOGO),
    "source_texture_hashes":{
        str((HERO / entry["file"]).relative_to(ROOT)):entry["sha256"]
        for surface in ("fur_white","fur_grey","silk_indigo","lacquer_oxblood")
        for entry in hero_maps[surface].values()},
    "outputs":{}
}
record["source_texture_hashes"].update({
    str((PAD / entry["file"]).relative_to(ROOT)):entry["sha256"]
    for entry in pad_record["maps"].values()})
for path in (BLEND,FBX,*sorted(OUT.glob("*Pose*.png")),
             *sorted(OUT.glob("GripDetail*.png"))):
    record["outputs"][path.name] = {"sha256":sha(path),"bytes":path.stat().st_size}
MANIFEST.write_text(json.dumps(record,indent=2)+"\n")
print("NYAAKOTO_BOKUTO_PAW_SOURCE_CREATED",len(all_meshes),len(arm_data.bones),flush=True)
