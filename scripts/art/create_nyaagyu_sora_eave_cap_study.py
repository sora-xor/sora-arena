"""Build an editable source-only modeled SORA-kamon ceramic eave-cap study.

Run build_nyaagyu_sora_eave_cap_maps.py first. The SVG-derived crest is real
raised clay geometry, not a texture/decal. This does not assert period accuracy
or Unreal runtime quality. Blender 5.2.2 LTS is the source authoring version.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuSoraEaveCapStudy"
SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SVG_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
assert hashlib.sha256(SVG.read_bytes()).hexdigest() == SVG_SHA256
texture_manifest = json.loads((OUT / "texture_manifest.json").read_text())
for record in texture_manifest["files"].values():
    path = OUT / record["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
asset = bpy.data.collections.new("SORA_EaveCap_Editable")
scene.collection.children.link(asset)
set_dressing = bpy.data.collections.new("ReviewOnly_Backdrop")
scene.collection.children.link(set_dressing)


def ceramic_material(name: str, polished: bool = False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    images = {}
    for channel, record in texture_manifest["files"].items():
        node = nodes.new("ShaderNodeTexImage")
        node.name = channel
        node.image = bpy.data.images.load(str(OUT / record["file"]), check_existing=True)
        node.image.colorspace_settings.name = "sRGB" if channel == "albedo" else "Non-Color"
        images[channel] = node
    if polished:
        tint = nodes.new("ShaderNodeMixRGB")
        tint.blend_type = "MULTIPLY"
        tint.inputs[0].default_value = 1
        tint.inputs[2].default_value = (1.12, 1.11, 1.09, 1)
        links.new(images["albedo"].outputs["Color"], tint.inputs[1])
        links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        links.new(images["albedo"].outputs["Color"], bsdf.inputs["Base Color"])
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(images["orm"].outputs["Color"], split.inputs["Color"])
    if polished:
        gloss = nodes.new("ShaderNodeMath")
        gloss.operation = "MULTIPLY"
        gloss.inputs[1].default_value = .81
        links.new(split.outputs["Green"], gloss.inputs[0])
        links.new(gloss.outputs[0], bsdf.inputs["Roughness"])
    else:
        links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = .38
    links.new(images["normal_gl"].outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0
    return mat


clay = ceramic_material("M_IbushiClay_AuthoredEstimate")
raised_clay = ceramic_material("M_IbushiClay_WornMoldedHighs", polished=True)
wood = bpy.data.materials.new("M_ReviewBackdrop_CharredCedar")
wood.use_nodes = True
wood.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.035, .024, .019, 1)
wood.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .82


def link_asset(obj, name, mat):
    obj.name = name
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    asset.objects.link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj["source_art_status"] = "editable; unapproved for Unreal runtime"
    return obj


def planar_uv(obj, shank=False):
    mesh = obj.data
    uv = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        p = obj.matrix_world @ mesh.vertices[loop.vertex_index].co
        if shank:
            u, v = .5 + p.x / .14, p.y / .24
        else:
            u, v = .5 + p.x / .14, .5 + (p.z - .055) / .14
        uv.data[loop.index].uv = (max(.01, min(.99, u)), max(.01, min(.99, v)))


# A 130 mm handmade cap with radial-profile raised lip, shallow score and a
# few tenths of a millimetre of kiln distortion. The front is -Y, back +Y.
radius_profile = [
    (.019, -.0225), (.040, -.0225), (.047, -.0221),
    (.051, -.0217), (.054, -.0223), (.0575, -.0251),
    (.061, -.0240), (.064, -.0190), (.065, -.0110),
    (.063, -.0045), (.058, .0020), (.044, .0050),
]
segments = 128
vertices = [(0, -.0225, .055)]
for ring, (r, y) in enumerate(radius_profile):
    for j in range(segments):
        a = 2 * math.pi * j / segments
        kiln = .00027 * math.sin(3*a + .8) + .00011 * math.sin(11*a + ring*.33)
        vertices.append(((r+kiln)*math.cos(a), y+.00014*math.sin(5*a+ring*.4),
                         .055+(r+kiln)*math.sin(a)))
back_center = len(vertices)
vertices.append((0, .0050, .055))
faces = [(0, 1+j, 1+(j+1)%segments) for j in range(segments)]
for ring in range(len(radius_profile)-1):
    start = 1 + ring*segments
    end = start + segments
    for j in range(segments):
        k = (j+1) % segments
        faces.append((start+j, end+j, end+k, start+k))
end = 1 + (len(radius_profile)-1)*segments
faces.extend((back_center, end+(j+1)%segments, end+j) for j in range(segments))
mesh = bpy.data.meshes.new("EaveCap_SculptedClay_Mesh")
mesh.from_pydata(vertices, [], faces)
mesh.update()
disc = bpy.data.objects.new("EaveCap_SculptedClay", mesh)
asset.objects.link(disc)
disc.data.materials.append(clay)
disc["construction"] = "solid radial profile with raised molded lip and kiln warp"
for poly in mesh.polygons:
    poly.use_smooth = True
planar_uv(disc)


# A solid vaulted cover-tile section runs upslope behind the badge. The front
# cap is mechanically integrated by overlap, not a floating medallion.
nx, ny = 32, 13
length = .224
tile_vertices = []
for skin in (0, 1):
    for iy in range(ny+1):
        v = iy/ny
        y = .002 + length*v
        for ix in range(nx+1):
            u = ix/nx
            s = u*2-1
            x = s*.049*(1-.025*v) + .00065*math.sin(4*math.pi*v+u*3)
            z = .039 + .044*(1-s*s) + .0035*v + .0018*(1-v)**2
            tile_vertices.append((x, y, z - skin*.010))
stride = (nx+1)*(ny+1)
tile_faces = []
for skin in (0, 1):
    for iy in range(ny):
        for ix in range(nx):
            a = skin*stride + iy*(nx+1)+ix
            quad = (a, a+1, a+nx+2, a+nx+1)
            tile_faces.append(quad if skin==0 else tuple(reversed(quad)))
for iy in range(ny):
    for ix in (0, nx):
        a = iy*(nx+1)+ix
        b = (iy+1)*(nx+1)+ix
        quad = (a,b,b+stride,a+stride)
        tile_faces.append(quad if ix==0 else tuple(reversed(quad)))
for ix in range(nx):
    for iy in (0, ny):
        a = iy*(nx+1)+ix
        quad = (a,a+1,a+1+stride,a+stride)
        tile_faces.append(tuple(reversed(quad)) if iy==0 else quad)
tile_mesh = bpy.data.meshes.new("VaultedCover_SolidClay_Mesh")
tile_mesh.from_pydata(tile_vertices, [], tile_faces)
tile_mesh.update()
shank = bpy.data.objects.new("VaultedCover_SolidClay", tile_mesh)
asset.objects.link(shank)
tile_mesh.materials.append(clay)
shank["construction"] = "solid vaulted cover section; approximately 10 mm clay wall"
for poly in tile_mesh.polygons:
    poly.use_smooth = True
planar_uv(shank, shank=True)


# Low, hand-rolled collar lines let the cap/socket transition read as formed
# ceramic instead of a floating disc. They are real beveled mesh geometry.
for collar_i, y in enumerate((.018, .034)):
    arc = []
    for ix in range(nx+1):
        s = 2*ix/nx-1
        x = s*.049*(1-.025*y/length)
        z = .040 + .044*(1-s*s) + .0035*y/length + .002
        arc.append(Vector((x,y,z)))
    tube_sides = 20
    bead = .0017 if collar_i == 0 else .0011
    collar_vertices = []
    for ix, center in enumerate(arc):
        tangent = (arc[min(ix+1,nx)] - arc[max(ix-1,0)]).normalized()
        transverse = tangent.cross(Vector((0,1,0))).normalized()
        for j in range(tube_sides):
            angle = 2*math.pi*j/tube_sides
            p = center + bead*(math.cos(angle)*Vector((0,1,0))
                                + math.sin(angle)*transverse)
            collar_vertices.append(tuple(p))
    front_center = len(collar_vertices)
    collar_vertices.append(tuple(arc[0]))
    rear_center = len(collar_vertices)
    collar_vertices.append(tuple(arc[-1]))
    collar_faces = []
    for ix in range(nx):
        for j in range(tube_sides):
            k = (j+1) % tube_sides
            a = ix*tube_sides+j
            b = (ix+1)*tube_sides+j
            collar_faces.append((a,ix*tube_sides+k,b+(k-j),b))
    for j in range(tube_sides):
        k = (j+1) % tube_sides
        collar_faces.append((front_center,k,j))
        collar_faces.append((rear_center,nx*tube_sides+j,nx*tube_sides+k))
    collar_mesh = bpy.data.meshes.new(f"MoldedCollar_{collar_i}_Mesh")
    collar_mesh.from_pydata(collar_vertices, [], collar_faces)
    collar_mesh.update()
    obj = bpy.data.objects.new(f"MoldedCollar_{collar_i}", collar_mesh)
    asset.objects.link(obj)
    obj.data.materials.append(raised_clay)
    obj["construction"] = "closed modeled shallow hand-rolled clay collar"
    planar_uv(obj, shank=True)


# Import the exact supplied vector paths. Their Bezier control points are
# retained in the .blend in a hidden reference collection; renderable copies
# become full 3D extruded and bevelled clay molds.
before = set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(SVG))
source_curves = sorted((obj for obj in set(bpy.data.objects)-before if obj.type=="CURVE"),
                       key=lambda obj: obj.name)
assert len(source_curves) == 2, len(source_curves)
world_corners = [obj.matrix_world @ Vector(corner)
                 for obj in source_curves for corner in obj.bound_box]
xmin, xmax = min(p.x for p in world_corners), max(p.x for p in world_corners)
ymin, ymax = min(p.y for p in world_corners), max(p.y for p in world_corners)
source_size = max(xmax-xmin, ymax-ymin)
scale = .093/source_size
center_x, center_y = (xmin+xmax)*.5, (ymin+ymax)*.5
mapper = Matrix(((scale, 0, 0, -scale*center_x),
                 (0, 0, -scale, -.0229),
                 (0, scale, 0, .055-scale*center_y),
                 (0, 0, 0, 1)))
crest_records = []
for path_index, obj in enumerate(source_curves):
    obj.name = f"SORA_ExactSVG_ClayRelief_Path_{path_index}"
    obj.data.dimensions = "2D"
    obj.data.fill_mode = "BOTH"
    obj.data.resolution_u = 24
    obj.matrix_world = mapper @ obj.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    relief = bpy.context.object
    solid = relief.modifiers.new("MoldedClay_3p6mm", "SOLIDIFY")
    solid.thickness = .0036/scale
    solid.offset = 0
    bpy.ops.object.modifier_apply(modifier=solid.name)
    bevel = relief.modifiers.new("MoldedClay_SoftArris", "BEVEL")
    bevel.width = .00045/scale
    bevel.segments = 3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    link_asset(relief, f"SORA_ExactSVG_ClayRelief_Path_{path_index}", raised_clay)
    relief["source_svg_sha256"] = SVG_SHA256
    relief["source_path_index"] = path_index
    relief["construction"] = "SVG Bezier path extruded 3.6 mm with 0.9 mm total edge bevel"
    planar_uv(relief)
    crest_records.append({"mesh": relief.name, "vertex_count": len(relief.data.vertices),
                          "triangle_count": sum(len(p.vertices)-2 for p in relief.data.polygons)})


# Review context only; never exported as part of the eave-cap asset.
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,.085,-.029))
backdrop = bpy.context.object
backdrop.name = "ReviewOnly_CharredCedarEave"
backdrop.dimensions = (.40,.31,.043)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
for col in tuple(backdrop.users_collection): col.objects.unlink(backdrop)
set_dressing.objects.link(backdrop)
backdrop.data.materials.append(wood)
bevel = backdrop.modifiers.new("SoftenedEaveEdge", "BEVEL")
bevel.width = .006
bevel.segments = 3

target = Vector((0,.055,.053))
camera_data = bpy.data.cameras.new("FixedReview_ThreeQuarter")
camera = bpy.data.objects.new("FixedReview_ThreeQuarter", camera_data)
scene.collection.objects.link(camera)
camera.location = (.126,-.296,.162)
camera.rotation_euler = (target-Vector(camera.location)).to_track_quat("-Z","Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = .32
scene.camera = camera
world = bpy.data.worlds.new("NeutralOvercast_Review")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.18,.22,.27,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .24
for name, location, energy, size, color in (
    ("LargeCoolSky", (.11,-.24,.31), 3.5, .32, (0.76,.86,1)),
    ("WarmLanternBounce", (-.16,-.10,.14), 1.2, .17, (1,.65,.35)),
    ("NarrowRakingEdge", (-.03,.03,.22), 1.4, .12, (1,.94,.84)),
):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    light.color = color
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target-Vector(location)).to_track_quat("-Z","Y").to_euler()

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "Nyaagyu_SORA_EaveCap_FixedReview.png")
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.3
scene.render.film_transparent = False
scene.render.image_settings.color_mode = "RGBA"

if os.environ.get("SORA_EAVE_GEOMETRY_ONLY") == "1":
    import bmesh
    for obj in asset.objects:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        print("GEOMETRY_ONLY", obj.name, len(obj.data.vertices),
              round(bm.calc_volume(signed=True), 10),
              sum(not edge.is_manifold for edge in bm.edges))
        bm.free()
    raise SystemExit(0)

for image in bpy.data.images:
    if image.source == "FILE" and image.filepath:
        image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Nyaagyu_SORA_EaveCap.blend"))
bpy.ops.object.select_all(action="DESELECT")
for obj in asset.objects:
    assert obj.type == "MESH", (obj.name,obj.type)
    obj.select_set(True)
bpy.context.view_layer.objects.active = disc
bpy.ops.export_scene.fbx(filepath=str(OUT / "SM_Nyaagyu_SORA_EaveCap.fbx"),
                         use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, axis_forward="-Z", axis_up="Y",
                         add_leaf_bones=False, path_mode="STRIP")
bpy.ops.render.render(write_still=True)

outputs = ("Nyaagyu_SORA_EaveCap.blend", "SM_Nyaagyu_SORA_EaveCap.fbx",
           "Nyaagyu_SORA_EaveCap_FixedReview.png")
manifest = {
    "status": "source-only ceramic detail, not approved for runtime",
    "generator": "scripts/art/create_nyaagyu_sora_eave_cap_study.py",
    "blender_version": bpy.app.version_string,
    "source_svg": "Content/SourceArt/UI/sora_logo_NOtext2.svg",
    "source_svg_sha256": SVG_SHA256,
    "crest_path_meshes": crest_records,
    "nominal_dimensions_m": {"cap_diameter": .130, "crest_diameter": .093,
                             "cover_section_length": length},
    "review": {"camera_location_m": list(camera.location),
               "camera_target_m": list(target), "camera_ortho_scale_m": camera_data.ortho_scale,
               "engine": scene.render.engine, "resolution": [900,900]},
    "material_note": "Authored clay estimates; not measured or historically authenticated.",
    "outputs": {name: hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in outputs},
}
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(json.dumps(manifest, indent=2))
