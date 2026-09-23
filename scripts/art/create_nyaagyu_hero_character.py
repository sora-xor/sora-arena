"""Author an original, editable Nyaakoto feline-samurai world-character study.

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
import bmesh
import numpy as np
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Characters/Hero"
NAME = "SM_Nyaagyu_HeroCharacter"
BLEND = OUT / "Nyaagyu_HeroCharacter.blend"
FBX = OUT / f"{NAME}.fbx"
PREVIEW = OUT / "Nyaagyu_HeroCharacter_Blender.png"
DETAIL = OUT / "Nyaagyu_HeroFace_Blender.png"
MANIFEST = OUT / "manifest.json"
EYE_DIR = OUT / "EyeStudy"
EYE_CLOSEUP = EYE_DIR / "Nyaakoto_Eye_Macro_Blender.png"
IRIS_TEXTURE = EYE_DIR / "T_Nyaakoto_Iris_Albedo.png"
OUT.mkdir(parents=True, exist_ok=True)
EYE_DIR.mkdir(parents=True, exist_ok=True)
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


FUR = mat("M_Hero_GreyTabbyFur", (.13,.15,.18), rough=.93, noise=125, bump=.00025)
FUR_DARK = mat("M_Hero_CharcoalStripeFur", (.045,.053,.063), rough=.92, noise=132, bump=.00019)
FUR_LIGHT = mat("M_Hero_WhiteFur", (.77,.80,.79), rough=.91, noise=112, bump=.00018)
EAR_INNER = mat("M_Hero_EarSkin", (.40,.17,.17), rough=.82, noise=83, bump=.00006)
NOSE = mat("M_Hero_RoseNose", (.42,.17,.18), rough=.47)
EYE = mat("M_Hero_BlueEye", (.16,.31,.43), rough=.36, coat=.12)
EYE_DARK = mat("M_Hero_EyePupil", (.008,.012,.013), rough=.12, coat=.38)
EYE_WHITE = mat("M_Hero_EyeGlint", (.78,.83,.86), rough=.15)
INDIGO = mat("M_Hero_IndigoSilk", (.016,.023,.045), rough=.80, noise=185, bump=.00013)
INDIGO_LIGHT = mat("M_Hero_FoldedIndigo", (.030,.041,.068), rough=.84, noise=190, bump=.00013)
KIMONO = mat("M_Hero_UndyedLinen", (.42,.37,.31), rough=.91, noise=185, bump=.00017)
LACQUER = mat("M_Hero_OxbloodUrushi", (.105,.011,.016), rough=.25, coat=.65, noise=58, bump=.00006)
LACQUER_DARK = mat("M_Hero_BlackUrushi", (.015,.014,.014), rough=.28, coat=.57, noise=62, bump=.00006)
IRON = mat("M_Hero_BlackenedIron", (.052,.057,.060), rough=.35, metal=.90, noise=107, bump=.00009)
BRASS = mat("M_Hero_AgedBrass", (.43,.25,.093), rough=.32, metal=.89, noise=89, bump=.00008)
SILVER = mat("M_Hero_BurnishedSteel", (.45,.51,.53), rough=.22, metal=.96, noise=109, bump=.00004)
CLAW = mat("M_Hero_IvoryClaw", (.63,.59,.48), rough=.43, noise=65)
TEAL = mat("M_Hero_JadeCircuit", (.016,.40,.34), rough=.25, metal=.19, emission=.35)
RESISTANCE_RED = mat("M_Hero_SORAResistanceRed", (.72,.036,.065), rough=.48)
SASH_RED = mat("M_Hero_ScarletSash", (.23,.011,.024), rough=.79, noise=168, bump=.00013)
BAMBOO = mat("M_Hero_YumiLaminatedBamboo", (.27,.15,.065), rough=.56, noise=93, bump=.00012)
ARROW = mat("M_Hero_BambooArrowShaft", (.48,.32,.17), rough=.72, noise=111, bump=.00008)
FLETCH = mat("M_Hero_RedArrowFletch", (.66,.050,.055), rough=.88, noise=118, bump=.00004)
STRING = mat("M_Hero_YumiSilkString", (.70,.66,.53), rough=.82)


def build_iris_texture():
    """Paint an original radial iris atlas rather than using a flat blue disc.

    The slight angular phase drift and broken fibres keep the iris legible at
    close review distance. The pupil and corneal bulge remain actual geometry.
    """
    size = 1024
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    xx = (xx - (size - 1) * .5) / (size * .48)
    yy = (yy - (size - 1) * .5) / (size * .48)
    radius = np.sqrt(xx * xx + yy * yy)
    angle = np.arctan2(yy, xx)
    drift = angle + .018 * np.sin(33 * angle + radius * 19)
    fine = .5 + .5 * np.sin(173 * drift + 9 * radius + 1.5 * np.sin(31 * angle))
    broad = .5 + .5 * np.sin(61 * drift - 11 * radius + .8 * np.sin(13 * angle))
    ring = .5 + .5 * np.sin(78 * radius + 4 * np.sin(15 * angle))
    rng = np.random.default_rng(290419)
    grain = rng.random((size, size), dtype=np.float32) - .5
    texture = np.empty((size, size, 4), dtype=np.float32)
    base = np.asarray((.095, .272, .355), dtype=np.float32)
    tone = (.69 + .27 * fine + .14 * broad + .045 * ring + .055 * grain)[..., None]
    color = base * tone
    blue_fibres = np.asarray((.095, .18, .22), dtype=np.float32)
    color += blue_fibres * np.clip((fine - .56) * 1.45, 0, 1)[..., None]
    inner = np.clip((.34 - radius) / .17, 0, 1)[..., None]
    color = color * (1 - inner * .47) + np.asarray((.19, .15, .08), dtype=np.float32) * inner * .47
    limbal = np.clip((radius - .78) / .18, 0, 1)[..., None]
    color = color * (1 - limbal * .86) + np.asarray((.012, .020, .027), dtype=np.float32) * limbal * .86
    texture[:, :, :3] = np.clip(color, 0, 1)
    texture[:, :, 3] = 1
    image = bpy.data.images.new("Nyaakoto_Iris_Painted_1024", width=size, height=size, alpha=True)
    image.pixels.foreach_set(texture.ravel())
    image.filepath_raw = str(IRIS_TEXTURE)
    image.file_format = "PNG"
    image.save()
    image.pack()
    nodes, links = EYE.node_tree.nodes, EYE.node_tree.links
    pigment = nodes.new("ShaderNodeTexImage")
    pigment.name = "Painted radial iris pigment"
    pigment.image = image
    pigment.interpolation = "Linear"
    bsdf = nodes.get("Principled BSDF")
    links.new(pigment.outputs["Color"], bsdf.inputs["Base Color"])
    relief = nodes.new("ShaderNodeBump")
    relief.inputs["Strength"].default_value = .15
    relief.inputs["Distance"].default_value = .00005
    links.new(pigment.outputs["Color"], relief.inputs["Height"])
    links.new(relief.outputs["Normal"], bsdf.inputs["Normal"])


build_iris_texture()


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


def eye_basis(sign):
    """Face-forward eye tangent with a modest outward gaze for each cheek."""
    vertical = Vector((0, 0, 1))
    horizontal = Vector((-sign * .18, .984, 0)).normalized()
    normal = horizontal.cross(vertical).normalized()
    origin = Vector((.205, sign * .084, 1.672))
    return origin, horizontal, vertical, normal


def eye_patch(name, sign, width, height, depth, crown, material,
              rings=10, segments=96, thickness=0):
    """UV-mapped convex ocular disc seated on the anatomical eyeball."""
    origin, horizontal, vertical, normal = eye_basis(sign)
    vertices = [origin + normal * (depth + crown)]
    coordinates = [(0.5, 0.5)]
    faces = []
    for ring in range(1, rings + 1):
        radius = ring / rings
        for angle_index in range(segments):
            angle = math.tau * angle_index / segments
            u, v = radius * math.cos(angle), radius * math.sin(angle)
            point = (origin + horizontal * (width * u) + vertical * (height * v)
                     + normal * (depth + crown * (1 - radius * radius)))
            vertices.append(point)
            coordinates.append((.5 + .48 * u, .5 + .48 * v))
    for index in range(segments):
        faces.append((0, 1 + index, 1 + (index + 1) % segments))
    for ring in range(rings - 1):
        lo = 1 + ring * segments
        hi = lo + segments
        for index in range(segments):
            j = (index + 1) % segments
            faces.append((lo + index, hi + index, hi + j, lo + j))
    obj = smooth(surface(name, vertices, faces, material, thickness=thickness))
    # Unreal samples UV channel 0 in the shared PBR master.  Joined Blender
    # meshes can have several named layers, so authored pigment coordinates
    # must occupy the same primary layer as the other source parts.
    uv = obj.data.uv_layers.new(name="UVMap")
    for loop in obj.data.loops:
        uv.data[loop.index].uv = coordinates[loop.vertex_index]
    return obj


def eye_lid(name, sign, upper, material, radius):
    origin, horizontal, vertical, normal = eye_basis(sign)
    points = []
    for u in (-1.0, -.7, -.35, 0.0, .35, .7, 1.0):
        arch = max(0.0, 1.0 - u * u) ** .72
        z = (.013 if upper else -.010) * arch + .0015 * u
        points.append(origin + horizontal * (.023 * u) + vertical * z
                      + normal * (.008 - .002 * u * u))
    return line(name, points, radius, material, 3)


def lower_lid_shelf(sign):
    """A narrow furred lower lid joins the globe to the cheek instead of a wire rim."""
    origin, horizontal, vertical, normal = eye_basis(sign)
    vertices = []
    faces = []
    for index in range(17):
        u = -1 + index / 8
        arch = max(0, 1 - u * u) ** .72
        rim_z = -.010 * arch + .0015 * u
        vertices.extend((
            origin + horizontal * (.023 * u) + vertical * rim_z
            + normal * (.0078 - .002 * u * u),
            origin + horizontal * (.026 * u) + vertical * (rim_z - .0065 * arch - .002)
            + normal * (.0025 - .001 * u * u),
        ))
        if index:
            a = (index - 1) * 2
            faces.append((a, a + 1, a + 3, a + 2))
    return smooth(surface(f"Eye_lower_lid_shelf_{sign}", vertices, faces, FUR))


def surface_fur_cards(name, source, material, count, seed, accept=None,
                      length=(.0018, .0050), width=(.00008, .00022)):
    """Root directional mesh fur on the deformed skin, preserving its outline."""
    rng = random.Random(seed)
    mesh = source.data
    mesh.calc_loop_triangles()
    triangles = [
        tri for tri in mesh.loop_triangles
        if tri.area > 1e-10 and (accept is None or accept(
            source.matrix_world @ mesh.vertices[tri.vertices[0]].co, tri))
    ]
    assert triangles, name
    weights = [tri.area for tri in triangles]
    vertices, faces = [], []
    for tri in rng.choices(triangles, weights=weights, k=count):
        a, b, c = (mesh.vertices[index].co for index in tri.vertices)
        u, v = rng.random(), rng.random()
        if u + v > 1:
            u, v = 1-u, 1-v
        normal = tri.normal.normalized()
        root = source.matrix_world @ (a + (b-a)*u + (c-a)*v + normal*.00013)
        normal = (source.matrix_world.to_3x3() @ normal).normalized()
        growth = (normal*.54 + Vector((-.17, .09 if root.y > 0 else -.09, -.68))).normalized()
        tangent = normal.cross(growth)
        if tangent.length < .01:
            tangent = Vector((0,1,0))
        tangent.normalize()
        half_width = rng.uniform(*width)
        fiber_length = rng.uniform(*length)
        index = len(vertices)
        vertices.extend((root-tangent*half_width, root+tangent*half_width,
                         root+growth*fiber_length))
        faces.append((index,index+1,index+2))
    return surface(name, vertices, faces, material)


def tapered_whisker(name, points, material, width=.00029):
    """A curved, narrowing vibrissa with a visibly rooted but fine tip."""
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = width
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for control, point, radius in zip(spline.bezier_points, points,
                                      (1.0, .80, .42, .045)):
        control.co = point
        control.handle_left_type = "AUTO"
        control.handle_right_type = "AUTO"
        control.radius = radius
    whisker = bpy.data.objects.new(name, curve)
    parts.objects.link(whisker)
    curve.materials.append(material)
    bpy.ops.object.select_all(action="DESELECT")
    whisker.select_set(True)
    bpy.context.view_layer.objects.active = whisker
    bpy.ops.object.convert(target="MESH")
    return smooth(bpy.context.object)


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
    """Curved, thick pinna with a recessed fossa and irregular furred margin."""
    levels = (
        # z, lateral center, half-width, front depth, back depth
        (1.662, .151, .056, .082, .010),
        (1.686, .151, .076, .105, .011),
        (1.714, .153, .078, .103, .014),
        (1.742, .155, .073, .097, .015),
        (1.770, .157, .064, .088, .017),
        (1.796, .159, .053, .077, .019),
        (1.820, .162, .039, .063, .020),
        (1.841, .164, .023, .050, .022),
        (1.858, .166, .008, .038, .025),
    )
    columns = 13
    vertices = []
    for z, cy, half_width, front_x, back_x in levels:
        for depth in (0, 1):
            for index in range(columns):
                q = -1 + 2*index/(columns-1)
                x = (front_x - .018*(1-q*q) + .008*q*q) if depth == 0 else (
                    back_x - .004*(1-q*q))
                vertices.append((x, sign*(cy+q*half_width), z))
    faces = []
    stride = columns*2
    for level in range(len(levels)-1):
        a, b = level*stride, (level+1)*stride
        for index in range(columns-1):
            faces.append((a+index, a+index+1, b+index+1, b+index))
            faces.append((a+columns+index+1, a+columns+index,
                          b+columns+index, b+columns+index+1))
        for edge in (0, columns-1):
            faces.append((a+edge, b+edge, b+columns+edge, a+columns+edge))
    for edge in range(columns-1):
        faces.append((edge, columns+edge, columns+edge+1, edge+1))
        top=(len(levels)-1)*stride
        faces.append((top+edge+1, top+columns+edge+1, top+columns+edge, top+edge))
    outer=smooth(surface(f"Ear_outer_{sign}", vertices, faces, FUR))
    # A separate conformal lining keeps the existing ear-skin material slot
    # while avoiding a flat pink triangular decal.
    inner_vertices, inner_faces = [], []
    for z, cy, half_width, front_x, _ in levels[1:-1]:
        for index in range(9):
            q=(-.59+1.18*index/8)
            inner_vertices.append((front_x-.018*(1-q*q)+.008*q*q+.0014,
                                   sign*(cy+q*half_width), z))
    for row in range(len(levels)-3):
        for index in range(8):
            a=row*9+index
            inner_faces.append((a,a+1,a+10,a+9))
    inner=smooth(surface(f"Ear_inner_{sign}", inner_vertices, inner_faces, EAR_INNER))
    surface_fur_cards(f"Ear_inner_fur_{sign}",inner,FUR_LIGHT,220,1400+sign,
                      length=(.003,.008),width=(.00006,.00015))
    rim_vertices, rim_faces = [], []
    rng=random.Random(1061+sign)
    for z, cy, half_width, front_x, _ in levels[1:]:
        for side in (-1,1):
            for index in range(10):
                q=side*rng.uniform(.72,.97)
                root=Vector((front_x-.018*(1-q*q)+.008*q*q+.002,
                             sign*(cy+q*half_width),z+rng.uniform(-.003,.003)))
                tip=root+Vector((-.003,sign*side*rng.uniform(.002,.006),
                                 rng.uniform(.004,.012)))
                width=rng.uniform(.00010,.00025)
                a=len(rim_vertices)
                rim_vertices.extend((root+Vector((0,width,0)),
                                     root-Vector((0,width,0)),tip))
                rim_faces.append((a,a+1,a+2))
    surface(f"Ear_rim_fur_{sign}", rim_vertices, rim_faces, FUR_LIGHT)
    return outer


# A grounded bipedal feline body, with separate jacket, neck and hakama panels.
ring_loft("Linen_under_kimono",[(.80,-.015,.16,.18),(.94,-.018,.19,.225),(1.15,-.02,.19,.24),(1.34,-.01,.145,.18)],KIMONO)
haori=ring_loft("Indigo_samurai_haori",[(.85,-.024,.205,.255),(.99,-.024,.23,.29),
                                       (1.20,-.02,.225,.28),(1.38,-.01,.16,.20),
                                       (1.455,.015,.128,.150)],INDIGO_LIGHT)
# A crossed kimono opening falls at the throat while the raised side/back
# collar conceals the rigid neck joint. Avoid a straight turtleneck rim.
for vertex in haori.data.vertices:
    front=max(0,min(1,(vertex.co.x-.015)/.125))
    top=max(0,min(1,(vertex.co.z-1.38)/.075))
    vertex.co.z-=.055*front*top
haori.data.update()
ring_loft("Layered_hakama_waist",[(.68,-.015,.19,.245),(.77,-.015,.19,.245),(.87,-.015,.205,.26)],INDIGO,pleats=.035)
neck_rings=(
    # z, forward center, fore-aft radius, lateral radius
    (1.285,.012,.107,.136),(1.326,.013,.111,.134),
    (1.366,.018,.108,.125),(1.405,.023,.098,.112),
    (1.444,.028,.094,.105),(1.482,.032,.101,.113),
    (1.519,.035,.105,.123),(1.550,.031,.103,.129),
)
neck_vertices,neck_faces=[],[]
neck_sides=64
for z,x0,rx,ry in neck_rings:
    for index in range(neck_sides):
        angle=math.tau*index/neck_sides
        neck_vertices.append((x0+rx*math.cos(angle),ry*math.sin(angle),z))
for row in range(len(neck_rings)-1):
    for index in range(neck_sides):
        a=row*neck_sides+index
        b=row*neck_sides+(index+1)%neck_sides
        neck_faces.append((a,b,b+neck_sides,a+neck_sides))
neck=smooth(surface("Fur_neck",neck_vertices,neck_faces,FUR))
neck.data.materials.append(FUR_LIGHT)
neck_uv=neck.data.uv_layers.new(name="UVMap")
for loop in neck.data.loops:
    point=neck.data.vertices[loop.vertex_index].co
    neck_uv.data[loop.index].uv=(math.atan2(point.y,point.x)/math.tau+.5,
                                 (point.z-1.28)/.29)
for face in neck.data.polygons:
    point=face.center
    # The visible throat is white all the way around its front and sides;
    # the grey join lies behind the neck under the haori collar.
    face.material_index=int(point.x>-.025)
neck.data.update()
surface_fur_cards("Fur_neck_mesh_fur_grey",neck,FUR,560,530,
                  accept=lambda p,tri: neck.data.polygons[tri.polygon_index].material_index==0,
                  length=(.003,.009))
surface_fur_cards("Fur_neck_mesh_fur_white",neck,FUR_LIGHT,1100,531,
                  accept=lambda p,tri: neck.data.polygons[tri.polygon_index].material_index==1,
                  length=(.004,.012))

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
    sphere(f"Shoulder_joint_{sign}",(.0,sy*.277,1.275),(.087,.108,.104),INDIGO)
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
box("Resistance_sash_band",(.016,0,.861),(.394,.538,.058),SASH_RED,.010)
box("Resistance_sash_hip_knot",(.207,-.206,.853),(.066,.094,.073),SASH_RED,.012)
surface("Resistance_sash_long_tail",[(.229,-.245,.836),(.227,-.137,.839),(.234,-.120,.539),(.230,-.236,.585)],[(0,1,2,3)],SASH_RED,thickness=.004)
surface("Resistance_sash_short_tail",[(.230,-.239,.838),(.230,-.140,.839),(.226,-.122,.668),(.225,-.239,.695)],[(0,1,2,3)],SASH_RED,thickness=.004)
box("Obi_burnished_plate",(.215,0,.858),(.023,.146,.091),BRASS,.009)
sphere("Clan_mon_roundel",(.230,0,.858),(.010,.051,.046),LACQUER_DARK,24,16)
line("Under_kimono_cross_collar_a",[(.163,-.14,1.356),(.188,.04,1.20),(.192,.129,1.102)],.020,KIMONO)
line("Under_kimono_cross_collar_b",[(.165,.14,1.355),(.193,-.025,1.205),(.197,-.110,1.13)],.018,INDIGO)

# Use the user's exact SVG paths for every clan crest. The vector source is
# read byte-for-byte; no rays or procedural substitute are allowed as kamon.
logo_svg=ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
logo_record=json.loads((logo_svg.parent/"sora_logo_manifest.json").read_text())
assert hashlib.sha256(logo_svg.read_bytes()).hexdigest()==logo_record["source_sha256"]

def sora_kamon(name, center, diameter, material):
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(logo_svg))
    curves=[o for o in set(bpy.data.objects)-before if o.type=="CURVE"]
    assert len(curves)==2,[o.name for o in curves]
    corners=[o.matrix_world @ Vector(c) for o in curves for c in o.bound_box]
    lo_x=min(v.x for v in corners);hi_x=max(v.x for v in corners)
    lo_y=min(v.y for v in corners);hi_y=max(v.y for v in corners)
    origin=((lo_x+hi_x)/2,(lo_y+hi_y)/2)
    scale=diameter/max(hi_x-lo_x,hi_y-lo_y)
    for index,o in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.convert(target="MESH")
        o=bpy.context.object
        for vert in o.data.vertices:
            p=o.matrix_world @ vert.co
            vert.co=(center[0],center[1]+(p.x-origin[0])*scale,
                     center[2]+(p.y-origin[1])*scale)
        o.matrix_world.identity()
        for c in tuple(o.users_collection):
            c.objects.unlink(o)
        parts.objects.link(o)
        o.name=f"UserSupplied_SORAKamon_{name}_Path_{index}"
        o.data.materials.clear()
        o.data.materials.append(material)
        o["source_svg_sha256"]=logo_record["source_sha256"]

bone("Resistance_insignia_backing",(.222,-.108,1.207),(.230,-.108,1.207),.044,.044,LACQUER_DARK,32)
sora_kamon("chest",(.235,-.108,1.207),.069,RESISTANCE_RED)
sora_kamon("waist",(.245,0,.858),.068,RESISTANCE_RED)
for sign in (-1,1):
    bone(f"Sode_kamon_backing_{sign}",(.116,sign*.345,1.325),(.121,sign*.345,1.325),.032,.032,LACQUER_DARK,24)
    sora_kamon(f"sode_{sign}",(.126,sign*.345,1.325),.052,BRASS)

# The skull carries cheek, whisker-pad, lip and chin volumes in one skin.  The
# lower white region is a material assignment on that same mesh, rather than
# separate white spheres pasted in front of the face.  It remains a rigid
# source-art study; production facial deformation and grooming are outstanding.
head_start=set(parts.objects)
skull=sphere("Skull",(.037,0,1.642),(.187,.196,.188),FUR,128,80)
for vertex in skull.data.vertices:
    p=vertex.co
    front=max(0,min(1,(p.x-.025)/.105))
    cheek=math.exp(-((p.z+.045)/.060)**2)
    p.y *= 1+.105*cheek-.09*max(0,-p.z/.19)
    p.z -= .020*math.exp(-((p.z-.150)/.055)**2)
    # Broad malar planes converge into two softly raised mystacial regions.
    # Their shared vertices preserve continuity through nose bridge and chin.
    pad=math.exp(-((p.z+.090)/.050)**2-((abs(p.y)-.050)/.072)**2)
    bridge=math.exp(-((p.z+.044)/.082)**2-(p.y/.061)**2)
    chin=math.exp(-((p.z+.139)/.035)**2-(p.y/.066)**2)
    p.x += front*(.071*pad+.028*bridge+.038*chin)
    p.x += .007*math.exp(-((p.z-.060)/.040)**2)*front
    p.x -= .010*max(0,-p.z/.19)
    # Seat the globes under the brow instead of laying them on a round forehead.
    for eye_sign in (-1, 1):
        orbital = math.exp(-(((p.y-eye_sign*.084)/.041)**2
                             + ((p.z-.030)/.029)**2)*1.4)
        p.x -= .008*orbital*max(0,min(1,(p.x-.08)/.10))
skull.data.update()
bm=bmesh.new()
bm.from_mesh(skull.data)
# Refine only the tabby-to-white boundary, rather than multiplying the whole
# skull's polygon budget. Material classification then has sub-centimeter
# triangles at the exposed side of the face.
seam_edges=[]
for edge in bm.edges:
    positions=[skull.matrix_world @ vert.co for vert in edge.verts]
    if any(p.x>.065 and 1.574<p.z<1.638 for p in positions):
        seam_edges.append(edge)
bmesh.ops.subdivide_edges(bm,edges=seam_edges,cuts=2,use_grid_fill=True)
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method="BEAUTY")
bm.to_mesh(skull.data)
bm.free()
skull.data.materials.append(FUR_LIGHT)
for face in skull.data.polygons:
    point=skull.matrix_world @ face.center
    x,y,z=point
    white_edge=1.605+.019*math.exp(-((abs(y)-.095)/.055)**2)-.017*(abs(y)/.19)**2
    # The connected white muzzle flows into the front of the jaw.  Brow and
    # flank remain tabby; short white fibers later break the hard color edge.
    face.material_index=int(x>.074 and abs(y)<.184 and z<white_edge)
skull.data.update()

def tabby_fiber_patches():
    """Root broken tabby bands on the actual sculpted skull surface."""
    rng=random.Random(1897)
    skull.data.calc_loop_triangles()
    triangles=[tri for tri in skull.data.loop_triangles
               if tri.area>1e-10 and skull.data.polygons[tri.polygon_index].material_index==0
               and (skull.matrix_world @ skull.data.vertices[tri.vertices[0]].co).x>.040]
    weights=[tri.area for tri in triangles]
    vertices,faces=[],[]
    for tri in rng.choices(triangles,weights=weights,k=60000):
        a,b,c=(skull.data.vertices[index].co for index in tri.vertices)
        u,v=rng.random(),rng.random()
        if u+v>1:u,v=1-u,1-v
        n=(skull.matrix_world.to_3x3() @ tri.normal).normalized()
        p=skull.matrix_world @ (a+(b-a)*u+(c-a)*v+tri.normal*.00045)
        x,y,z=p
        ay=abs(y)
        forehead=x>.105 and z>1.684 and any(
            abs(ay-(.028+band*.043+max(0,z-1.72)*.13))<.0075
            for band in range(3))
        cheek=x>.055 and ay>.105 and 1.56<z<1.70 and any(
            abs(z-(1.595+band*.036-(ay-.105)*.28))<.007
            for band in range(3))
        if not (forehead or cheek):
            continue
        tangent=n.cross(Vector((0,0,1)))
        if tangent.length<.1:
            tangent=Vector((0,1,0))
        tangent.normalize()
        width=rng.uniform(.00018,.00043)
        growth=(Vector((-.18,math.copysign(.24,y),-.73))+n*.22).normalized()
        tip=p+growth*rng.uniform(.004,.007)
        index=len(vertices)
        vertices.extend((p-tangent*width,p+tangent*width,tip))
        faces.append((index,index+1,index+2))
    return surface("Head_tabby_stripe_fibers",vertices,faces,FUR_DARK)

tabby_fiber_patches()
surface_fur_cards("Head_short_mesh_fur",skull,FUR,6000,781,
                  accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==0)
surface_fur_cards("Head_face_mesh_fur",skull,FUR,3500,973,
                  accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==0
                  and p.x>.10)
surface_fur_cards("Head_white_mesh_fur",skull,FUR_LIGHT,2200,974,
                  accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==1)
surface_fur_cards("Head_transition_mesh_fur",skull,FUR,2700,975,
                  accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==0
                  and p.x>.07 and abs(p.z-(1.605+.019*math.exp(-((abs(p.y)-.095)/.055)**2)
                                                 -.017*(abs(p.y)/.19)**2))<.015,
                  length=(.005,.011),width=(.00007,.00018))
for sign in (-1,1):
    ear(sign)
    surface_fur_cards(f"Cheek_mesh_fur_{sign}",skull,FUR_LIGHT,850,sign+234,
                      accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==1
                      and p.y*sign>.070 and p.z>1.51,
                      length=(.003,.008))
    surface_fur_cards(f"Muzzle_mesh_fur_{sign}",skull,FUR_LIGHT,950,791+sign,
                      accept=lambda p,tri: skull.data.polygons[tri.polygon_index].material_index==1
                      and p.y*sign>.012 and p.x>.175 and p.z>1.51,
                      length=(.0015,.004))
    sphere(f"Eye_socket_{sign}",(.204,sign*.084,1.672),(.003,.023,.014),EYE_DARK,56,36)
    # Keep the sclera as a narrow, partly covered crescent at the canthus.
    # A bright full circle would turn the feline eye into a cartoon human eye.
    eye_patch(f"Eye_scleral_crescent_{sign}",sign,.0215,.014,.0071,.0007,
              EYE_WHITE,rings=4,segments=80)
    eye_patch(f"Eye_iris_{sign}",sign,.0195,.013,.008,.0015,EYE)
    eye_patch(f"Eye_vertical_pupil_{sign}",sign,.0028,.0095,.010,.001,EYE_DARK,6,48)
    # The current UE master is opaque. Keep this a small highlight until a
    # dedicated transparent cornea can be authored and qualified on both GPUs.
    sphere(f"Corneal_glint_{sign}",(.216,sign*.073,1.680),
           (.001,.002,.0025),EYE_WHITE,12,8)
    eye_lid(f"Eye_upper_tarsal_margin_{sign}",sign,True,FUR_DARK,.00175)
    eye_lid(f"Eye_lower_tarsal_margin_{sign}",sign,False,FUR_DARK,.0014)
    lower_lid_shelf(sign)
    eye_lid(f"Eye_upper_wetline_{sign}",sign,True,EYE_WHITE,.00042)
    sphere(f"Eye_lacrimal_corner_{sign}",(.211,sign*.061,1.670),
           (.0017,.0021,.0017),EAR_INNER,16,12)
    line(f"Angular_brow_{sign}",[(.174,sign*.044,1.724),(.184,sign*.086,1.729),
                                  (.168,sign*.127,1.716)],.0014,FUR_DARK,2)
    whisker_roots = []
    for row in range(3):
        for col in range(4):
            x = .255 - .006 * row - .009 * col
            y = .034 + .015 * col + .002 * (row % 2)
            z = 1.573 - .014 * row + .002 * (col % 2)
            sphere(f"Muzzle_follicle_{sign}_{row}_{col}",
                   (x,sign*y,z),(.0010,.0013,.0011),FUR_DARK,10,8)
            whisker_roots.append((row,col,x,y,z))
    long_roots = [whisker_roots[index] for index in (0,1,2,4,5,6,8,9)]
    for whisker,(row,col,x,y,z) in enumerate(long_roots):
        lift = (.028, .021, .012, .006, -.002, -.014, -.026, -.038)[whisker]
        spread = .251 + .015 * (col % 3) + .009 * row
        tapered_whisker(f"Whisker_{sign}_{whisker}",(
            (x, sign*y, z),
            (x-.015, sign*(y+.047), z+lift*.21),
            (.132-.011*row, sign*(y+.145), z+lift*.70),
            (.070-.010*row, sign*spread, z+lift)),FUR_LIGHT)
    for whisker in range(42):
        rng=random.Random(240+sign*100+whisker)
        a=rng.uniform(-.55,.55)
        y=sign*(.151+rng.uniform(-.017,.017))
        z=1.55+rng.uniform(-.049,.055)
        line(f"Guard_hair_{sign}_{whisker}",[(.075,y,z),(.040,y+sign*.033,z+a*.027)],.00035,FUR_LIGHT,1)
# A rounded, hairless nasal planum has a broad dorsal edge, tapering ventral
# tip and two separate nares. A grooved philtrum reaches the split upper lip.
nose=sphere("Triangular_nose",(.276,0,1.579),(.009,.022,.012),NOSE,48,32)
for vertex in nose.data.vertices:
    height = max(0,min(1,(vertex.co.z+.012)/.024))
    vertex.co.y *= .33+.67*height**.8
    vertex.co.x += .002*(1-height)
for sign in (-1,1):
    sphere(f"Triangular_nose_naris_{sign}",(.284,sign*.011,1.578),
           (.0007,.0025,.0018),FUR_DARK,16,10)
line("Philtrum",[(.285,0,1.566),(.281,0,1.551),(.274,0,1.538)],.00065,FUR_DARK)
for sign in (-1,1):
    line(f"Mouth_upper_lip_{sign}",[(.274,0,1.538),(.271,sign*.017,1.532),
         (.254,sign*.037,1.535),(.228,sign*.054,1.544)],.00055,FUR_DARK)

# No helmet or headband hides the upright ears and distinctive tabby face in
# the user's Nyaakoto reference. The asymmetric small crown stripes remain fur.

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
# A sheathed katana's wrapped hilt projects forward from the left hip; the
# blade is never modelled as an exposed back-scabbard or fantasy straight sword.
line("Katana_tsuka_sheathed",[(-.105,-.310,.925),(.058,-.331,1.021),(.247,-.351,1.120)],.019,FUR_LIGHT)
sphere("Katana_tsuba_iron",(-.101,-.312,.928),(.024,.049,.051),IRON,24,14)
for i in range(8):
    t=i/8
    x=-.073+t*.290
    z=.946+t*.170
    line(f"Katana_tsukamaki_cross_{i}",[(x,-.351,z-.017),(x+.024,-.355,z+.018)],.003,INDIGO)
sphere("Katana_kashira",(.251,-.352,1.125),(.023,.024,.023),IRON,18,12)

# The open ebira is a source-art interpretation of the Japanese quiver type
# documented by the British Museum. Six bamboo shafts show red fletching above
# the shoulder, as in the supplied Nyaakoto image. Nocks point upward.
box("Ebira_lacquer_backboard",(-.230,-.340,1.134),(.030,.213,.374),LACQUER_DARK,.009)
for z in (.984,1.099,1.218,1.321):
    line(f"Ebira_rattan_crossbar_{z}",[(-.245,-.448,z),(-.259,-.338,z),(-.245,-.232,z)],.008,BAMBOO)
for y in (-.437,-.243):
    line(f"Ebira_lacing_{y}",[(-.227,y,.947),(-.239,y,1.327)],.005,SASH_RED)
line("Ebira_shoulder_strap",[(-.227,-.329,1.29),(-.065,-.213,1.39),(.145,.130,1.25)],.012,INDIGO)
for index in range(6):
    y=-.420+index*.033
    x=-.266-(index%2)*.011
    z_top=1.727+index*.012
    bone(f"Ya_bamboo_shaft_{index}",(x,y,1.05),(x+.005,y,z_top),.0042,.0042,ARROW,10)
    bone(f"Ya_nock_{index}",(x+.005,y,z_top-.009),(x+.005,y,z_top+.012),.006,.006,IRON,10)
    for side in (-1,1):
        offset=side*.022
        surface(f"Ya_red_fletch_{index}_{side}",
                [(x+.005,y,z_top-.078),(x+.006,y+offset,z_top-.030),
                 (x+.005,y,z_top+.006)],[(0,1,2)],FLETCH,thickness=.001)

# A long asymmetric yumi is carried beside the back, clear of the cat's face.
# The ~2.2 m laminated-bamboo silhouette and grip about one-third from the
# lower tip follow the All Japan Kyudo Federation equipment proportions; the
# placement is a static review pose, not a claim of historical carry mechanics.
yumi_points=[(-.405,-.505,.045),(-.483,-.517,.37),(-.520,-.520,.69),
             (-.471,-.524,1.020),(-.451,-.526,1.380),(-.364,-.522,1.780),
             (-.215,-.511,2.178)]
line("Yumi_laminated_bamboo",yumi_points,.010,BAMBOO,5)
line("Yumi_silk_string",[yumi_points[0],(-.222,-.531,1.085),yumi_points[-1]],.0017,STRING,2)
line("Yumi_lower_grip_wrap",[(-.521,-.520,.640),(-.518,-.520,.736)],.016,INDIGO,4)
for i in range(5):
    z=.644+i*.022
    line(f"Yumi_grip_rattan_{i}",[(-.539,-.533,z),(-.502,-.533,z+.006)],.0026,BRASS)
for index,point in enumerate((yumi_points[0],yumi_points[-1])):
    sphere(f"Yumi_horn_nock_{index}",point,(.012,.011,.017),IRON,14,10)

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
# FBX carries native material slots into Unreal, while its absolute image paths
# would leak a workstation directory. The project-owned atlas is packed in the
# editable .blend and imported to UE separately; omit its node for this export.
iris_nodes, iris_links = EYE.node_tree.nodes, EYE.node_tree.links
iris_node = iris_nodes["Painted radial iris pigment"]
iris_nodes.remove(iris_node)
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,object_types={"MESH"},
                         apply_unit_scale=True,global_scale=1.0,axis_forward="-Y",
                         axis_up="Z",path_mode="STRIP",add_leaf_bones=False,bake_anim=False)
iris_node = iris_nodes.new("ShaderNodeTexImage")
iris_node.name = "Painted radial iris pigment"
iris_node.image = bpy.data.images["Nyaakoto_Iris_Painted_1024"]
iris_links.new(iris_node.outputs["Color"], iris_nodes["Principled BSDF"].inputs["Base Color"])
iris_links.new(iris_node.outputs["Color"], iris_nodes["Bump"].inputs["Height"])
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
camera.location=(.50,-.33,1.79)
camera.rotation_euler=(Vector((.180,-.071,1.665))-camera.location).to_track_quat("-Z","Y").to_euler()
camera_data.ortho_scale=.24
scene.render.resolution_x=1200;scene.render.resolution_y=900
scene.render.filepath=str(EYE_CLOSEUP)
bpy.ops.render.render(write_still=True)
camera_data.ortho_scale=2.45
camera.location=(3.0,-4.4,2.44)
camera.rotation_euler=(Vector((0,0,1.02))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.resolution_x=1200;scene.render.resolution_y=1400
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest={
    "schema_version":2,
    "name":NAME,
    "character_name_ja":"ニャーコト",
    "character_name_en":"Nyaakoto",
    "generator":"scripts/art/create_nyaagyu_hero_character.py",
    "validator":"scripts/art/validate_nyaagyu_hero_character.py",
    "source_blend":BLEND.name,"blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "preview":PREVIEW.name,"preview_sha256":sha(PREVIEW),
    "detail_preview":DETAIL.name,"detail_preview_sha256":sha(DETAIL),
    "eye_macro":str(EYE_CLOSEUP.relative_to(OUT)),"eye_macro_sha256":sha(EYE_CLOSEUP),
    "generated_textures":[{"path":str(IRIS_TEXTURE.relative_to(OUT)),"sha256":sha(IRIS_TEXTURE)}],
    "unreal_asset":f"/Game/ArtReview/Characters/{NAME}.{NAME}",
    "source_parts":len(source_parts),"source_triangles":source_tris,
    "bounds_m":bounds,"local_forward":"+X face-forward; +Z up",
    "world_origin_m":[0,0,0],"rigged":False,"external_images":[],
    "user_design_reference_sha256":"c9f7a4bbe6ba529b2bbdb629db3ba09858c11b563c334e31593876455a550801",
    "user_design_reference_embedded":False,
    "design_details":["grey tabby and white fur","blue eyes","red-and-black lamellar armor",
                      "red waist sash","sheathed katana","asymmetric yumi",
                      "open ebira with six red-fletched bamboo arrows"],
    "insignia_source":"../../UI/sora_logo_NOtext2.svg",
    "insignia_sha256":logo_record["source_sha256"],
    "sora_kamon_placements":["chest","waist","sode_-1","sode_1"],
    "license":"Original project-owned character geometry, shaders and review renders; exact user-supplied SORA insignia paths retain their user-provided provenance and are licensed only for this game. No purchased or external models/textures",
    "limitations":"Stylized concept/blockout, not the photoreal shipping character. Unrigged static mesh; the bow and quiver are static pose source, not functional carry/draw animation. Blender procedural shaders and fur geometry have not been evaluated in UE 5.8.2. No animation, cloth simulation, groom, UE import, or in-game performance claim.",
}
MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_HERO_SOURCE_CREATED",len(source_parts),source_tris,bounds)
