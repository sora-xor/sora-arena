"""Build an editable, source-only Nyaagyu su-yari form/material study.

The one dimensional anchor is British Museum OA+.7199.  Shaft fittings,
cross-section, finish and wrapping are an original game-art interpretation.
Run build_textures.py first, then Blender in background with this script.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
TEX = OUT / "Textures"
assert len(list(TEX.glob("T_Yari_*.png"))) == 15, "Run build_textures.py first"
for path in TEX.glob("T_Yari_*.png"):
    assert path.stat().st_size > 1000, path

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (.09, .09, .09)

asset = bpy.data.collections.new("NyaagyuSuyari_EditableWeapon")
scene.collection.children.link(asset)
presentation = bpy.data.collections.new("SourceReview_LightRig_ExcludedFromFBX")
scene.collection.children.link(presentation)


def pbr(name: str, tex_name: str, *, metal: bool = False,
        tint: tuple[float, float, float] | None = None,
        roughness_override: float | None = None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    maps = {}
    for map_name in ("Albedo", "ORM", "NormalDX"):
        node = nodes.new("ShaderNodeTexImage")
        node.name = map_name
        node.image = bpy.data.images.load(
            str(TEX / f"T_Yari_{tex_name}_{map_name}.png"), check_existing=True)
        node.image.colorspace_settings.name = (
            "sRGB" if map_name == "Albedo" else "Non-Color")
        links.new(coords.outputs["UV"], node.inputs["Vector"])
        maps[map_name] = node
    if tint is None:
        links.new(maps["Albedo"].outputs["Color"], bsdf.inputs["Base Color"])
    else:
        colored = nodes.new("ShaderNodeMixRGB")
        colored.blend_type = "MULTIPLY"
        colored.inputs[0].default_value = 1
        colored.inputs[2].default_value = (*tint, 1)
        links.new(maps["Albedo"].outputs["Color"], colored.inputs[1])
        links.new(colored.outputs["Color"], bsdf.inputs["Base Color"])
    split_orm = nodes.new("ShaderNodeSeparateColor")
    links.new(maps["ORM"].outputs["Color"], split_orm.inputs["Color"])
    if roughness_override is None:
        links.new(split_orm.outputs["Green"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = roughness_override
    if metal:
        links.new(split_orm.outputs["Blue"], bsdf.inputs["Metallic"])
    # Generated files are DirectX; Blender's normal-map node expects OpenGL.
    split_n = nodes.new("ShaderNodeSeparateColor")
    links.new(maps["NormalDX"].outputs["Color"], split_n.inputs["Color"])
    flip_green = nodes.new("ShaderNodeMath")
    flip_green.operation = "SUBTRACT"
    flip_green.inputs[0].default_value = 1
    links.new(split_n.outputs["Green"], flip_green.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(split_n.outputs["Red"], rgb.inputs["Red"])
    links.new(flip_green.outputs[0], rgb.inputs["Green"])
    links.new(split_n.outputs["Blue"], rgb.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .42 if metal else .32
    links.new(rgb.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


steel = pbr("M_Yari_ForgedSteel", "ForgedSteel", metal=True)
dark_steel = pbr("M_Yari_PatinatedFerrule", "PatinatedIron", metal=True)
wood = pbr("M_Yari_ExposedAsh", "AshWood")
lacquer = pbr("M_Yari_BlackUrushiConcept", "BlackUrushi")
cord = pbr("M_Yari_RussetBinding", "RussetCord",
           tint=(.55,.48,.42), roughness_override=.84)


def mesh_object(name, verts, faces, face_uvs, material, *, smooth=True):
    assert len(faces) == len(face_uvs)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="UVMap")
    for poly, corners in zip(mesh.polygons, face_uvs):
        assert len(poly.loop_indices) == len(corners)
        for loop, xy in zip(poly.loop_indices, corners):
            uv.data[loop].uv = xy
        poly.use_smooth = smooth
    obj["source_only"] = True
    obj["accession_anchor"] = "British Museum OA+.7199"
    return obj


def ring_solid(name, rings, material, *, sides=48, faceted=False):
    """Sweep a watertight, UV-mapped polygonal profile along global Z."""
    verts, faces, uv_faces = [], [], []
    z0, z1 = rings[0][0], rings[-1][0]
    for z, radius in rings:
        sway = .00045 * math.sin(z * 4.2) if name == "UrushiCoatedHaft" else 0
        for side in range(sides):
            angle = side * 2 * math.pi / sides
            if name.startswith("Ferrule_"):
                # Under half a millimetre of hammered asymmetry at the join.
                radius_here = radius + .00018*math.sin(7*angle+z*19)
            else:
                radius_here = radius
            verts.append((radius_here * math.cos(angle) + sway,
                          radius_here * math.sin(angle), z))
    for row in range(len(rings) - 1):
        for side in range(sides):
            a = row * sides + side
            b = row * sides + (side + 1) % sides
            faces.append((a, b, b + sides, a + sides))
            uv_faces.append(((side/sides, (rings[row][0]-z0)/(z1-z0)),
                             ((side+1)/sides, (rings[row][0]-z0)/(z1-z0)),
                             ((side+1)/sides, (rings[row+1][0]-z0)/(z1-z0)),
                             (side/sides, (rings[row+1][0]-z0)/(z1-z0))))
    # End faces are inward or outward as appropriate; UVs remain editable.
    faces.append(tuple(reversed(range(sides))))
    uv_faces.append(tuple((.5 + .48*math.cos(i*2*math.pi/sides),
                           .5 + .48*math.sin(i*2*math.pi/sides))
                          for i in reversed(range(sides))))
    faces.append(tuple((len(rings)-1)*sides+i for i in range(sides)))
    uv_faces.append(tuple((.5 + .48*math.cos(i*2*math.pi/sides),
                           .5 + .48*math.sin(i*2*math.pi/sides))
                          for i in range(sides)))
    return mesh_object(name, verts, faces, uv_faces, material,
                       smooth=not faceted)


# OA+.7199 gives 1.93 m overall and an 18 cm blade. The visible assembly is
# modeled to that envelope; its shaft material and fittings are interpretation.
shaft_rings = []
for i in range(31):
    z = .010 + i * 1.738 / 30
    t = z / 1.748
    # Hand-lathed appearance without a machine-perfect cylindrical silhouette.
    radius = .0180 - .0030*t + .00016*math.sin(t*8.7)
    shaft_rings.append((z, radius))
shaft = ring_solid("UrushiCoatedHaft", shaft_rings, lacquer)
shaft["interpreted_material"] = "project-authored ash-colored wood beneath black urushi"
shaft["overall_envelope_m"] = 1.93

# Lower exposed wood end and understated protective iron shoe.
ring_solid("ButtEnd_ExposedWood", [(0, .0159), (.013, .0159)], wood)
ring_solid("IronButtShoe", [(.003, .0185), (.006, .0194),
                              (.033, .0192), (.038, .0180)], dark_steel)

# A dark forged ferrule leaves the base of the steel shank readable. These
# profiles are art estimates and have no claimed identity with OA+.7199.
ring_solid("Ferrule_Main", [(1.718, .0163), (1.721, .0168),
                             (1.742, .0161), (1.750, .0146)], dark_steel)
ring_solid("Ferrule_LowerLip", [(1.715, .0167), (1.717, .0177),
                                 (1.720, .0177), (1.722, .0167)], dark_steel)
ring_solid("Ferrule_UpperLip", [(1.742, .0162), (1.745, .0177),
                                 (1.748, .0177), (1.751, .0150)], dark_steel)

# Museum tang length 0.48 m: z 1.27..1.75. It is an inspectable mesh inside
# the haft and a visible 8 mm shank immediately above the ferrule.
ring_solid("SteelTang_480mm_InsideHaft", [(1.270, .0055),
                                          (1.710, .0069),
                                          (1.750, .0070)], steel, sides=12,
           faceted=True)
ring_solid("VisibleBladeNeck", [(1.746, .0072), (1.760, .0070)],
           steel, sides=12, faceted=True)

# Blade rings form a solid eight-facet diamond section. Its central arris is
# modeled, not painted into a flat billboard; thin edge and tip are geometry.
blade_sections = [
    (1.750, .0062, .0032),
    (1.762, .0060, .0031),
    (1.772, .0094, .0033),
    (1.792, .0128, .0038),
    (1.820, .0121, .0037),
    (1.850, .0103, .0033),
    (1.880, .0078, .0027),
    (1.910, .0040, .0017),
    (1.927, .0008, .00045),
    (1.930, .00008, .00006),
]
verts, faces, uvs = [], [], []
for z, half_width, thickness in blade_sections:
    section = ((half_width, 0),
               (half_width*.55, thickness*.76),
               (0, thickness),
               (-half_width*.55, thickness*.76),
               (-half_width, 0),
               (-half_width*.55, -thickness*.76),
               (0, -thickness),
               (half_width*.55, -thickness*.76))
    verts += [(x, y, z) for x, y in section]
for row in range(len(blade_sections)-1):
    for side in range(8):
        a = row*8+side
        b = row*8+(side+1)%8
        faces.append((a,b,b+8,a+8))
        uvs.append(((side/8,row/(len(blade_sections)-1)),
                    ((side+1)/8,row/(len(blade_sections)-1)),
                    ((side+1)/8,(row+1)/(len(blade_sections)-1)),
                    (side/8,(row+1)/(len(blade_sections)-1))))
faces.append(tuple(reversed(range(8))))
uvs.append(tuple((.5+.45*math.cos(i*2*math.pi/8),
                  .5+.45*math.sin(i*2*math.pi/8)) for i in reversed(range(8))))
faces.append(tuple((len(blade_sections)-1)*8+i for i in range(8)))
uvs.append(tuple((.5+.45*math.cos(i*2*math.pi/8),
                  .5+.45*math.sin(i*2*math.pi/8)) for i in range(8)))
blade = mesh_object("SuyariBlade_EightFacetDiamond", verts, faces, uvs,
                    steel, smooth=False)
blade["blade_length_m"] = .18
blade["blade_section"] = "original eight-facet diamond design; expert review required"


def helix_binding(name: str, z0: float, z1: float, turns: int, base_radius: float,
                  tube_radius: float):
    """Modeled diagonal cord, not a flat material stripe."""
    path_steps = turns*16
    radial_sides = 8
    points = []
    for i in range(path_steps+1):
        t = i/path_steps
        angle = 2*math.pi*turns*t
        points.append(Vector((base_radius*math.cos(angle),
                              base_radius*math.sin(angle),
                              z0+t*(z1-z0))))
    verts, faces, uvs = [], [], []
    for i, p in enumerate(points):
        tangent = (points[min(i+1,path_steps)] - points[max(i-1,0)]).normalized()
        side = Vector((-p.y, p.x, 0)).normalized()
        normal = tangent.cross(side).normalized()
        for j in range(radial_sides):
            angle = j*2*math.pi/radial_sides
            v = p + tube_radius*(side*math.cos(angle)+normal*math.sin(angle))
            verts.append(tuple(v))
    for i in range(path_steps):
        for j in range(radial_sides):
            a=i*radial_sides+j
            b=i*radial_sides+(j+1)%radial_sides
            faces.append((a,b,b+radial_sides,a+radial_sides))
            uvs.append(((j/radial_sides,i/path_steps),
                        ((j+1)/radial_sides,i/path_steps),
                        ((j+1)/radial_sides,(i+1)/path_steps),
                        (j/radial_sides,(i+1)/path_steps)))
    faces.append(tuple(reversed(range(radial_sides))))
    uvs.append(tuple((.5+.45*math.cos(j*2*math.pi/radial_sides),
                      .5+.45*math.sin(j*2*math.pi/radial_sides))
                     for j in reversed(range(radial_sides))))
    faces.append(tuple(path_steps*radial_sides+j for j in range(radial_sides)))
    uvs.append(tuple((.5+.45*math.cos(j*2*math.pi/radial_sides),
                      .5+.45*math.sin(j*2*math.pi/radial_sides))
                     for j in range(radial_sides)))
    return mesh_object(name, verts, faces, uvs, cord)


helix_binding("FerruleBinding_Cord", 1.680, 1.711, 14, .0154, .00104)

# Save the reusable mesh and a source interchange export. No lights or camera
# are included in the FBX; the Blender file retains them for exact review.
bpy.ops.object.select_all(action="DESELECT")
for obj in asset.objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = shaft
fbx_path = OUT / "SM_Nyaagyu_Suyari_SourceStudy.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         axis_forward="-Y", axis_up="Z", path_mode="RELATIVE",
                         add_leaf_bones=False)
bpy.ops.object.select_all(action="DESELECT")


def area(name, location, target, power, color, shape="RECTANGLE", sx=1, sy=2):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = shape
    data.size = sx
    if shape == "RECTANGLE":
        data.size_y = sy
    obj = bpy.data.objects.new(name, data)
    presentation.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


area("LongSoftbox_Key", (-.64,-.82,1.04), (0,0,1), 160,
     (1.0,.86,.72), sx=.38, sy=1.65)
area("CoolRim", (.55,.33,1.18), (0,0,1), 120,
     (.60,.77,1.0), sx=.20, sy=1.50)
area("BladeWhiteCard", (.18,-.25,1.85), (0,0,1.85), 12,
     (1,1,1), sx=.15, sy=.25)
area("LowShaftFill", (.10,-.38,.48), (0,0,.7), 18,
     (1.0,.77,.58), sx=.26, sy=.70)
world = bpy.data.worlds.new("Neutral_Charcoal_Studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.12,.125,.14,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .35
scene.world = world

cam_data = bpy.data.cameras.new("SourceReview_Camera")
camera = bpy.data.objects.new("SourceReview_Camera", cam_data)
presentation.objects.link(camera)
scene.camera = camera
cam_data.type = "ORTHO"
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.color_mode = "RGBA"


def render(name, location, target, ortho, x, y, roll=0):
    camera.location = location
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    if roll:
        camera.rotation_euler.rotate_axis("Z", math.radians(roll))
    cam_data.ortho_scale = ortho
    scene.render.resolution_x = x
    scene.render.resolution_y = y
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)


render("Nyaagyu_Suyari_Full.png", (.44,-1.4,1.0), (0,0,.97),
       2.16, 1000, 1750, roll=-7)
render("Nyaagyu_Suyari_BladeJoin.png", (.24,-.44,1.79), (0,0,1.79),
       .375, 1400, 1300, roll=-12)

scene.render.filepath = ""
bpy.ops.file.pack_all()
blend_path = OUT / "Nyaagyu_Suyari_SourceStudy.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

texture_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(TEX.glob("T_Yari_*.png"))}
manifest = {
    "asset_status": "source-only, not imported into Unreal gameplay",
    "museum_anchor": {
        "institution": "The British Museum",
        "accession": "OA+.7199",
        "url": "https://www.britishmuseum.org/collection/object/A_OA-7199",
        "catalog_period": "Edo Period (middle), 18th-19th century",
        "catalog_measurements_m": {"overall": 1.93, "blade": .18, "tang": .48},
        "catalog_material_record": "steel",
    },
    "authored_interpretation": [
        "eight-facet diamond blade section and 25.6 mm maximum blade width",
        "ash-colored wood shaft, black urushi finish, steel ferrule/shoe, russet cord",
        "haft diameter and mounting details are art estimates",
    ],
    "geometry_m": {"overall_envelope": 1.93, "blade": .18,
                    "modeled_internal_tang": .48},
    "texture_source": "original project-authored procedural maps; no external bitmap copied",
    "textures_sha256": texture_hashes,
    "fbx_sha256": hashlib.sha256(fbx_path.read_bytes()).hexdigest(),
    "renders": ["Nyaagyu_Suyari_Full.png", "Nyaagyu_Suyari_BladeJoin.png"],
    "limitations": "not historical reconstruction, Japanese-arms-reviewed, AAA-approved, or runtime-tested",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("YARI_BUILT", len(asset.objects), len(list(TEX.glob("T_Yari_*.png"))),
      fbx_path.stat().st_size, blend_path.stat().st_size)
