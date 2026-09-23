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
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "Content/SourceArt/Fonts/NotoSansCJKjp-Regular.otf"
NAME = "SM_Alien_StreetDebtTerminal"
FBX = OUT / (NAME + ".fbx")
BLEND = OUT / "Alien_StreetDebtTerminal.blend"
PREVIEW = OUT / "Alien_StreetDebtTerminal_Blender.png"
BLOCKOUT = OUT / "Alien_StreetDebtTerminal_Blockout_Blender.png"
COMPARISON = OUT / "Alien_StreetDebtTerminal_MaterialComparison_Blender.png"

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


def palette_surface(mat, asset_id, tile, tint=None):
    """Link retained, digest-verified CC0 albedo/normal/ARM as a box projection."""
    palette_manifest = json.loads((PALETTE / "manifest.json").read_text())
    assert palette_manifest["asset_license"] == "CC0-1.0"
    entry = next(entry for entry in palette_manifest["assets"] if entry["asset_id"] == asset_id)
    files = {item["channel"].lower(): item for item in entry["files"]}
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (tile, tile, tile)
    links.new(coords.outputs["Object"], mapping.inputs["Vector"])
    images = {}
    for channel in ("diffuse", "nor_dx", "arm"):
        record = files[channel]
        path = PALETTE / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], path
        image = bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        texture = nodes.new("ShaderNodeTexImage")
        texture.name = channel
        texture.image = image
        texture.projection = "BOX"
        texture.projection_blend = .18
        links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
        images[channel] = texture
    if tint is None:
        links.new(images["diffuse"].outputs["Color"], shader.inputs["Base Color"])
    else:
        # The retained rusty metal map has a pale bare-steel substrate. A
        # cold iron tint keeps the occupation silhouette readable while
        # retaining its actual rust, scratches and photographic variation.
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1
        multiply.inputs[2].default_value = (*tint, 1)
        links.new(images["diffuse"].outputs["Color"], multiply.inputs[1])
        links.new(multiply.outputs[0], shader.inputs["Base Color"])
    channels = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], channels.inputs["Color"])
    links.new(channels.outputs["Green"], shader.inputs["Roughness"])
    links.new(channels.outputs["Blue"], shader.inputs["Metallic"])
    # Poly Haven supplies DirectX normals. Blender's tangent convention needs
    # the green channel flipped; Unreal uses its native DX source files.
    normal_channels = nodes.new("ShaderNodeSeparateColor")
    links.new(images["nor_dx"].outputs["Color"], normal_channels.inputs["Color"])
    flip_green = nodes.new("ShaderNodeMath")
    flip_green.operation = "SUBTRACT"
    flip_green.inputs[0].default_value = 1
    links.new(normal_channels.outputs["Green"], flip_green.inputs[1])
    rgb = nodes.new("ShaderNodeCombineColor")
    links.new(normal_channels.outputs["Red"], rgb.inputs["Red"])
    links.new(flip_green.outputs[0], rgb.inputs["Green"])
    links.new(normal_channels.outputs["Blue"], rgb.inputs["Blue"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = .65
    links.new(rgb.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])


def original_surface_wear(mat, dark, light, scale, bump_distance):
    """Subtle oxidization and micro-roughness on original non-Palette parts."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .24
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].position = .77
    ramp.color_ramp.elements[1].color = (*light, 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    roughness = nodes.new("ShaderNodeMapRange")
    roughness.inputs["To Min"].default_value = .28
    roughness.inputs["To Max"].default_value = .64
    links.new(noise.outputs["Fac"], roughness.inputs["Value"])
    links.new(roughness.outputs["Result"], shader.inputs["Roughness"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .12
    bump.inputs["Distance"].default_value = bump_distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])


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
scene.render.filepath = str(BLOCKOUT)
scene.world.color = (.02, .025, .035)
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -.5
bpy.ops.render.render(write_still=True)

# Retain the exact old flat treatment for a controlled material comparison.
flat_mats = {mat: mat.copy() for mat in
             (TIMBER, METAL, STONE, BRASS, ENAMEL, DISPLAY, CYAN, RED, WASHI)}
for old, flat in flat_mats.items():
    flat.name = "M_ComparisonFlat_" + old.name
palette_surface(TIMBER, "wood_planks_dirt", 1.6)
palette_surface(METAL, "rusty_metal_02", 1.2, (.27, .34, .40))
palette_surface(STONE, "stone_floor", 1.1)
original_surface_wear(BRASS, (.16, .18, .11), (.43, .33, .14), 7, .00022)
original_surface_wear(ENAMEL, (.012, .021, .036), (.034, .07, .09), 25, .00007)
original_surface_wear(DISPLAY, (.008, .013, .019), (.024, .041, .048), 47, .00002)
scene.render.filepath = str(PREVIEW)
bpy.ops.render.render(write_still=True)

# This second source-art render uses identical neutral lighting on both
# versions. Comparison copies are discarded before the editable blend saves.
comparison = bpy.data.collections.new("Temporary_FlatVsPBR_Review")
scene.collection.children.link(comparison)
for source in parts:
    source.hide_render = True
    for side, title in ((-1, "Flat"), (1, "PBR")):
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = "Comparison_" + title + "_" + source.name
        copy.location.x += side*1.65
        copy.hide_render = False
        comparison.objects.link(copy)
        if side < 0:
            for slot in copy.material_slots:
                if slot.material in flat_mats:
                    slot.material = flat_mats[slot.material]
for side, title in ((-1, "FLAT BLOCKOUT"), (1, "PBR MATERIALS")):
    bpy.ops.object.text_add(location=(side*1.65, -.67, 2.92),
                            rotation=(math.pi/2, 0, 0))
    text_obj = bpy.context.object
    text_obj.name = "Comparison_Title_" + title
    text_obj.data.body = title
    text_obj.data.align_x = "CENTER"
    text_obj.data.size = .145
    text_obj.data.materials.append(WASHI)
    for col in tuple(text_obj.users_collection):
        col.objects.unlink(text_obj)
    comparison.objects.link(text_obj)

lights = [bpy.data.objects[name] for name in
          ("Lantern_WarmKey", "Alien_CoolRim", "Readable_FrontFill")]
light_state = [(obj.location.copy(), obj.rotation_euler.copy(),
                tuple(obj.data.color), obj.data.energy, obj.data.size)
               for obj in lights]
for obj in lights:
    obj.data.energy = 0
neutral = lights[0]
neutral.location = (0, -3.6, 4.5)
neutral.data.color = (1, 1, 1)
neutral.data.energy = 620
neutral.data.size = 5.2
neutral.rotation_euler = (Vector((0, 0, 1.3))-neutral.location).to_track_quat("-Z", "Y").to_euler()
bpy.ops.object.camera_add(location=(0, -7, 3.3))
comparison_camera = bpy.context.object
comparison_camera.name = "Temporary_MaterialComparisonCamera"
comparison_camera.rotation_euler = (Vector((0, 0, 1.18))-comparison_camera.location).to_track_quat("-Z", "Y").to_euler()
comparison_camera.data.type = "ORTHO"
comparison_camera.data.ortho_scale = 5.6
scene.camera = comparison_camera
scene.render.resolution_x = 1800
scene.render.resolution_y = 1200
scene.render.filepath = str(COMPARISON)
bpy.ops.render.render(write_still=True)

for obj, state in zip(lights, light_state):
    location, rotation, color, energy, size = state
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.color = color
    obj.data.energy = energy
    obj.data.size = size
for obj in list(comparison.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.data.collections.remove(comparison)
bpy.data.objects.remove(comparison_camera, do_unlink=True)
for source in parts:
    source.hide_render = False
scene.camera = camera
scene.render.resolution_x = 1200
scene.render.resolution_y = 1500
scene.render.filepath = str(PREVIEW)
for image in bpy.data.images:
    if image.source == "FILE":
        path = Path(bpy.path.abspath(image.filepath)).resolve()
        if path.is_relative_to(PALETTE):
            image.filepath = "//../PolyHaven/" + path.relative_to(PALETTE).as_posix()
for font in bpy.data.fonts:
    if Path(bpy.path.abspath(font.filepath)).resolve() == FONT.resolve():
        font.filepath = "//../../Fonts/NotoSansCJKjp-Regular.otf"
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

manifest = {
    "schema_version": 1,
    "name": NAME,
    "generator": "scripts/art/create_street_debt_terminal.py",
    "authorship": "Original project-owned geometry and authored wear; Japanese glyph geometry from the bundled SIL OFL font; retained Poly Haven PBR surface maps",
    "license": "Original project-owned geometry; no purchased assets. Bundled Noto Japanese font is SIL OFL; source and runtime palettes use separately pinned CC0 Poly Haven materials.",
    "source_blend": BLEND.name,
    "fbx": FBX.name,
    "preview": PREVIEW.name,
    "blockout_preview": BLOCKOUT.name,
    "comparison_preview": COMPARISON.name,
    "fbx_sha256": hashlib.sha256(FBX.read_bytes()).hexdigest(),
    "blend_sha256": hashlib.sha256(BLEND.read_bytes()).hexdigest(),
    "preview_sha256": hashlib.sha256(PREVIEW.read_bytes()).hexdigest(),
    "blockout_sha256": hashlib.sha256(BLOCKOUT.read_bytes()).hexdigest(),
    "comparison_sha256": hashlib.sha256(COMPARISON.read_bytes()).hexdigest(),
    "font_sha256": hashlib.sha256(FONT.read_bytes()).hexdigest(),
    "palette_manifest_sha256": hashlib.sha256((PALETTE / "manifest.json").read_bytes()).hexdigest(),
    "palette_asset_ids": ["wood_planks_dirt", "rusty_metal_02", "stone_floor"],
    "source_parts": len(parts),
    "source_triangles": triangles,
    "collision_boxes": 1,
    "bounds_m": {"min": minimum, "max": maximum},
    "unreal_asset": f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "placement": "Ground plane at origin; local -Y front faces the Lantern Ward road",
    "scope": "Decorative campaign prop with source PBR review and established simple collision proxy. UE 5.8.2 import, shader translation, lighting and performance unverified.",
}
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
print("STREET_DEBT_TERMINAL_READY", len(parts), triangles, minimum, maximum, FBX)
