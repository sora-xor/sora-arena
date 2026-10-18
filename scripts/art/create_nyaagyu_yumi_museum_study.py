"""Build an original museum-dimensioned yumi/ya/ebira source-art study.

Run after build_nyaagyu_yumi_museum_maps.py with Blender 5.2+. Geometry and
materials are authored for this project. A museum dimension is not a complete
reconstruction: bow curvature, stave section, grip, steel point and ebira rack
details here are explicitly interpretive pending a specialist and draw test.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/HistoricalStudy"
TEX = OUT / "Textures"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
OUT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
assets = bpy.data.collections.new("Nyaagyu_Yumi_MuseumStudy_Editable")
scene.collection.children.link(assets)
review = bpy.data.collections.new("Review_Only")
scene.collection.children.link(review)


def pbr(name: str, family: str) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    src = {}
    for kind in ("Albedo", "NormalDX", "ORM"):
        img = bpy.data.images.load(str(TEX / f"{family}_{kind}.png"), check_existing=True)
        img.colorspace_settings.name = "sRGB" if kind == "Albedo" else "Non-Color"
        img.pack()
        n = nodes.new("ShaderNodeTexImage")
        n.name = f"{family}_{kind}"
        n.image = img
        src[kind] = n
    links.new(src["Albedo"].outputs["Color"], bsdf.inputs["Base Color"])
    orm = nodes.new("ShaderNodeSeparateColor")
    links.new(src["ORM"].outputs["Color"], orm.inputs["Color"])
    links.new(orm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(orm.outputs["Blue"], bsdf.inputs["Metallic"])
    # Source normal is DirectX; Blender's normal node expects +Y/OpenGL.
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(src["NormalDX"].outputs["Color"], channels.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(channels.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(channels.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(channels.outputs["Blue"], combine.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .65
    links.new(combine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


M_BAMBOO = pbr("M_Yumi_Museum_Bamboo", "Bamboo")
M_LACQUER = pbr("M_Yumi_Museum_BlackUrushi", "BlackLacquer")
M_RATTAN = pbr("M_Yumi_Museum_SplitRattan", "Rattan")
M_FEATHER = pbr("M_Yumi_Museum_Fletching", "Fletching")
M_IRON = pbr("M_Yumi_Museum_ForgedIron", "ForgedIron")


def plain(name, rgb, roughness, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*rgb, 1)
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Metallic"].default_value = metallic
    return mat


M_HORN = plain("M_Yumi_Museum_Horn", (.022, .018, .014), .29)
M_STRING = plain("M_Yumi_Museum_Tsuru", (.42, .37, .25), .82)
M_INDIGO = plain("M_Yumi_Museum_IndigoCloth", (.025, .045, .060), .84)
M_KAMON = plain("M_Yumi_Museum_KamonBrass", (.34, .22, .09), .38, .8)


def move_asset(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    assets.objects.link(obj)
    obj["asset_source"] = "Original project-authored Nyaagyu yumi museum study"
    return obj


def mesh(name, verts, faces, mats, face_materials=None, uv_faces=None, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    assets.objects.link(obj)
    for mat in mats:
        data.materials.append(mat)
    layer = data.uv_layers.new(name="UV0")
    for index, poly in enumerate(data.polygons):
        poly.use_smooth = smooth
        poly.material_index = 0 if face_materials is None else face_materials[index]
        coords = uv_faces[index] if uv_faces is not None else [
            ((i % 2), (i // 2) % 2) for i in range(len(poly.loop_indices))]
        for li, coord in zip(poly.loop_indices, coords):
            layer.data[li].uv = coord
    return move_asset(obj)


def box(name, loc, dim, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = move_asset(bpy.context.object)
    obj.name = name
    obj.dimensions = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("WornHandworkedEdges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def tube(name, points, radius, material, sides=8, closed=False):
    pts = [Vector(p) for p in points]
    count = len(pts)
    vertices, faces, uv_faces = [], [], []
    for i, pt in enumerate(pts):
        tangent = (pts[(i + 1) % count] - pts[(i - 1) % count]).normalized() if closed else (
            (pts[min(i + 1, count - 1)] - pts[max(i - 1, 0)]).normalized())
        axis = Vector((0, 1, 0)) if abs(tangent.dot(Vector((0, 1, 0)))) < .93 else Vector((1, 0, 0))
        right = tangent.cross(axis).normalized()
        up = tangent.cross(right).normalized()
        for side in range(sides):
            angle = 2 * math.pi * side / sides
            vertices.append(tuple(pt + radius * (right * math.cos(angle) + up * math.sin(angle))))
    segments = count if closed else count - 1
    for i in range(segments):
        nxt = (i + 1) % count
        for side in range(sides):
            s1 = (side + 1) % sides
            faces.append((i * sides + side, i * sides + s1, nxt * sides + s1, nxt * sides + side))
            uv_faces.append(((side / sides, i / segments), (s1 / sides, i / segments),
                             (s1 / sides, (i + 1) / segments), (side / sides, (i + 1) / segments)))
    if not closed:
        faces.extend([tuple(reversed(range(sides))), tuple((count - 1) * sides + s for s in range(sides))])
        uv_faces.extend([tuple((s / sides, 0) for s in reversed(range(sides))),
                         tuple((s / sides, 1) for s in range(sides))])
    return mesh(name, vertices, faces, [material], uv_faces=uv_faces)


# Agency for Cultural Affairs lists 195.3 cm total length for a 19th-century
# shigeto yumi. This study measures tip to tip, whereas its curved/strung pose
# is designed and not read from a measured scan of that accession.
BOW_LENGTH = 1.953
GRIP_FROM_LOWER = .66  # interpretive below-centre placement; not measured accession data
Z_LOW = -GRIP_FROM_LOWER
Z_HIGH = BOW_LENGTH - GRIP_FROM_LOWER
CONTROL = [
    (Z_LOW, -.005), (-.60, .038), (-.42, .075), (-.22, .046),
    (0, .0), (.22, .032), (.48, .094), (.70, .141),
    (.94, .125), (1.12, .056), (Z_HIGH, .022),
]


def profile(z):
    if z <= CONTROL[0][0]:
        return CONTROL[0][1]
    if z >= CONTROL[-1][0]:
        return CONTROL[-1][1]
    j = next(j for j in range(len(CONTROL) - 1) if CONTROL[j][0] <= z <= CONTROL[j + 1][0])
    a, b = CONTROL[j], CONTROL[j + 1]
    p = CONTROL[max(j - 1, 0)]
    q = CONTROL[min(j + 2, len(CONTROL) - 1)]
    t = (z - a[0]) / (b[0] - a[0])
    m0 = (b[1] - p[1]) / (b[0] - p[0]) * (b[0] - a[0])
    m1 = (q[1] - a[1]) / (q[0] - a[0]) * (b[0] - a[0])
    return ((2*t**3 - 3*t*t + 1) * a[1] + (t**3 - 2*t*t + t) * m0 +
            (-2*t**3 + 3*t*t) * b[1] + (t**3 - t*t) * m1)


def half_width(z):
    t = (z - Z_LOW) / BOW_LENGTH
    return .008 + .010 * (math.sin(math.pi * t) ** .6)


def half_thick(z):
    t = (z - Z_LOW) / BOW_LENGTH
    return .006 + .004 * (math.sin(math.pi * t) ** .7) + .002 * math.exp(-(z / .12) ** 2)


RING = [(-.50, -.32), (-.39, -.50), (.39, -.50), (.50, -.32),
        (.50, .32), (.39, .50), (-.39, .50), (-.50, .32)]
N_RING = 157
stave_vertices, stave_faces, stave_mats, stave_uv = [], [], [], []
for j in range(N_RING):
    z = Z_LOW + BOW_LENGTH * j / (N_RING - 1)
    for dx, dy in RING:
        stave_vertices.append((profile(z) + dx * 2 * half_thick(z),
                               dy * 2 * half_width(z), z))
for j in range(N_RING - 1):
    for k in range(8):
        kn = (k + 1) % 8
        stave_faces.append((j * 8 + k, j * 8 + kn, (j + 1) * 8 + kn, (j + 1) * 8 + k))
        stave_mats.append(0 if k in (0, 7) else 1 if k in (3, 4) else 2)
        stave_uv.append(((k / 8, j / (N_RING - 1)), (kn / 8, j / (N_RING - 1)),
                         (kn / 8, (j + 1) / (N_RING - 1)), (k / 8, (j + 1) / (N_RING - 1))))
stave_faces.extend([tuple(reversed(range(8))), tuple((N_RING - 1)*8+k for k in range(8))])
stave_mats.extend([2, 2])
stave_uv.extend([tuple((k/8, 0) for k in reversed(range(8))),
                 tuple((k/8, 1) for k in range(8))])
stave = mesh("Yumi_1953mm_LaminatedStave", stave_vertices, stave_faces,
             [M_BAMBOO, M_LACQUER, M_RATTAN], stave_mats, stave_uv)

# Fine independent dark glue-line/layer edges, following the actual limb curve.
for side in (-1, 1):
    line = []
    for j in range(123):
        z = Z_LOW + BOW_LENGTH * j / 122
        line.append((profile(z), side * (half_width(z) + .0002), z))
    tube(f"Yumi_LaminateEdge_{side:+d}", line, .00055, M_HORN, 6)

# Rattan coils follow the stave's changing section rather than an even cylinder.
for first, last, pitch in ((-.54, -.42, .012), (-.15, .17, .011),
                           (.44, .56, .012), (1.11, 1.21, .012)):
    n = round((last - first) / pitch) + 1
    for index in range(n):
        z = first + (last - first) * index / max(1, n - 1)
        points = []
        for k in range(9):
            a = 2 * math.pi * k / 8
            points.append((profile(z) + (half_thick(z) + .0012) * math.cos(a),
                           (half_width(z) + .0012) * math.sin(a), z + .001 * math.sin(a)))
        tube(f"Rattan_Binding_{first:+.2f}_{index:02d}", points[:-1], .00115,
             M_RATTAN, 6, closed=True)

# Indigo hand contact and carved shoulder nocks remain independent edit parts.
grip = box("Yumi_IndigoGripUnderRattan", (profile(0), 0, .012),
           (.025, .039, .19), M_INDIGO, .003)
for name, z, direction in (("Motohazu_Lower", Z_LOW, -1), ("Urahazu_Upper", Z_HIGH, 1)):
    tube(name + "_HornShoulder", [(profile(z), 0, z - direction*.010),
                                   (profile(z) + direction*.005, 0, z + direction*.014)],
         .0065, M_HORN, 10)
    tube(name + "_StringGrooveRim", [(profile(z) - .002, -.006, z + direction*.006),
                                     (profile(z) - .004, 0, z + direction*.008),
                                     (profile(z) - .002, .006, z + direction*.006)],
         .00075, M_RATTAN, 7)

string_points = [(profile(Z_LOW), 0, Z_LOW), (-.095, 0, -.42),
                 (-.135, 0, .04), (-.14, 0, .55), (-.11, 0, 1.02),
                 (profile(Z_HIGH), 0, Z_HIGH)]
tube("Tsuru_StrungDisplayOnly", string_points, .0013, M_STRING, 9)


# The Met 36.25.2554a-p gives the ebira's 584 x 130 x 103 mm envelope and
# twelve arrows 859-889 mm long. Its page supplies no image: the rack below is
# an original, openly marked design interpretation of an open ebira, not a copy.
QX = .53
box("Ebira_LacqueredBackboard", (QX, .040, .292), (.130, .012, .584), M_LACQUER, .004)
box("Ebira_PointDrawer", (QX, -.008, .049), (.130, .092, .088), M_LACQUER, .004)
box("Ebira_PointDrawer_Lip", (QX, -.057, .089), (.132, .006, .009), M_HORN, .001)
for side in (-1, 1):
    x = QX + side * .061
    tube(f"Ebira_CaneSideRail_{side:+d}", [(x, -.051, .045), (x, -.051, .58)],
         .0035, M_RATTAN, 8)
    for depth in (-.048, .039):
        tube(f"Ebira_VerticalRib_{side:+d}_{depth:+.3f}",
             [(x, depth, .10), (x, depth, .57)], .0018, M_RATTAN, 6)
for h in (.16, .28, .4, .52, .577):
    tube(f"Ebira_CrossRail_{h:.3f}", [(QX-.063, -.054, h), (QX+.063, -.054, h)],
         .0026, M_RATTAN, 7)
    tube(f"Ebira_BackCrossRail_{h:.3f}", [(QX-.063, .047, h), (QX+.063, .047, h)],
         .0021, M_RATTAN, 7)
for i in range(5):
    x = QX - .048 + i * .024
    tube(f"Ebira_ArrowComb_{i:02d}", [(x, -.05, .557), (x, .038, .557)],
         .002, M_HORN, 6)
for side in (-1, 1):
    x = QX + side * .046
    tube(f"Ebira_Lashing_{side:+d}", [(x, -.061, .12),
         (QX + side*.064, .005, .28), (x, -.061, .47)], .003, M_INDIGO, 8)

# Kamon comes from the user's exact original SVG path, scaled only. The motif
# is an in-world resistance badge, not an asserted historical family crest.
disc = box("Ebira_SORA_KamonBacking", (QX, -.064, .31),
           (.060, .003, .060), M_HORN, .003)
before = set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(LOGO))
bpy.context.view_layer.update()
svg_curves = [obj for obj in set(bpy.data.objects) - before if obj.type == "CURVE"]
assert len(svg_curves) == 2, len(svg_curves)
corners = [obj.matrix_world @ Vector(c) for obj in svg_curves for c in obj.bound_box]
lo_x, hi_x = min(v.x for v in corners), max(v.x for v in corners)
lo_y, hi_y = min(v.y for v in corners), max(v.y for v in corners)
scale = .046 / max(hi_x - lo_x, hi_y - lo_y)
cx, cy = (lo_x + hi_x)/2, (lo_y + hi_y)/2
for index, obj in enumerate(svg_curves):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    for vert in obj.data.vertices:
        p = obj.matrix_world @ vert.co
        vert.co = (QX + (p.x - cx)*scale, -.067,
                   .31 + (p.y - cy)*scale)
    obj.matrix_world.identity()
    move_asset(obj)
    obj.name = f"Ebira_UserSVG_SORA_KamonPath_{index}"
    obj.data.materials.clear()
    obj.data.materials.append(M_KAMON)
    obj["source_svg_sha256"] = hashlib.sha256(LOGO.read_bytes()).hexdigest()
    if not obj.data.uv_layers:
        layer = obj.data.uv_layers.new(name="UV0")
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                v = obj.data.vertices[obj.data.loops[li].vertex_index].co
                layer.data[li].uv = ((v.x - QX)/.046 + .5, (v.z-.31)/.046 + .5)


def feather(name, base, angle, z0, z1):
    # Tapered, curved feather vane with explicit thickness and a central rachis.
    x0, y0 = base
    radial = Vector((math.cos(angle), math.sin(angle), 0))
    normal = Vector((-math.sin(angle), math.cos(angle), 0))
    verts, faces, uv_faces = [], [], []
    sections = 15
    for layer in (-1, 1):
        for i in range(sections):
            t = i / (sections - 1)
            z = z0 + (z1-z0)*t
            width = .014 * math.sin(math.pi * t) ** .8
            centre = Vector((x0, y0, z)) + radial * (.003 + .006*t*t)
            for j in (-1, 0, 1):
                p = centre + normal * (j * width) + radial * (layer * .00035)
                verts.append(tuple(p))
    per_layer = sections * 3
    for layer in range(2):
        offset = layer * per_layer
        for i in range(sections - 1):
            for j in range(2):
                a = offset + i*3 + j
                b = offset + (i+1)*3 + j
                faces.append((a, a+1, b+1, b) if layer == 0 else (a, b, b+1, a+1))
                uv_faces.append(((j/2, i/(sections-1)), ((j+1)/2, i/(sections-1)),
                                 ((j+1)/2, (i+1)/(sections-1)), (j/2, (i+1)/(sections-1))))
    for i in range(sections-1):
        for edge in (0, 2):
            a = i*3+edge
            b = (i+1)*3+edge
            faces.append((a, b, per_layer+b, per_layer+a))
            uv_faces.append(((0, i/(sections-1)), (1, i/(sections-1)),
                             (1, (i+1)/(sections-1)), (0, (i+1)/(sections-1))))
    obj = mesh(name, verts, faces, [M_FEATHER], uv_faces=uv_faces)
    tube(name+"_Rachis", [(x0+radial.x*.003, y0+radial.y*.003, z0),
                           (x0+radial.x*.008, y0+radial.y*.008, z1)],
         .00055, M_HORN, 5)
    return obj


ARROW_LENGTH = .884  # near the Met object's 85.9-88.9 cm range
for a in range(12):
    col, row = a % 4, a // 4
    ax = QX - .043 + col * .028
    ay = -.031 + row * .029
    ztip = .031 + .0015 * (a % 3)
    ztop = ztip + ARROW_LENGTH
    # Slightly different fletch tones and apparent staggering without changing
    # the recorded arrow length or adding implausible broadhead flanges.
    tube(f"Ya_{a:02d}_YadakeBambooShaft", [(ax, ay, ztip+.028),
         (ax + (col-1.5)*.002, ay + (row-1)*.002, ztop-.008)], .0032, M_BAMBOO, 10)
    tube(f"Ya_{a:02d}_IronPoint", [(ax, ay, ztip), (ax, ay, ztip+.032)],
         .0025, M_IRON, 9)
    tube(f"Ya_{a:02d}_NockCollar", [(ax, ay, ztop-.015), (ax, ay, ztop)],
         .0036, M_HORN, 9)
    for vane in range(3):
        feather(f"Ya_{a:02d}_Hane_{vane}", (ax, ay),
                vane * 2*math.pi/3 + a*.08, ztop-.17, ztop-.028)


# Reviewer lighting is separated from exported geometry.
def review_obj(obj):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    review.objects.link(obj)
    return obj


floor_mat = plain("Review_CharcoalFloor", (.057, .066, .070), .9)
floor = box("ReviewFloor", (.22, 0, -.72), (3.0, 2.5, .035), floor_mat, .01)
review_obj(floor)


def area(name, loc, power, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    review.objects.link(obj)
    obj.location = loc
    direction = Vector((.23, 0, .40)) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


area("SoftboxKey", (1.8, -2.0, 3.1), 620, (1.0, .91, .80), 2.2)
area("ColdRim", (-1.6, 1.8, 2.7), 760, (.68, .79, 1.0), 1.5)
area("BambooFill", (-1.1, -1.6, .55), 240, (1.0, .95, .79), 1.3)
world = bpy.data.worlds.new("SoftDarkStudio")
scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.095,.106,.117,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .45

cam_data = bpy.data.cameras.new("ReviewCamera")
cam = bpy.data.objects.new("ReviewCamera", cam_data)
review.objects.link(cam)
scene.camera = cam
cam_data.type = "ORTHO"


def render(filename, location, target, scale, resolution):
    cam.location = location
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)


scene.render.engine = "BLENDER_EEVEE"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.color_mode = "RGBA"

# Stable product views, not in-engine material or frame-rate qualification.
render("Nyaagyu_Yumi_Ebira_Hero.png", (3.5, -5.2, 2.25), (.24, 0, .34), 2.42,
       (1500, 1500))
render("Nyaagyu_Yumi_Ebira_Detail.png", (1.5, -2.4, .83), (.52, 0, .45), .98,
       (1500, 1300))
render("Nyaagyu_Yumi_Profile.png", (2.6, -.35, 1.05), (.02, 0, .30), 2.35,
       (1000, 1400))

# Save the source scene before selected-mesh export. Review objects never ship.
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Nyaagyu_Yumi_Ebira_MuseumStudy.blend"))
bpy.ops.object.select_all(action="DESELECT")
for obj in assets.objects:
    obj.select_set(True)
active = next(obj for obj in assets.objects if obj.type == "MESH")
bpy.context.view_layer.objects.active = active
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_Nyaagyu_Yumi_Ebira_MuseumStudy.fbx"),
                         use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, bake_space_transform=False,
                         path_mode="RELATIVE", add_leaf_bones=False)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


artifacts = ["Nyaagyu_Yumi_Ebira_MuseumStudy.blend",
             "SM_Nyaagyu_Yumi_Ebira_MuseumStudy.fbx",
             "Nyaagyu_Yumi_Ebira_Hero.png", "Nyaagyu_Yumi_Ebira_Detail.png",
             "Nyaagyu_Yumi_Profile.png"]
textures = sorted(TEX.glob("*.png"))
manifest = {
    "schema_version": 1,
    "status": "source_only_unqualified_art_study",
    "runtime_integrated": False,
    "license": "Original project-authored mesh and textures; no paid assets or downloaded images",
    "units": "metres",
    "bow_tip_to_tip_m": BOW_LENGTH,
    "bow_grip_from_lower_tip_m": GRIP_FROM_LOWER,
    "quiver_envelope_m": [.584, .130, .103],
    "arrow_count": 12,
    "arrow_length_m": ARROW_LENGTH,
    "mesh_parts": len([o for o in assets.objects if o.type == "MESH"]),
    "triangle_count": sum(len(poly.vertices)-2 for obj in assets.objects if obj.type == "MESH" for poly in obj.data.polygons),
    "svg_sha256": sha(LOGO),
    "generator": "scripts/art/create_nyaagyu_yumi_museum_study.py",
    "generator_sha256": sha(Path(__file__)),
    "texture_generator": "scripts/art/build_nyaagyu_yumi_museum_maps.py",
    "texture_generator_sha256": sha(ROOT / "scripts/art/build_nyaagyu_yumi_museum_maps.py"),
    "artifacts": {name: sha(OUT / name) for name in artifacts},
    "textures": {p.name: sha(p) for p in textures},
    "source_references": [
        {"url": "https://online.bunka.go.jp/heritages/detail/388744", "use": "19th-century 195.3 cm shigeto bow; bamboo, wood, lacquer and rattan"},
        {"url": "https://www.metmuseum.org/art/collection/search/23966", "use": "Edo ebira envelope and 12 arrow lengths"},
        {"url": "https://www.clevelandart.org/art/1921.390", "use": "bamboo arrow shaft and three long feathers"},
        {"url": "https://hikone-castle-museum.jp/exhibition_old/6522.html", "use": "Edo warrior archery, laminated bows and quiver context"},
    ],
    "interpretations": ["strung limb profile and grip ratio", "nock shoulders and binding layout",
                        "quiver rack/drawer geometry without accession imagery", "arrow-point form and feather species"],
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print("NYAAGYU_YUMI_MUSEUM_STUDY_BUILT", manifest["mesh_parts"], manifest["triangle_count"])
