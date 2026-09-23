"""Source-only Nyaakoto head V3: anatomical/form and fur-shader test.

Run after create_coat_maps.py:
  blender -b --factory-startup --python Content/SourceArt/Characters/NyaakotoCoatV3/create_coat_v3.py

The V2 source is an explicit, pinned input. This study does not alter the
runtime skeletal character or its Unreal import pipeline.
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
BASE = ROOT.parent / "NyaakotoAnatomyV2" / "Nyaakoto_FacialAnatomy_V2_Study.blend"
USER_REFERENCE_SHA256 = "c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801"
random.seed(260925)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.context.scene


def smoothstep(lo, hi, x):
    t = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return t * t * (3.0 - 2.0 * t)


def reshape(p):
    x, y, z = p
    # Shorten the spherical caudal braincase and lower its crown. The
    # fronto-nasal wedge remains, so the identity is still the same cat.
    rear = 1.0 - smoothstep(-.13, .065, x)
    upper = smoothstep(1.59, 1.71, z)
    x += .056 * rear * (.42 + .58 * upper)
    y *= 1.0 - .12 * rear * upper
    z -= .030 * upper * (1.0 - smoothstep(.08, .20, x))
    # The throat must emerge from a jaw, rather than read as a round column.
    neck = 1.0 - smoothstep(1.49, 1.615, z)
    y *= 1.0 - .44 * neck
    x += .022 * neck
    z += .035 * (1.0 - smoothstep(1.45, 1.53, z))
    # Subtly pull the white whisker-pad shelf into the facial wedge.
    muzzle = smoothstep(.145, .215, x) * (1.0 - smoothstep(1.59, 1.64, z))
    x -= .012 * muzzle
    cheek = math.exp(-((z - 1.615) / .035) ** 2 - ((abs(y) - .092) / .050) ** 2)
    y -= math.copysign(.009 * cheek, y)
    return Vector((x, y, z))


def delete_obj(ob):
    bpy.data.objects.remove(ob, do_unlink=True)


# Remove V2's triangular ear blades, opaque quill-like card cloud, and whisker
# lines before building more organic ear shells and thin keratin filaments.
for ob in tuple(bpy.data.objects):
    if ob.name.startswith((
        "Ear_CuppedCartilage_", "Ear_rolled_margin_", "Ear_guard_hair_",
        "Fur_Cards_Head_Directional", "Whisker_", "Eye_socket_shadow_",
    )):
        delete_obj(ob)

head = bpy.data.objects["SM_Nyaakoto_FacialAnatomy_V2_Study"]
head.name = "SM_Nyaakoto_HeadCoat_V3_Study"
for ob in tuple(bpy.data.objects):
    if ob.type != "MESH":
        continue
    inverse = ob.matrix_world.inverted()
    for vertex in ob.data.vertices:
        q = reshape(ob.matrix_world @ vertex.co)
        vertex.co = inverse @ q
    ob.data.update()

# Broaden the orbital recesses around the still-editable separate globes. The
# depression is in the connected head shell, not a black eye-socket decal.
for v in head.data.vertices:
    x, y, z = v.co
    if x < .10:
        continue
    for side in (-1, 1):
        cy = side * .063
        influence = math.exp(-((y - cy) / .033) ** 2 - ((z - 1.675) / .022) ** 2)
        v.co.x -= .0040 * influence
head.data.update()

eye_prefixes = (
    "Eye_", "Iris_UV0_", "Cornea_ClearConvex_", "Upper_TarsalMargin_",
    "Lower_TarsalMargin_", "Upper_Wetline_",
)
for ob in bpy.data.objects:
    if ob.type != "MESH" or not ob.name.startswith(eye_prefixes):
        continue
    side = -1 if ob.name.endswith("_-1") else 1
    center = reshape(Vector((.150, side * .064, 1.678)))
    inverse = ob.matrix_world.inverted()
    for vertex in ob.data.vertices:
        world = ob.matrix_world @ vertex.co
        delta = world - center
        # Retreat the old exposed glass/rim assembly into the orbit while
        # widening the almond aperture. The V2 dark socket sphere was removed.
        world = center + Vector((delta.x * .72 - .008, delta.y * 1.15, delta.z * 1.17))
        vertex.co = inverse @ world
    ob.data.update()

for side in (-1, 1):
    globe = bpy.data.objects.get(f"Eye_globe_{side}")
    if globe:
        glass = globe.data.materials[0].node_tree.nodes.get("Principled BSDF")
        glass.inputs["Base Color"].default_value = (.24, .255, .265, 1)
        glass.inputs["Roughness"].default_value = .32


def image(name, noncolor=False):
    im = bpy.data.images.load(str(ROOT / name), check_existing=False)
    if noncolor:
        im.colorspace_settings.name = "Non-Color"
    im.pack()
    return im


albedo = image("T_Nyaakoto_CoatV3_Albedo.png")
normal = image("T_Nyaakoto_CoatV3_NormalGL.png", True)
orm = image("T_Nyaakoto_CoatV3_ORM.png", True)
coat = bpy.data.materials.new("M_Nyaakoto_CoatV3_UniqueUV_PBR")
coat.use_nodes = True
nodes = coat.node_tree.nodes
links = coat.node_tree.links
bsdf = nodes.get("Principled BSDF")
bsdf.inputs["Metallic"].default_value = 0
bsdf.inputs["Sheen Weight"].default_value = .18
bsdf.inputs["Sheen Roughness"].default_value = .72
col = nodes.new("ShaderNodeTexImage")
col.name = "UniqueUV_Albedo"
col.image = albedo
mask_attr = nodes.new("ShaderNodeAttribute")
mask_attr.attribute_name = "CoatMix"
mask_sep = nodes.new("ShaderNodeSeparateColor")
links.new(mask_attr.outputs["Color"], mask_sep.inputs["Color"])
stripe_factor = nodes.new("ShaderNodeMath")
stripe_factor.operation = "MULTIPLY"
stripe_factor.inputs[1].default_value = .60
links.new(mask_sep.outputs["Green"], stripe_factor.inputs[0])
darkened = nodes.new("ShaderNodeMixRGB")
darkened.blend_type = "MIX"
darkened.inputs[2].default_value = (.11, .10, .095, 1)
links.new(col.outputs["Color"], darkened.inputs[1])
links.new(stripe_factor.outputs[0], darkened.inputs[0])
grade = nodes.new("ShaderNodeMixRGB")
grade.blend_type = "MULTIPLY"
grade.inputs[0].default_value = 1.0
grade.inputs[2].default_value = (.79, .76, .74, 1)
links.new(darkened.outputs[0], grade.inputs[1])
links.new(grade.outputs[0], bsdf.inputs["Base Color"])
ntex = nodes.new("ShaderNodeTexImage")
ntex.name = "UniqueUV_FiberNormal_GL"
ntex.image = normal
nmap = nodes.new("ShaderNodeNormalMap")
nmap.inputs["Strength"].default_value = .43
links.new(ntex.outputs["Color"], nmap.inputs["Color"])
links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
packed = nodes.new("ShaderNodeTexImage")
packed.name = "UniqueUV_ORM_AOwhite"
packed.image = orm
sep = nodes.new("ShaderNodeSeparateColor")
links.new(packed.outputs["Color"], sep.inputs["Color"])
links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
head.data.materials.clear()
head.data.materials.append(coat)
head["source_study_only"] = True
head["mesh_form_note"] = "V2 connected shell reshaped; jaw/eyelids still require production sculpt/retopo"


def mat(name, color, rough, sss=0.0, transmission=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    p = material.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Subsurface Weight"].default_value = sss
    p.inputs["Transmission Weight"].default_value = transmission
    return material


fur_gray = mat("M_ShortGuardHair_Grey", (.29, .28, .265), .73)
fur_cream = mat("M_ShortGuardHair_Ivory", (.68, .64, .58), .78)
fur_dark = mat("M_ShortGuardHair_Charcoal", (.13, .12, .115), .76)
for m in (fur_gray, fur_cream, fur_dark):
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Sheen Weight"].default_value = .36
    p.inputs["Sheen Roughness"].default_value = .65

ear_mat = mat("M_CuppedEar_CartilageFurBlend", (.26, .245, .23), .79, .10)
ear_nodes = ear_mat.node_tree.nodes
ear_links = ear_mat.node_tree.links
ear_attr = ear_nodes.new("ShaderNodeAttribute")
ear_attr.attribute_name = "EarSkinMix"
ear_mix = ear_nodes.new("ShaderNodeMixRGB")
ear_mix.inputs[1].default_value = (.26, .245, .23, 1)
ear_mix.inputs[2].default_value = (.40, .235, .215, 1)
ear_links.new(ear_attr.outputs["Fac"], ear_mix.inputs[0])
ear_links.new(ear_mix.outputs[0], ear_nodes.get("Principled BSDF").inputs["Base Color"])
ear_noise = ear_nodes.new("ShaderNodeTexNoise")
ear_noise.inputs["Scale"].default_value = 230
ear_bump = ear_nodes.new("ShaderNodeBump")
ear_bump.inputs["Strength"].default_value = .12
ear_bump.inputs["Distance"].default_value = .00007
ear_links.new(ear_noise.outputs["Fac"], ear_bump.inputs["Height"])
ear_links.new(ear_bump.outputs[0], ear_nodes.get("Principled BSDF").inputs["Normal"])


def new_mesh(name, vertices, faces, material, uv):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(ob)
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        face.use_smooth = True
        for loop_idx in face.loop_indices:
            vertex_idx = mesh.loops[loop_idx].vertex_index
            layer.data[loop_idx].uv = uv[vertex_idx]
    ob["source_study_only"] = True
    return ob


for side in (-1, 1):
    rows, columns = 28, 24
    verts, uv, faces = [], [], []
    for layer in (0, 1):
        for j in range(rows + 1):
            t = j / rows
            half = (.036 + .007 * math.sin(math.pi * t)) * (1.0 - t) ** .64 + .0007
            center_y = side * (.084 + .019 * t)
            z = 1.713 + .091 * t
            for i in range(columns + 1):
                u = 2 * i / columns - 1
                # Concave inner cup with a substantial rolled edge and a
                # rear surface, tapering to a softly rounded asymmetric tip.
                bowl = .007 * (1 - u * u) * math.sin(math.pi * t)
                x = (.019 - .011 * t - bowl) if layer == 0 else (-.001 - .004 * t)
                verts.append((x, center_y + side * u * half, z))
                uv.append((i / columns, t))
    stride = columns + 1
    sheet = (rows + 1) * stride
    for layer in (0, 1):
        for j in range(rows):
            for i in range(columns):
                a = layer * sheet + j * stride + i
                quad = (a, a + 1, a + stride + 1, a + stride)
                faces.append(quad if layer == 0 else quad[::-1])
    for j in range(rows):
        for i in (0, columns):
            a = j * stride + i
            faces.append((a, a + stride, a + stride + sheet, a + sheet))
    ear = new_mesh(f"Ear_CuppedOrganic_{side}", verts, faces, ear_mat, uv)
    attr = ear.data.color_attributes.new(name="EarSkinMix", type="FLOAT_COLOR", domain="CORNER")
    for loop in ear.data.loops:
        idx = loop.vertex_index
        if idx >= sheet:
            val = 0
        else:
            j, i = divmod(idx, stride)
            t = j / rows
            u = abs(2 * i / columns - 1)
            val = .68 * (1 - smoothstep(.41, .83, u)) * smoothstep(.17, .38, t) * (1 - smoothstep(.85, 1, t))
        attr.data[loop.index].color = (val, val, val, 1)

# The nose has tiny pores and a restrained waxy leather response. No metallic
# or plastic clearcoat is used on fur or cartilage.
nose = bpy.data.objects.get("Nose_Leather_Tapered")
if nose:
    nose_mat = mat("M_NoseLeather_MicroPores", (.38, .21, .21), .53, .055)
    n_nodes = nose_mat.node_tree.nodes
    n_links = nose_mat.node_tree.links
    micro = n_nodes.new("ShaderNodeTexNoise")
    micro.inputs["Scale"].default_value = 770
    bump = n_nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .22
    bump.inputs["Distance"].default_value = .000026
    n_links.new(micro.outputs["Fac"], bump.inputs["Height"])
    n_links.new(bump.outputs[0], n_nodes.get("Principled BSDF").inputs["Normal"])
    nose.data.materials.clear()
    nose.data.materials.append(nose_mat)

# Short guard hairs follow the surface with a small out-of-plane lift. Roots
# use the V2 unique-UV coat mask for color, but are new splines, not cards.
head.data.update()
polys = [p for p in head.data.polygons if p.area > 1e-10]
cumulative = []
total = 0.0
for p in polys:
    total += p.area
    cumulative.append(total)
fur_curve = bpy.data.curves.new("Nyaakoto_DirectionalFur_V3", "CURVE")
fur_curve.dimensions = "3D"
fur_curve.resolution_u = 1
fur_curve.bevel_depth = .000045
fur_curve.bevel_resolution = 1
for m in (fur_gray, fur_cream, fur_dark):
    fur_curve.materials.append(m)
coat_mask = head.data.color_attributes["CoatMix"]
strand_count = 0
for _ in range(36000):
    poly = polys[bisect.bisect_left(cumulative, random.random() * total)]
    ids = list(poly.vertices)
    if len(ids) < 3:
        continue
    a, b, c = (head.data.vertices[i].co for i in ids[:3])
    r1, r2 = random.random(), random.random()
    sr1 = math.sqrt(r1)
    u, v, w = 1 - sr1, sr1 * (1 - r2), sr1 * r2
    p = a * u + b * v + c * w
    n = poly.normal.normalized()
    if p.z < 1.53 or (p.x > .17 and abs(p.y) < .036 and 1.55 < p.z < 1.69):
        continue
    side = 1 if p.y >= 0 else -1
    direction = Vector((-.5, side * (.3 if p.z < 1.72 else .12), -.8 if p.z < 1.72 else -.2))
    direction -= n * direction.dot(n)
    if direction.length < .00001:
        continue
    direction.normalize()
    length = random.uniform(.0017, .0041)
    if p.x > .12 and p.z < 1.63:
        length *= .74
    root = p + n * .00012
    mid = root + direction * length * .50 + n * .00014
    tip = root + direction * length + n * .00023
    spline = fur_curve.splines.new("POLY")
    spline.points.add(2)
    for point, co in zip(spline.points, (root, mid, tip)):
        point.co = (*co, 1)
    mask = [coat_mask.data[i].color for i in poly.loop_indices[:3]]
    ivory = sum(color[0] for color in mask) / len(mask)
    stripe = sum(color[1] for color in mask) / len(mask)
    spline.material_index = 1 if ivory > .58 else (2 if stripe > .48 else 0)
    strand_count += 1
fur_ob = bpy.data.objects.new("Groom_Nyaakoto_ShortDirectional_V3", fur_curve)
bpy.context.collection.objects.link(fur_ob)
fur_ob["source_study_only"] = True
fur_ob["production_note"] = "Cycles source groom; no UE groom binding or validated card LOD"


def add_filaments(name, polylines, radius, material):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    curve.materials.append(material)
    for line in polylines:
        spline = curve.splines.new("POLY")
        spline.points.add(len(line) - 1)
        for point, co in zip(spline.points, line):
            point.co = (*co, 1)
    ob = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(ob)
    ob["source_study_only"] = True
    return ob


whisker_mat = mat("M_Whisker_Keratin_V3", (.75, .73, .68), .69)
whiskers = []
for side in (-1, 1):
    for k in range(9):
        dz = -.011 + .003 * k
        root = Vector((.198 - .002 * (k % 3), side * (.027 + .004 * (k % 3)), 1.579 + dz))
        reach = .062 + .007 * (k % 4)
        whiskers.append((
            root,
            root + Vector((-.012, side * .052, .002 + .003 * (k - 4))),
            root + Vector((-.047, side * reach * 1.7, -.003 + .003 * (k - 4))),
        ))
add_filaments("Vibrissae_FineKeratin_V3", whiskers, .00007, whisker_mat)

for side in (-1, 1):
    filaments = []
    for k in range(95):
        t = random.uniform(.12, .86)
        u = random.uniform(-.66, .66)
        half = (.036 + .007 * math.sin(math.pi * t)) * (1 - t) ** .64 + .0007
        y = side * (.084 + .019 * t + u * half)
        z = 1.713 + .091 * t
        x = .019 - .011 * t - .007 * (1 - u * u) * math.sin(math.pi * t) + .0006
        start = Vector((x, y, z))
        filaments.append((
            start, start + Vector((.003, side * u * .005, .004)),
            start + Vector((.004, side * u * .010, .007 + .004 * random.random())),
        ))
    add_filaments(f"Ear_AuralFur_{side}_V3", filaments, .000035, fur_cream)

# A neutral portrait rig, identical for every fixed-view frame. These are
# review renders, not in-game evidence.
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.render.resolution_x = 1152
scene.render.resolution_y = 1152
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (.15, .15, .15)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -.23
cam = bpy.data.objects["Portrait_85mm"]
cam.data.ortho_scale = .42
for label, location in (
    ("Front", (.70, 0, 1.675)),
    ("ThreeQuarter", (.52, -.45, 1.705)),
    ("Profile", (.025, -.74, 1.675)),
):
    cam.location = location
    cam.rotation_euler = (Vector((.074, 0, 1.684)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(ROOT / f"Nyaakoto_CoatV3_{label}.png")
    bpy.ops.render.render(write_still=True)

# FBX carries the editable mesh and UV0; the Blender file carries the
# source groom. Production would require a skinned groom/card export.
meshes = [o for o in scene.objects if o.type == "MESH" and o != cam]
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = head
bpy.ops.export_scene.fbx(
    filepath=str(ROOT / "SM_Nyaakoto_HeadCoat_V3_Study.fbx"),
    use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
    add_leaf_bones=False, path_mode="STRIP", embed_textures=False,
    use_mesh_modifiers=True, mesh_smooth_type="FACE",
)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "Nyaakoto_HeadCoat_V3_Study.blend"))

manifest = {
    "schema_version": 1,
    "identity": "Nyaakoto / ニャーコト connected-head and coat V3 source-only study",
    "production_status": "REVIEW_ONLY; no runtime integration, rig, or AAA qualification",
    "user_reference_sha256": USER_REFERENCE_SHA256,
    "user_reference_embedded": False,
    "v2_source_blend_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "texture_provenance": "Project-owned V2 unique-UV bake; color is retained and micro-normal/ORM are artist-derived, not scans",
    "scale": "meters; +X face forward; +Z up",
    "groom_strands": strand_count,
    "fbx": "SM_Nyaakoto_HeadCoat_V3_Study.fbx",
    "source_blend": "Nyaakoto_HeadCoat_V3_Study.blend",
    "map_conventions": "NormalGL for Blender; NormalDX for Unreal; ORM R=unbaked AO white, G=roughness, B=metallic zero",
    "files_sha256": {},
}
for path in sorted(ROOT.iterdir()):
    if path.is_file() and path.name not in {
        "manifest.json", "create_coat_maps.py", "create_coat_v3.py",
        "validate_coat_v3.py", "README.md",
    }:
        manifest["files_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print("NYAAKOTO_COAT_V3_COMPLETE", len(meshes), "meshes", strand_count, "groom splines")
