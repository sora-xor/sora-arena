"""Build an original, editable oak bokken for chapter-one nonlethal sparring.

Run: blender -b --factory-startup --python scripts/art/create_dojo_bokken.py
The preview is a Blender source-art render, not an Unreal screenshot. Geometry
uses meters and follows the hero katana's local X axis/grip origin.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Weapons/Original"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_DojoBokken"
FBX = OUT / f"{NAME}.fbx"
BLEND = OUT / "Nyaagyu_DojoBokken.blend"
PREVIEW = OUT / "Nyaagyu_DojoBokken_Blender.png"

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
collection = bpy.data.collections.new("DojoBokken_Editable")
bpy.context.scene.collection.children.link(collection)


def material(name, color, roughness, grain_scale):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = .10
    bsdf.inputs["Coat Roughness"].default_value = .44
    if "EndGrain" not in name and "QuietWoodGrain" not in name:
        coordinates = nodes.new("ShaderNodeTexCoord")
        waves = nodes.new("ShaderNodeTexWave")
        waves.wave_type = "BANDS"
        waves.bands_direction = "Y"
        waves.inputs["Scale"].default_value = 15
        waves.inputs["Distortion"].default_value = 2.8
        waves.inputs["Detail"].default_value = 3
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = .18
        ramp.color_ramp.elements[0].color = (*[c*.69 for c in color], 1)
        ramp.color_ramp.elements[1].position = .82
        ramp.color_ramp.elements[1].color = (*[min(1,c*1.11) for c in color], 1)
        links.new(coordinates.outputs["Generated"], waves.inputs["Vector"])
        links.new(waves.outputs["Color"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = grain_scale
    tex.inputs["Detail"].default_value = 3
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .12
    bump.inputs["Distance"].default_value = .00015
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


OAK = material("M_Bokken_SeasonedWhiteOak", (.39, .27, .135), .52, 165)
GRIP = material("M_Bokken_HandOiledGrip", (.27, .17, .075), .58, 185)
ENDGRAIN = material("M_Bokken_EndGrain", (.23, .13, .050), .71, 210)
GRAIN = material("M_Bokken_QuietWoodGrain", (.16, .095, .033), .69, 195)


def make_mesh(name, vertices, faces, mats, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    for mat in mats:
        data.materials.append(mat)
    for index, polygon in enumerate(data.polygons):
        polygon.material_index = indices[index] if indices is not None else 0
        polygon.use_smooth = True
    obj["authorship"] = "Original SORA Arena procedural geometry"
    return obj


def blade_section(x):
    """Elliptical wood section with a broad, deliberately blunt cutting edge."""
    if x < -.015:
        u = (x + .310) / .295
        ry = .0175 + .0035 * math.sin(math.pi * max(0, u))
        rz = .0210 + .0015 * math.sin(math.pi * max(0, u))
        z = .0015
    else:
        u = min(1.0, (x + .015) / .772)
        taper = 1 - .45 * u
        # A training bokken ends in a rounded, visibly blunt oval rather than
        # the needle-like kissaki of a sharpened blade.
        tip = min(1.0, max(.62, (.757 - x) / .079))
        ry = .0162 * taper * tip
        rz = .0225 * taper * tip
        z = .002 + .020 * u * u
    return z, ry, rz


# Distinct, hand-shaped grip and a smoothly tapered blade remain separate
# editable meshes. Both have real end caps and rounded, non-metal edges.
for name, start, end, count, mat in [
    ("Grip_OnePieceOak", -.310, -.015, 31, GRIP),
    ("Blade_BluntOvoidOak", -.015, .757, 79, OAK),
]:
    vertices, faces, indices = [], [], []
    sides = 16
    for section in range(count):
        x = start + (end-start)*section/(count-1)
        z, ry, rz = blade_section(x)
        for side in range(sides):
            a = 2 * math.pi * side/sides
            # The lightly faceted ridge is an original hand-planed surface.
            contour = 1 + .018 * math.cos(4*a)
            vertices.append((x, ry * math.sin(a)*contour,
                             z + rz * math.cos(a)*contour))
    for section in range(count-1):
        for side in range(sides):
            nxt = (side+1) % sides
            faces.append((section*sides+side, section*sides+nxt,
                          (section+1)*sides+nxt, (section+1)*sides+side))
            indices.append(0)
    faces += [tuple(reversed(range(sides))),
              tuple((count-1)*sides+side for side in range(sides))]
    indices += [1, 1]
    make_mesh(name, vertices, faces, [mat, ENDGRAIN], indices)


# A narrow, integral shoulder and pommel detail are stained wood. No steel,
# metal guard, or sharp point appears on this nonlethal training prop.
def ring(name, x0, x1, radius_y, radius_z, mat):
    verts, faces = [], []
    sides = 20
    for x, scale in ((x0, .96), ((x0+x1)/2, 1), (x1, .96)):
        z, _, _ = blade_section(x)
        for side in range(sides):
            a = math.tau*side/sides
            verts.append((x, radius_y*scale*math.sin(a),
                          z+radius_z*scale*math.cos(a)))
    for section in range(2):
        for side in range(sides):
            nxt = (side+1)%sides
            faces.append((section*sides+side, section*sides+nxt,
                          (section+1)*sides+nxt, (section+1)*sides+side))
    faces.extend((tuple(reversed(range(sides))),
                  tuple(2*sides+side for side in range(sides))))
    make_mesh(name, verts, faces, [mat])


ring("GripEnd_HandCarvedCollar", -.310, -.301, .019, .023, GRIP)
ring("BladeRoot_HandCarvedShoulder", -.028, -.016, .021, .024, GRIP)


def grain_curve(name, points, width):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = width
    curve.bevel_resolution = 1
    spline = curve.splines.new("POLY")
    spline.points.add(len(points)-1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(GRAIN)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj["authorship"] = "Original shallow relief wood grain"
    return obj


# Sparse physical incisions survive FBX export. The subtler shader-only grain
# remains in the editable Blender source; UE material translation needs review.
for side in (-1, 1):
    for strand in range(6):
        points = []
        lo = .028 + .012 * (strand % 3)
        hi = .62 + .013 * strand
        for index in range(32):
            t = index / 31
            x = lo + (hi-lo)*t
            z, ry, rz = blade_section(x)
            a = -.82 + strand*.205 + .04*math.sin(2*math.pi*t+strand*.9)
            # Grain is placed on the left/right side of the oval, just proud
            # of the surface so the FBX has visible, gentle shallow lines.
            points.append((x, side*(ry*math.cos(a)+.00012),
                           z + rz*math.sin(a)))
        grain_curve(f"WoodGrain_{'L' if side<0 else 'R'}_{strand:02d}",
                    points, .00015)


parts = [obj for obj in collection.objects if obj.type == "MESH"]
triangles = sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons)
assert len(parts) == 16 and 3500 < triangles < 10000, (len(parts), triangles)

# Export a joined duplicate while retaining every authored component editable.
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
duplicates = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
export_obj = bpy.context.object
export_obj.name = NAME
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         global_scale=1.0, axis_forward="-Y", axis_up="Z",
                         add_leaf_bones=False, bake_anim=False,
                         path_mode="AUTO")
bpy.data.objects.remove(export_obj, do_unlink=True)

# Studio lighting is preview-only and excluded from the static mesh export.
studio = bpy.data.collections.new("Preview_Studio_NotForFBX")
bpy.context.scene.collection.children.link(studio)
floor_mat = material("M_Preview_Stone", (.023, .025, .026), .80, 25)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.045))
floor = bpy.context.object
floor.name = "Preview_Floor"
floor.data.materials.append(floor_mat)
for old in tuple(floor.users_collection):
    old.objects.unlink(floor)
studio.objects.link(floor)


def light(name, position, color, energy, size):
    bpy.ops.object.light_add(type="AREA", location=position)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = energy
    obj.data.color = color
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.rotation_euler = (Vector((.25, 0, 0))-obj.location).to_track_quat("-Z", "Y").to_euler()
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    studio.objects.link(obj)


light("Lantern_WarmKey", (.0, -.7, 1.2), (1, .76, .49), 140, 1.2)
light("Courtyard_CoolRim", (.65, .7, .9), (.65, .75, 1), 115, .9)
bpy.ops.object.camera_add(location=(.22, -.84, .98))
camera = bpy.context.object
camera.name = "Bokken_Preview_Camera"
camera.rotation_euler = (Vector((.23, 0, 0))-camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 1.32
for old in tuple(camera.users_collection):
    old.objects.unlink(camera)
studio.objects.link(camera)
scene = bpy.context.scene
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PREVIEW)
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.75
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_dojo_bokken.py",
    "authorship": "Original project-owned geometry, source materials and lighting; no third-party mesh or texture",
    "license": "Original project-owned artwork; no purchased assets",
    "source_blend": BLEND.name,
    "fbx": FBX.name,
    "preview": PREVIEW.name,
    "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "blend_sha256": hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
    "source_triangles": triangles,
    "units": "Blender meters; FBX unit metadata converts to Unreal centimeters",
    "length_m": 1.067,
    "unreal_asset": f"/Game/Generated/Meshes/{NAME}.{NAME}",
    "scope": "Visual nonlethal dojo sparring prop. Damage rules are independent. UE 5.8.2 material appearance and scale remain unverified.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
print("DOJO_BOKKEN_READY", len(parts), triangles, FBX, PREVIEW)
