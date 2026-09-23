"""Create an original alien debt-levy terminal for Lantern Ward.

Run: blender -b --factory-startup --python scripts/art/create_street_debt_terminal.py
This exports a visual mesh with one UCX box. The source blend and render are
art review material, not evidence of UE 5.8.2 import or in-game quality.
"""

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/StreetDebtTerminal"
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
NAME = "SM_Alien_StreetDebtTerminal"
FBX = OUT / (NAME + ".fbx")
BLEND = OUT / "Alien_StreetDebtTerminal.blend"
PREVIEW = OUT / "Alien_StreetDebtTerminal_Blender.png"

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
asset = bpy.data.collections.new("StreetDebtTerminal_Editable")
scene.collection.children.link(asset)


def material(name, color, metallic=0, roughness=.5, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


# Timber, metal, and stone slot names bind to the separately licensed CC0
# Poly Haven material instances already used by the world builder at runtime.
TIMBER = material("M_Env_Timber", (.21, .13, .055), 0, .78)
METAL = material("M_Env_Metal", (.095, .12, .14), .88, .42)
STONE = material("M_Env_Stone", (.23, .23, .20), 0, .83)
BRASS = material("M_StreetTerminal_AgedBronze", (.38, .28, .13), .78, .34)
ENAMEL = material("M_StreetTerminal_IndigoEnamel", (.015, .042, .066), .31, .27)
DISPLAY = material("M_StreetTerminal_ObsidianScreen", (.016, .027, .035), .26, .19)
CYAN = material("M_StreetTerminal_ColdLienSeal", (.012, .28, .36), .18, .26, 2.1)
RED = material("M_StreetTerminal_DebtTally", (.56, .035, .029), .13, .28, 2.5)
WASHI = material("M_StreetTerminal_PaperNotice", (.61, .48, .30), 0, .73)


def keep(obj, name, mat):
    obj.name = name
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena source geometry"
    return obj


def box(name, location, dimensions, mat, bevel=.005, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = keep(bpy.context.object, name, mat)
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation is not None:
        obj.rotation_euler = rotation
    if bevel:
        mod = obj.modifiers.new("Worn_Edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def cylinder(name, location, radius, depth, mat, vertices=24, rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=location)
    return keep(bpy.context.object, name, mat) if rotation is None else rotated(name, mat, rotation)


def rotated(name, mat, rotation):
    obj = keep(bpy.context.object, name, mat)
    obj.rotation_euler = rotation
    return obj


def torus(name, center, major, minor, mat, major_segments=40, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_segments=major_segments,
                                     minor_segments=minor_segments,
                                     location=center, rotation=(math.pi/2, 0, 0),
                                     major_radius=major, minor_radius=minor)
    return keep(bpy.context.object, name, mat)


def wedge(name, side, mat):
    # The twin offset claws give a slender street silhouette unlike the
    # existing citadel kiosk's broad rectangular cabinet and vault wheel.
    x0 = side*.36
    profile = [(-.12, .75), (.13, .78), (.34, 2.28), (.13, 2.14)]
    vertices = []
    for y in (-.15, .15):
        for dx, z in profile:
            vertices.append((x0+side*dx, y+.11, z))
    faces = [(0, 1, 2, 3), (4, 7, 6, 5)]
    for i in range(4):
        j = (i+1)%4
        faces.append((i, j, j+4, i+4))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    asset.objects.link(obj)
    mesh.materials.append(mat)
    obj["author"] = "Original SORA Arena source geometry"
    return obj


def label(name, text, center, size, mat):
    bpy.ops.object.text_add(location=center, rotation=(math.pi/2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = text
    obj.data.font = bpy.data.fonts.load(str(FONT), check_existing=True)
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    # At street-view size the mark is read as a flat inset. Extrusion would
    # spend more than 10k triangles on two small glyphs alone.
    obj.data.extrude = 0
    obj.data.bevel_depth = 0
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    asset.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    result = bpy.context.object
    result["author"] = "Original SORA Arena label geometry using bundled OFL Japanese font"
    return result


# Edo foundation is visibly appropriated by cold occupation machinery.
box("Roadside_StoneFoot", (0, .04, .09), (1.18, .74, .18), STONE, .023)
box("Weathered_Timber_LowerCase", (0, .03, .43), (.86, .52, .58), TIMBER, .026)
box("Black_Iron_UpperSpine", (0, .11, 1.32), (.37, .27, 1.44), METAL, .027)
for side in (-1, 1):
    wedge(f"Occupation_Claw_{side}", side, METAL)
    box(f"Bronze_LowerStrut_{side}", (side*.32, -.20, .78), (.10, .055, .48), BRASS, .005)
    box(f"BladeFin_Glow_{side}", (side*.63, -.105, 1.63), (.012, .020, .70), CYAN, .002,
        (0, side*.16, 0))
    for z in (.33, .55):
        cylinder(f"Rivet_{side}_{z}", (side*.35, -.244, z), .014, .012,
                 BRASS, 12, (math.pi/2, 0, 0))

# Circular lien scanner above a small transaction face. The red declining
# tally and receipt clamp tell the occupation/debt story without lore text.
torus("Bronze_OuterLienRing", (0, -.239, 1.58), .373, .035, BRASS)
torus("Cyan_InnerLienRing", (0, -.278, 1.58), .311, .009, CYAN)
box("Hanging_Obsidian_Display", (0, -.251, 1.56), (.62, .055, .59), DISPLAY, .021)
box("Washi_SeizureNotice", (0, -.287, 1.59), (.44, .007, .20), WASHI, .003)
label("Japanese_Levy_Mark", "徴収", (0, -.295, 1.59), .13, RED)
for i in range(7):
    x = -.21+i*.07
    height = .19-.018*i
    box(f"Descending_DebtTally_{i}", (x, -.287, 1.28+height*.5),
        (.032, .009, height), RED, .002)
box("DeedClamp_BronzeRim", (0, -.266, .88), (.68, .07, .23), BRASS, .014)
box("DeedClamp_PaperSlot", (0, -.304, .91), (.48, .012, .028), RED, .002)
box("Iron_ServiceHatch", (0, -.248, .53), (.50, .045, .32), ENAMEL, .017)
for side in (-1, 1):
    box(f"MaintenanceLatch_{side}", (side*.18, -.278, .52),
        (.06, .023, .10), BRASS, .006)
cylinder("Cold_Crest", (0, .12, 2.35), .08, .13, CYAN, 20)

parts = [obj for obj in asset.objects if obj.type == "MESH"]
triangles = sum(len(poly.vertices)-2 for obj in parts for poly in obj.data.polygons)
assert 30 <= len(parts) <= 45 and 3000 < triangles < 15000, (len(parts), triangles)
points = [obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
minimum = [round(min(point[axis] for point in points), 3) for axis in range(3)]
maximum = [round(max(point[axis] for point in points), 3) for axis in range(3)]

# Export a joined duplicate; source parts remain individually editable.
bpy.ops.object.select_all(action="DESELECT")
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
render_mesh = bpy.context.object
render_mesh.name = NAME
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
collision = box(f"UCX_{NAME}_00", (0, .04, 1.17), (1.22, .75, 2.34), METAL, 0)
bpy.ops.object.select_all(action="DESELECT")
render_mesh.select_set(True)
collision.select_set(True)
bpy.context.view_layer.objects.active = render_mesh
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         global_scale=1, axis_forward="-Y", axis_up="Z",
                         add_leaf_bones=False, bake_anim=False, path_mode="STRIP")
bpy.data.objects.remove(collision, do_unlink=True)
bpy.data.objects.remove(render_mesh, do_unlink=True)

studio = bpy.data.collections.new("Preview_Studio_NotForFBX")
scene.collection.children.link(studio)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.024))
floor = bpy.context.object
floor.name = "Review_Floor"
floor.data.materials.append(material("M_Review_Stone", (.026, .031, .038), 0, .88))
for col in tuple(floor.users_collection):
    col.objects.unlink(floor)
studio.objects.link(floor)


def area(name, location, color, energy, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.size = size
    obj.rotation_euler = (Vector((0, 0, 1.3))-obj.location).to_track_quat("-Z", "Y").to_euler()
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    studio.objects.link(obj)


area("Lantern_WarmKey", (-1.8, -2.4, 3.4), (1, .68, .39), 230, 3)
area("Alien_CoolRim", (1.7, 1.5, 3), (.4, .7, 1), 240, 2.5)
area("Readable_FrontFill", (1.2, -3.2, 2.3), (.8, .86, 1), 130, 2.3)
bpy.ops.object.camera_add(location=(2.55, -4.25, 2.8))
camera = bpy.context.object
camera.name = "StreetDebtTerminal_ReviewCamera"
camera.rotation_euler = (Vector((0, 0, 1.22))-camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.05
for col in tuple(camera.users_collection):
    col.objects.unlink(camera)
studio.objects.link(camera)
scene.camera = camera
scene.render.engine = "CYCLES"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 1500
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(PREVIEW)
scene.world.color = (.02, .025, .035)
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.5
bpy.ops.render.render(write_still=True)
for font in bpy.data.fonts:
    if Path(bpy.path.abspath(font.filepath)).resolve() == FONT.resolve():
        font.filepath = "//../../Fonts/NotoSansCJKjp-Regular.otf"
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_street_debt_terminal.py",
    "authorship": "Original project-owned geometry and source materials; Japanese glyph geometry from the bundled SIL OFL font",
    "license": "Original project-owned geometry; no purchased assets. Bundled Noto Japanese font is SIL OFL; runtime palette uses separately pinned CC0 Poly Haven materials.",
    "source_blend": BLEND.name,
    "fbx": FBX.name,
    "preview": PREVIEW.name,
    "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "blend_sha256": hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
    "font_sha256": hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "source_parts": len(parts),
    "source_triangles": triangles,
    "collision_boxes": 1,
    "bounds_m": {"min": minimum, "max": maximum},
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "placement": "Ground plane at origin; local -Y front faces the Lantern Ward road",
    "scope": "Decorative campaign prop with established simple collision proxy. UE 5.8.2 import, shader translation, lighting and performance unverified.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
print("STREET_DEBT_TERMINAL_READY", len(parts), triangles, minimum, maximum, FBX)
