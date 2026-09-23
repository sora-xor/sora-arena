"""Editable, source-only Nyaakoto V4 facial anatomy study from pinned V3.

Run create_head_v4_maps.py first, then:
  blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoHeadV4/create_head_v4.py
No runtime asset is modified. The goal is a measurable anatomy pass, not a
production-ready character or a claim of photoreal qualification.
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

ROOT = Path(__file__).resolve().parent
V3 = ROOT.parent / "NyaakotoCoatV3"
BASE = V3 / "Nyaakoto_HeadCoat_V3_Study.blend"
PIN = "9563f2521fe272b4dbf969e7a1d3e99b22f17dbcb6f6e3ab683f89eb093b9e98"
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == PIN, "V3 source revision changed"
random.seed(26092404)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.context.scene


def smooth(a, b, v):
    t = max(0., min(1., (v-a)/(b-a)))
    return t*t*(3-2*t)


def gauss(v, center, radius):
    return math.exp(-((v-center)/radius)**2)


def material(name, rgba, rough=.8, sss=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Subsurface Weight"].default_value = sss
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def drop(ob):
    bpy.data.objects.remove(ob, do_unlink=True)


for ob in tuple(bpy.data.objects):
    if ob.name.startswith(("Ear_CuppedOrganic_", "Ear_AuralFur_", "Groom_Nyaakoto_",
                           "Vibrissae_", "Follicle_")):
        drop(ob)

head = bpy.data.objects["SM_Nyaakoto_HeadCoat_V3_Study"]
head.name = "SM_Nyaakoto_HeadAnatomy_V4_Study"
# Deform the original connected 82k-vertex facial shell. The broad, smooth
# displacement fields retain topology/UVs and transition through jaw, cheek,
# and forehead rather than adding separate spherical cheek/muzzle primitives.
for v in head.data.vertices:
    x, y, z = v.co
    side = 1 if y >= 0 else -1
    cheek = gauss(x, .086, .078) * gauss(abs(y), .097, .037) * gauss(z, 1.615, .034)
    muzzle = smooth(.147, .202, x) * (1-smooth(1.608, 1.650, z)) * smooth(1.528, 1.55, z)
    forehead = smooth(.07, .155, x) * smooth(1.691, 1.724, z)
    low_neck = 1-smooth(1.489, 1.568, z)
    # A zygomatic slope instead of round lateral cheek pouches.
    y -= side * .018 * cheek
    x += .004 * cheek
    z -= .003 * cheek
    # The two white whisker pads stay visible, but retreat into the bridge.
    x -= .014 * muzzle
    y *= 1 - .065 * muzzle
    # Frontonasal wedge and lower crown: reduce the overspherical dome.
    x -= .006 * forehead
    z -= .006 * forehead * (1-smooth(.14, .22, x))
    # Broaden the jaw-to-neck attachment and shorten the pointed throat.
    y *= 1 + .18 * low_neck
    x += .006 * low_neck
    z += .009 * (1-smooth(1.465, 1.505, z))
    v.co = (x, y, z)
head.data.update()

# These small features were separate V3 meshes. Bring them forward/back with
# the moved muzzle shell so that the leather nose and philtrum remain seated.
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith(("Nose_", "Naris_", "Mouth_", "Philtrum")):
        continue
    shift = -.021 if ob.name.startswith(("Nose_", "Naris_")) else -.014
    inv = ob.matrix_world.inverted()
    for v in ob.data.vertices:
        q = ob.matrix_world @ v.co
        q.x += shift
        v.co = inv @ q
    ob.data.update()

# Paint small M-shaped forehead tabby strokes into V3's coat vertex mask.
# These markings remain editable and travel with the connected mesh/FBX.
mix = head.data.color_attributes["CoatMix"]
for loop in head.data.loops:
    p = head.data.vertices[loop.vertex_index].co
    if p.x < .098 or not 1.686 < p.z < 1.749 or abs(p.y) > .074:
        continue
    zt = (p.z - 1.688)/.060
    stripe = 0.
    for sign in (-1, 0, 1):
        center = sign * (.029 + .007 * (1-zt))
        if sign == 0:
            center = .006 * math.sin(zt*math.pi*2)
        stripe = max(stripe, gauss(p.y, center, .0065) * smooth(0, .17, zt) * (1-smooth(.82, 1, zt)))
    old = list(mix.data[loop.index].color)
    old[1] = max(old[1], .78 * stripe)
    mix.data[loop.index].color = old


def packed(name, noncolor=False):
    im = bpy.data.images.load(str(ROOT / name), check_existing=False)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    im.pack()
    return im


coat = bpy.data.materials.new("M_Nyaakoto_V4_UniqueUV_Coat")
coat.use_nodes = True
n, links = coat.node_tree.nodes, coat.node_tree.links
bsdf = n.get("Principled BSDF")
bsdf.inputs["Metallic"].default_value = 0
bsdf.inputs["Sheen Weight"].default_value = .24
bsdf.inputs["Sheen Roughness"].default_value = .78
c = n.new("ShaderNodeTexImage"); c.name = "UniqueUV_Albedo"; c.image = packed("T_Nyaakoto_HeadV4_Albedo.png")
mask = n.new("ShaderNodeAttribute"); mask.attribute_name = "CoatMix"
split = n.new("ShaderNodeSeparateColor")
links.new(mask.outputs["Color"], split.inputs["Color"])
factor = n.new("ShaderNodeMath"); factor.operation = "MULTIPLY"; factor.inputs[1].default_value = .86
links.new(split.outputs["Green"], factor.inputs[0])
dark = n.new("ShaderNodeMixRGB"); dark.blend_type = "MIX"; dark.inputs[2].default_value = (.075, .079, .083, 1)
links.new(factor.outputs[0], dark.inputs[0]); links.new(c.outputs["Color"], dark.inputs[1])
links.new(dark.outputs[0], bsdf.inputs["Base Color"])
normal = n.new("ShaderNodeTexImage"); normal.name = "UniqueUV_NormalGL"; normal.image = packed("T_Nyaakoto_HeadV4_NormalGL.png", True)
nmap = n.new("ShaderNodeNormalMap"); nmap.inputs["Strength"].default_value = .48
links.new(normal.outputs["Color"], nmap.inputs["Color"]); links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
orm = n.new("ShaderNodeTexImage"); orm.name = "UniqueUV_ORM"; orm.image = packed("T_Nyaakoto_HeadV4_ORM.png", True)
sep = n.new("ShaderNodeSeparateColor"); links.new(orm.outputs["Color"], sep.inputs["Color"])
links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
assign(head, coat)
head["study_revision"] = "V4 connected facial-shell cheek/jaw/orbit pass"
head["source_only"] = True

# Seat the V3 eye pieces deeper and narrow the vertical opening. Recolor the
# wetlines/tarsal margins as fur/skin so they stop reading as chrome rings.
upper = material("M_UpperLid_DarkTabby", (.16, .16, .16, 1), .82, .05)
lower = material("M_LowerLid_CoolGrey", (.28, .27, .26, 1), .86, .05)
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith(("Eye_", "Iris_", "Cornea_", "Upper_Tarsal", "Lower_Tarsal", "Upper_Wetline")):
        continue
    side = -1 if ob.name.endswith("_-1") else 1
    center = Vector((.144, side*.064, 1.670))
    inv = ob.matrix_world.inverted()
    for v in ob.data.vertices:
        q = ob.matrix_world @ v.co
        delta = q-center
        q = center + Vector((delta.x*.83-.012, delta.y*.91, delta.z*.78))
        v.co = inv @ q
    ob.data.update()
    if ob.name.startswith(("Upper_Tarsal", "Upper_Wetline")):
        assign(ob, upper)
    elif ob.name.startswith("Lower_Tarsal"):
        assign(ob, lower)

# Tilt each auricle backward and give the bowl a true front/back thickness.
# The central concavity and dark rim replace the former flat pink panels.
earmat = material("M_Auricle_InnerSkin_And_GreyFur", (.14, .145, .15, 1), .85, .10)
en = earmat.node_tree.nodes; el = earmat.node_tree.links
attr = en.new("ShaderNodeAttribute"); attr.attribute_name = "EarSkinMix"
emix = en.new("ShaderNodeMixRGB"); emix.inputs[1].default_value = (.15,.155,.16,1); emix.inputs[2].default_value = (.22,.105,.10,1)
el.new(attr.outputs["Fac"], emix.inputs[0]); el.new(emix.outputs[0], en.get("Principled BSDF").inputs["Base Color"])


def mesh_obj(name, verts, faces, uvs, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces); mesh.update()
    ob = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(ob)
    mesh.materials.append(mat)
    layer = mesh.uv_layers.new(name="UVMap")
    for f in mesh.polygons:
        f.use_smooth = True
        for li in f.loop_indices:
            layer.data[li].uv = uvs[mesh.loops[li].vertex_index]
    ob["source_only"] = True
    return ob


for side in (-1, 1):
    nr, nc = 24, 24
    verts, uv, faces = [], [], []
    for layer in range(2):
        for j in range(nr+1):
            t = j/nr
            half = (.032*(1-t)**.88 + .00025) * (1+.12*math.sin(math.pi*t))
            center_y = side*(.079 + .014*t)
            # Lower quarter is deliberately buried inside the crown so the
            # free-standing bottom cap cannot form a black cutout at the root.
            z = 1.688 + .099*t
            for i in range(nc+1):
                u = 2*i/nc - 1
                # Front/back sheets converge at the tip. Curved rolled edges
                # and a recessed central bowl give the profile a cartilage
                # wedge rather than the V3 rectangular/slab silhouette.
                center_x = .001 - .029*t + .004*math.sin(math.pi*t)
                thickness = .014*(1-t)**.8 + .0003
                front = center_x + thickness*.55 + .006*(abs(u)**2)*math.sin(math.pi*t) - .006*(1-u*u)*math.sin(math.pi*t)
                rear = center_x - thickness*.55 - .002*(1-u*u)*math.sin(math.pi*t)
                x = front if layer == 0 else rear
                verts.append((x, center_y + side*u*half, z))
                uv.append((i/nc, t))
    stride = nc+1; sheet = (nr+1)*stride
    for layer in range(2):
        for j in range(nr):
            for i in range(nc):
                a = layer*sheet + j*stride+i
                face = (a, a+1, a+stride+1, a+stride)
                faces.append(face if layer == 0 else face[::-1])
    for j in range(nr):
        for i in (0, nc):
            a=j*stride+i; faces.append((a,a+stride,a+stride+sheet,a+sheet))
    for i in range(nc):
        faces.append((i,i+sheet,i+sheet+1,i+1))
        a=nr*stride+i; faces.append((a,a+1,a+sheet+1,a+sheet))
    ear = mesh_obj(f"Ear_CuppedThick_V4_{side}", verts, faces, uv, earmat)
    ca = ear.data.color_attributes.new(name="EarSkinMix", type="FLOAT_COLOR", domain="CORNER")
    for loop in ear.data.loops:
        idx = loop.vertex_index
        if idx >= sheet:
            f = 0
        else:
            j,i = divmod(idx,stride); t=j/nr; u=abs(2*i/nc-1)
            f=.78*(1-smooth(.36,.79,u))*smooth(.12,.30,t)*(1-smooth(.81,1,t))
        ca.data[loop.index].color = (f,f,f,1)

# Smaller, darker embedded follicle papillae with five filament roots per side.
follicle = material("M_FolliclePigment_V4", (.16,.13,.125,1), .88)
keratin = material("M_VibrissaKeratin_V4", (.56,.54,.52,1), .77)
curve = bpy.data.curves.new("V4_Vibrissae", "CURVE")
curve.dimensions="3D"; curve.bevel_depth=.000052; curve.bevel_resolution=2
curve.materials.append(keratin)
for side in (-1,1):
    for k in range(5):
        root = Vector((.178-.002*(k%2), side*(.027+.004*(k%2)), 1.566+.005*k))
        # Arched, tapered in direction; no rigid ruler-straight starburst.
        coords = (root,
                  root+Vector((.006,side*.031,.005+(k-2)*.002)),
                  root+Vector((-.009,side*.075,.004+(k-2)*.004)),
                  root+Vector((-.029,side*(.103+.004*k),-.004+(k-2)*.006)))
        spline=curve.splines.new("BEZIER"); spline.bezier_points.add(3)
        for p,q in zip(spline.bezier_points,coords):
            p.co=q; p.handle_left_type="AUTO"; p.handle_right_type="AUTO"
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=.00065, location=root)
        dot=bpy.context.object; dot.name=f"FollicleV4_{side}_{k}"; assign(dot,follicle)
        dot["source_only"] = True
whiskers=bpy.data.objects.new("Vibrissae_CurvedKeratin_V4",curve)
bpy.context.collection.objects.link(whiskers); whiskers["source_only"] = True

# Restrained guard coat: shorter and sparser than V3, following the revised
# surface normals. Source curves are deliberately excluded from static FBX.
furgray=material("M_GuardHair_GreyV4",(.255,.25,.245,1),.82)
furivory=material("M_GuardHair_IvoryV4",(.71,.68,.64,1),.84)
furdark=material("M_GuardHair_CharcoalV4",(.11,.11,.11,1),.84)
fur=bpy.data.curves.new("V4_ShortGuardGroom", "CURVE")
fur.dimensions="3D"; fur.resolution_u=1; fur.bevel_depth=.000028; fur.bevel_resolution=1
for m in (furgray,furivory,furdark): fur.materials.append(m)
polys=[p for p in head.data.polygons if p.area > 1e-10]
cumulative=[]; total=0.
for p in polys:
    total += p.area; cumulative.append(total)
count=0
for _ in range(22000):
    p=polys[bisect.bisect_left(cumulative,random.random()*total)]
    ids=list(p.vertices)
    if len(ids)<3: continue
    a,b,c=(head.data.vertices[i].co for i in ids[:3])
    r1,r2=random.random(),random.random(); sr=math.sqrt(r1)
    q=a*(1-sr)+b*(sr*(1-r2))+c*(sr*r2)
    if q.z<1.535 or (q.x>.17 and abs(q.y)<.03 and q.z<1.67): continue
    nrm=p.normal.normalized(); side=1 if q.y>=0 else -1
    direction=Vector((-.48,side*.24,-.72))
    direction-=nrm*direction.dot(nrm)
    if direction.length<.00001: continue
    direction.normalize(); length=random.uniform(.0010,.0028)
    if q.x>.13 and q.z<1.64: length*=.72
    root=q+nrm*.00008
    spline=fur.splines.new("POLY"); spline.points.add(2)
    for point,pos in zip(spline.points,(root,root+direction*length*.55+nrm*.00010,root+direction*length+nrm*.00015)):
        point.co=(*pos,1)
    colors=[mix.data[li].color for li in p.loop_indices[:3]]
    white=sum(col[0] for col in colors)/len(colors)
    stripe=sum(col[1] for col in colors)/len(colors)
    spline.material_index=1 if white>.58 else (2 if stripe>.43 else 0)
    count+=1
groom=bpy.data.objects.new("Groom_Nyaakoto_ShortGuard_V4",fur)
bpy.context.collection.objects.link(groom); groom["source_only"] = True

scene.render.engine="CYCLES"; scene.cycles.samples=48
scene.render.resolution_x=1152; scene.render.resolution_y=1152; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.world.color=(.15,.15,.15)
scene.view_settings.view_transform="AgX"; scene.view_settings.look="AgX - Medium High Contrast"
scene.view_settings.exposure=-.23
cam=bpy.data.objects["Portrait_85mm"]; cam.data.ortho_scale=.42
for label,loc in (("Front",(.70,0,1.675)),("ThreeQuarter",(.52,-.45,1.705)),("Profile",(.025,-.74,1.675))):
    cam.location=loc
    cam.rotation_euler=(Vector((.074,0,1.684))-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(ROOT/f"Nyaakoto_HeadV4_{label}.png")
    bpy.ops.render.render(write_still=True)

meshes=[o for o in scene.objects if o.type=="MESH"]
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes: ob.select_set(True)
bpy.context.view_layer.objects.active=head
bpy.ops.export_scene.fbx(filepath=str(ROOT/"SM_Nyaakoto_HeadAnatomy_V4_Study.fbx"),
    use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
    add_leaf_bones=False, path_mode="STRIP", embed_textures=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE")
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"Nyaakoto_HeadAnatomy_V4_Study.blend"))
manifest={
    "schema_version":1,
    "identity":"Nyaakoto / ニャーコト anatomical head V4 source-only study",
    "production_status":"SOURCE_REVIEW_ONLY; no Unreal/runtime integration or photoreal qualification",
    "base_v3_blend_sha256":PIN,
    "user_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
    "user_reference_embedded":False,
    "source_license":"Original project work, revised from project-owned V3. No external scans or paid assets.",
    "texture_provenance":"Project-owned V3 unique-UV atlas transformed and normal/ORM artist-derived; no measured scan or AO bake",
    "units":"meters; +X face forward; +Z up",
    "groom_strands":count,
    "files_sha256":{},
}
for p in sorted(ROOT.iterdir()):
    if p.is_file() and p.name not in ("manifest.json","create_head_v4.py","create_head_v4_maps.py","validate_head_v4.py","README.md"):
        manifest["files_sha256"][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
(ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAKOTO_HEAD_V4_COMPLETE",len(meshes),"meshes",count,"groom splines")
