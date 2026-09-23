"""Author a measured white-oak bokuto form study, separate from the playable mesh.

Run with Blender 5.2.2 LTS from the repository root. The modern All Japan
Kendo Federation jodo dimensions are a proportion benchmark, not a claim that
every Edo-period bokuto had one fixed pattern. No gameplay mesh is replaced.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/DojoBokutoForm"
PBR = ROOT / "Content/SourceArt/Weapons/DojoBokkenPBR"
LEATHER = ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/Textures"
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "Nyaagyu_BokutoForm.blend"
FBX = OUT / "SM_Nyaagyu_BokutoForm.fbx"
PREVIEW = OUT / "Nyaagyu_BokutoForm_Blender.png"
DETAIL = OUT / "Nyaagyu_BokutoForm_Detail_Blender.png"
MANIFEST = OUT / "manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


texture_manifest = json.loads((PBR / "texture_manifest.json").read_text())
for entry in texture_manifest["maps"].values():
    path = PBR / entry["file"]
    assert sha(path) == entry["sha256"], path
leather_manifest = json.loads(
    (ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/manifest.json").read_text())
leather_files = {item["channel"]: item for item in leather_manifest["textures"]
                 if item["surface"] == "leather"}
assert set(leather_files) == {"Albedo", "NormalDX", "ARM"}
for entry in leather_files.values():
    assert sha(ROOT / "Content/SourceArt/Weapons/NyaagyuYumi" / entry["file"]) == entry["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
asset = bpy.data.collections.new("BokutoForm_Editable")
scene.collection.children.link(asset)


def img(path: Path, noncolor=False):
    image = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        image.colorspace_settings.name = "Non-Color"
    return image


def material(name, base, normal, orm, tint, rough_scale=1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0
    bsdf.inputs["Coat Weight"].default_value = .04
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    color = nodes.new("ShaderNodeTexImage")
    color.image = img(base)
    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    multiply.inputs[2].default_value = (*tint, 1)
    links.new(color.outputs["Color"], multiply.inputs[1])
    links.new(multiply.outputs["Color"], bsdf.inputs["Base Color"])
    packed = nodes.new("ShaderNodeTexImage")
    packed.image = img(orm, True)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(packed.outputs["Color"], split.inputs["Color"])
    scale = nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = rough_scale
    links.new(split.outputs["Green"], scale.inputs[0])
    links.new(scale.outputs[0], bsdf.inputs["Roughness"])
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img(normal, True)
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(tex.outputs["Color"], channels.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(channels.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    combine.mode = "RGB"
    links.new(channels.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(channels.outputs["Blue"], combine.inputs["Blue"])
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = .35
    links.new(combine.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    mat.diffuse_color = (*tint, 1)
    return mat


oak = material(
    "M_Bokuto_QuarterSawnWhiteOak",
    PBR / texture_manifest["maps"]["Albedo"]["file"],
    PBR / texture_manifest["maps"]["NormalDX"]["file"],
    PBR / texture_manifest["maps"]["ORM"]["file"],
    (.55, .48, .41),
)
oiled = material(
    "M_Bokuto_HandOiledOakGrip",
    PBR / texture_manifest["maps"]["Albedo"]["file"],
    PBR / texture_manifest["maps"]["NormalDX"]["file"],
    PBR / texture_manifest["maps"]["ORM"]["file"],
    (.42, .34, .27), .83,
)
leather = material(
    "M_Bokuto_DarkLeatherTsuba",
    ROOT / "Content/SourceArt/Weapons/NyaagyuYumi" / leather_files["Albedo"]["file"],
    ROOT / "Content/SourceArt/Weapons/NyaagyuYumi" / leather_files["NormalDX"]["file"],
    ROOT / "Content/SourceArt/Weapons/NyaagyuYumi" / leather_files["ARM"]["file"],
    (.27, .20, .15), 1.07,
)


def ring_mesh(name, section_count, section_fn, x0, x1, mat):
    verts, faces, uv_faces = [], [], []
    reverse_profile = name.startswith("Tachi_")
    for index in range(section_count):
        x = x0 + (x1 - x0) * index / (section_count - 1)
        profile = section_fn(x)
        for y, z in profile:
            verts.append((x, y, z))
    sides = len(section_fn(x0))
    for index in range(section_count - 1):
        for side in range(sides):
            n = (side + 1) % sides
            if reverse_profile:
                faces.append((index*sides+side,index*sides+n,
                              (index+1)*sides+n,(index+1)*sides+side))
                uv_faces.append(((side/sides,index/(section_count-1)),
                                 ((side+1)/sides,index/(section_count-1)),
                                 ((side+1)/sides,(index+1)/(section_count-1)),
                                 (side/sides,(index+1)/(section_count-1))))
            else:
                faces.append((index*sides+side, (index+1)*sides+side,
                              (index+1)*sides+n, index*sides+n))
                uv_faces.append(((side/sides, index/(section_count-1)),
                                 (side/sides, (index+1)/(section_count-1)),
                                 ((side+1)/sides, (index+1)/(section_count-1)),
                                 ((side+1)/sides, index/(section_count-1))))
    start_order = list(reversed(range(sides))) if reverse_profile else list(range(sides))
    end_order = list(range(sides)) if reverse_profile else list(reversed(range(sides)))
    faces.append(tuple(start_order))
    faces.append(tuple((section_count-1)*sides+side for side in end_order))
    uv_faces.extend((tuple((.5+.48*math.cos(math.tau*i/sides),
                            .5+.48*math.sin(math.tau*i/sides)) for i in start_order),
                     tuple((.5+.48*math.cos(math.tau*i/sides),
                            .5+.48*math.sin(math.tau*i/sides)) for i in end_order)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name="UV0")
    for poly, face_uv in zip(mesh.polygons, uv_faces):
        for loop, point in zip(poly.loop_indices, face_uv):
            uv.data[loop].uv = point
        poly.use_smooth = poly.index < len(faces) - 2
    if name.startswith("Tachi_"):
        # Hold carved shinogi/ha facets while keeping longitudinal surfaces
        # smoothly interpolated. A fully smooth cross section reads as a rod.
        for edge in mesh.edges:
            a, b = edge.vertices
            if abs(a-b) == sides and a%sides in {0, 2, 4, 5, 6, 7, 9, 11}:
                edge.use_edge_sharp = True
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    obj["authorship"] = "Original SORA Arena hand-profiled bokuto study"
    return obj


# Modern AJKF jodo benchmark: 101.5 cm overall, 24.2 cm handle, 1.5 cm sori.
# Its side-view deviation is a shallow arc from the straight base-to-tip chord.
def grip_profile(x):
    u = (x + .242) / .242
    taper = .92 + .08 * math.sin(math.pi * max(0, min(1, u)))
    cy = .0164 * taper
    cz = .0137 * taper
    return [(cy * math.sin(math.tau*i/16), cz * math.cos(math.tau*i/16))
            for i in range(16)]


def blade_profile(x):
    u = max(0., min(1., x/.773))
    sori = .015 * 4*u*(1-u)
    root = 1 - .35*u
    cap = 1.0 if x <= .760 else math.sqrt(max(.16, 1-((x-.760)/.013)**2))
    tip = cap
    width = root*tip
    thick = (1-.20*u)*tip
    # Mune, ridged ji and deliberately blunt ha have distinct facets. This
    # avoids the cylindrical baton silhouette without introducing a sharp edge.
    yz = [(-.0075,.0132),(-.0122,.0111),(-.0172,.0027),
          (-.0135,-.0059),(-.0052,-.0137),(-.0013,-.0154),
          (.0013,-.0154),(.0052,-.0137),(.0135,-.0059),
          (.0172,.0027),(.0122,.0111),(.0075,.0132)]
    hand = .00018*math.sin(31*x+.4) + .00009*math.sin(93*x+1.9)
    return [(y*width + (hand if y>0 else -hand), sori + z*thick)
            for y, z in yz]


grip = ring_mesh("Tsuka_HandPlanedOvalWhiteOak", 33, grip_profile,
                 -.242, 0, oiled)
blade = ring_mesh("Tachi_MuneShinogiBluntHaWhiteOak", 160,
                  blade_profile, 0, .773, oak)


def leather_tsuba():
    verts, faces = [], []
    for x in (-.0025, .0025):
        for radius in (.0165, .040):
            for i in range(40):
                a = math.tau*i/40
                # A slightly asymmetric hand-cut leather ellipse.
                r = radius*(1 + .018*math.sin(5*a+.3))
                verts.append((x, r*math.cos(a), r*.79*math.sin(a)))
    face_uvs = []
    for side in range(40):
        n = (side+1)%40
        faces.extend(((side,n,40+n,40+side),
                      (80+side,120+side,120+n,80+n),
                      (40+side,40+n,120+n,120+side),
                      (side,80+side,80+n,n)))
        # Annular front/back use planar YZ coordinates. Inner and outer walls
        # unwrap around their circumference with X as the second dimension.
        for kind in range(4):
            if kind < 2:
                face_uvs.append(None)
            else:
                u0, u1 = side/40, (side+1)/40
                face_uvs.append(((u0,0),(u1,0),(u1,1),(u0,1)) if kind==2
                                else ((u0,0),(u0,1),(u1,1),(u1,0)))
    mesh = bpy.data.meshes.new("LeatherTsuba")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(leather)
    uv = mesh.uv_layers.new(name="UV0")
    for poly, wall_uv in zip(mesh.polygons, face_uvs):
        for corner, loop in enumerate(poly.loop_indices):
            if wall_uv is None:
                p = verts[mesh.loops[loop].vertex_index]
                uv.data[loop].uv = (.5+p[1]*7, .5+p[2]*7)
            else:
                uv.data[loop].uv = wall_uv[corner]
    obj = bpy.data.objects.new("Tsuba_HandCutDarkLeather", mesh)
    asset.objects.link(obj)
    obj["authorship"] = "Original SORA Arena leather guard geometry"
    return obj


guard = leather_tsuba()


def retainer_profile(_x):
    return [(.0182*math.sin(math.tau*i/16),
             .0144*math.cos(math.tau*i/16)) for i in range(16)]


retainer = ring_mesh("Tsubadome_LeatherRetainingCollar", 4,
                     retainer_profile, -.009, -.0025, leather)
parts = (grip, blade, guard, retainer)
assert abs(min(v.co.x for o in parts for v in o.data.vertices)+.242) < 1e-6
assert abs(max(v.co.x for o in parts for v in o.data.vertices)-.773) < 1e-6

# Studio and cameras are review-only, never exported.
studio = bpy.data.collections.new("ReviewStudio_NotForFBX")
scene.collection.children.link(studio)
world = bpy.data.worlds.new("NeutralWorld")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.22,.23,.25,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .18


def area(name, pos, power, size):
    data = bpy.data.lights.new(name, "AREA")
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (Vector((.22,0,0))-obj.location).to_track_quat("-Z","Y").to_euler()
    data.energy = power
    data.shape = "DISK"
    data.size = size


area("LongSoftbox", (.33,-.52,.65), 24, 1.1)
area("RimSoftbox", (.15,.48,.42), 16, .85)
camera_data = bpy.data.cameras.new("ReviewCamera")
camera = bpy.data.objects.new("ReviewCamera", camera_data)
studio.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"


def render(path, position, target, ortho):
    camera.location = position
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.ortho_scale = ortho
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


render(PREVIEW, (.22,-1.33,.57), (.22,0,.005), 1.22)
render(DETAIL, (.44,-.47,.29), (.40,0,.005), .43)

bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = grip
bpy.ops.export_scene.fbx(
    filepath=str(FBX), use_selection=True, object_types={"MESH"},
    apply_unit_scale=True, global_scale=1, axis_forward="-Y", axis_up="Z",
    path_mode="STRIP", add_leaf_bones=False, bake_anim=False,
)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

MANIFEST.write_text(json.dumps({
    "schema_version": 1,
    "name": "SM_Nyaagyu_BokutoForm",
    "generator": "scripts/art/create_dojo_bokuto_form_study.py",
    "source_blend": BLEND.name,
    "blend_sha256": sha(BLEND),
    "fbx": FBX.name,
    "fbx_sha256": sha(FBX),
    "preview": PREVIEW.name,
    "preview_sha256": sha(PREVIEW),
    "detail_preview": DETAIL.name,
    "detail_preview_sha256": sha(DETAIL),
    "parts": len(parts),
    "triangles": sum(len(poly.vertices)-2 for part in parts for poly in part.data.polygons),
    "bounds_m": {"min_x": -.242, "max_x": .773},
    "dimensions_cm": {"total": 101.5, "grip": 24.2, "sori": 1.5},
    "materials": [o.data.materials[0].name for o in parts],
    "source_texture_manifest_sha256": sha(PBR / "texture_manifest.json"),
    "leather_source_manifest_sha256": sha(ROOT / "Content/SourceArt/Weapons/NyaagyuYumi/manifest.json"),
    "proportion_reference": "https://www.kendo.or.jp/wp/wp-content/uploads/2023/07/jodo-shiai_regulations.pdf",
    "scope": "Source-only modern jodo-proportioned bokuto study. No historic Edo attribution, Unreal import, combat geometry, collision, or animation change.",
}, ensure_ascii=False, indent=2) + "\n")
print("BOKUTO_FORM_STUDY_READY", sha(FBX))
