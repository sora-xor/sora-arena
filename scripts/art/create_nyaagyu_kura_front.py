"""Source-only, eye-height study of one weathered Nyaagyu kura frontage.

Run after create_nyaagyu_kura_front_textures.py with Blender 5.2.2 LTS:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_kura_front.py

This derives an alternate full-building visual mesh from the unchanged kura
source. Gameplay collision, the current shipped kura, and WorldBuilder are not
modified. It must pass a packaged first-person A/B before runtime admission.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "Content/SourceArt/Environment/NyaagyuKura/Nyaagyu_ProvisionKura.blend"
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuKuraFront"
PALETTE = ROOT / "Content/SourceArt/Environment/PolyHaven"
NAME = "SM_Nyaagyu_KuraFront_Candidate"
OUT.mkdir(parents=True, exist_ok=True)
BASELINE_PREVIEW = OUT / "KuraFront_Baseline_EyeHeight_Source.png"
assert BASELINE_PREVIEW.is_file(), "Run render_nyaagyu_kura_front_baseline.py first"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.preferences.filepaths.save_version = 0
SCENE = bpy.context.scene
EDITABLE = bpy.data.collections["Nyaagyu_ProvisionKura_Editable"]
STAGE = bpy.data.collections.get("ArtReview_NotForFBX")
if STAGE:
    for obj in list(STAGE.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(STAGE)
for obj in list(bpy.data.objects):
    if obj.type in {"CAMERA", "LIGHT"}:
        bpy.data.objects.remove(obj, do_unlink=True)

# Replace the overly regular flat double doors while leaving the existing
# storehouse plinth, plaster, roof, shutters and SORA-sign artwork untouched.
removed = []
for obj in list(EDITABLE.objects):
    if obj.name.startswith(("LoadingDoor_", "Door_PlankSeam_", "Door_CrossRail_",
                            "Door_Rivet_", "Door_RingPlate_", "Door_PullRing_")):
        removed.append(obj.name)
        bpy.data.objects.remove(obj, do_unlink=True)
assert len(removed) == 38, len(removed)
RETRO = bpy.data.collections.new("KuraFront_Editable_PatinaAndJoinery")
SCENE.collection.children.link(RETRO)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_material(name, color, metallic=0, roughness=.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def image_node(mat, path, colorspace, x, y):
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = colorspace
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.location = (x, y)
    return node


def scan_material(name, files, uv=True, tint=(1, 1, 1)):
    mat = base_material(name, (.35, .29, .22))
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    coord = nodes.new("ShaderNodeTexCoord")
    coord.location = (-1000, 200)
    albedo = image_node(mat, files["Albedo"], "sRGB", -700, 380)
    normal = image_node(mat, files["NormalDX"], "Non-Color", -700, 50)
    arm = image_node(mat, files["ARM"], "Non-Color", -700, -280)
    source = coord.outputs["UV"] if uv else coord.outputs["Generated"]
    for node in (albedo, normal, arm):
        links.new(source, node.inputs["Vector"])
        if not uv:
            node.projection = "BOX"
            node.projection_blend = .2
    color = nodes.new("ShaderNodeMixRGB")
    color.blend_type = "MULTIPLY"
    color.inputs[0].default_value = 1
    color.inputs[2].default_value = (*tint, 1)
    links.new(albedo.outputs["Color"], color.inputs[1])
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
    split_arm = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split_arm.inputs["Color"])
    links.new(split_arm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split_arm.outputs["Blue"], bsdf.inputs["Metallic"])
    split_normal = nodes.new("ShaderNodeSeparateColor")
    links.new(normal.outputs["Color"], split_normal.inputs["Color"])
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    links.new(split_normal.outputs["Green"], invert.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(split_normal.outputs["Red"], combine.inputs["Red"])
    links.new(invert.outputs[0], combine.inputs["Green"])
    links.new(split_normal.outputs["Blue"], combine.inputs["Blue"])
    nm = nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = .72
    links.new(combine.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


wood_files = {
    "Albedo": OUT / "T_KuraFront_AgedCedar_Albedo_2k.jpg",
    "NormalDX": OUT / "T_KuraFront_AgedCedar_NormalDX_2k.png",
    "ARM": OUT / "T_KuraFront_AgedCedar_ARM_2k.png",
}
tex_manifest = json.loads((OUT / "texture_manifest.json").read_text())
for role, path in wood_files.items():
    assert sha(path) == tex_manifest["atlas_files"][role]["sha256"]
WOOD = scan_material("M_KuraFront_CC0CedarAtlas", wood_files)
TIMBER = bpy.data.materials["M_Env_Timber"]
metal_files = {
    "Albedo": PALETTE / "rusty_metal_02/rusty_metal_02_diff_2k.jpg",
    "NormalDX": PALETTE / "rusty_metal_02/rusty_metal_02_nor_dx_2k.png",
    "ARM": PALETTE / "rusty_metal_02/rusty_metal_02_arm_2k.png",
}
IRON = scan_material("M_KuraFront_ForgedIron", metal_files, uv=False,
                     tint=(.21, .24, .27))


def register(obj, name, mat):
    obj.name = name
    for coll in tuple(obj.users_collection):
        coll.objects.unlink(obj)
    RETRO.objects.link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj["author"] = "Original SORA Arena weathered kura frontage study"
    return obj


def box(name, loc, dims, mat, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = register(bpy.context.object, name, mat)
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("hand_softened_edge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        for face in obj.data.polygons:
            face.use_smooth = True
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                        depth=depth, location=loc,
                                        rotation=(math.pi / 2, 0, 0))
    return register(bpy.context.object, name, mat)


def plank(index, side, board):
    leaf_min = -1.402 if side == -1 else .012
    step = 1.39 / 7
    xlo = leaf_min + board * step + .0018
    xhi = leaf_min + (board + 1) * step - .0018
    zlo, zhi = .78, 3.46
    # Front-face transverse cupping and three gentle height warps are explicit
    # geometry. The photographed cedar atlas supplies only surface microdetail.
    xs = [xlo, (xlo+xhi)/2, xhi]
    zs = [zlo + (zhi-zlo)*i/5 for i in range(6)]
    front, rear = [], []
    vertices = []
    for layer in (0, 1):
        for iz, z in enumerate(zs):
            for ix, x in enumerate(xs):
                y = (-3.128 - (.007 if ix == 1 else 0)
                     - .003 * math.sin(iz * 1.21 + index * .77)) if layer == 0 else -3.045
                vertices.append((x, y, z + .002 * math.sin(index * 1.73 + ix)))
                (front if layer == 0 else rear).append(len(vertices)-1)
    faces = []
    for iz in range(5):
        for ix in range(2):
            a = iz*3+ix
            faces.append((front[a], front[a+1], front[a+4], front[a+3]))
            faces.append((rear[a+3], rear[a+4], rear[a+1], rear[a]))
    for iz in range(5):
        a = iz*3
        faces.append((front[a+3], front[a], rear[a], rear[a+3]))
        faces.append((front[a+2], front[a+5], rear[a+5], rear[a+2]))
    for ix in range(2):
        faces.append((front[ix], front[ix+1], rear[ix+1], rear[ix]))
        top = 5*3+ix
        faces.append((front[top+1], front[top], rear[top], rear[top+1]))
    data = bpy.data.meshes.new(f"CedarPlank_{index:02d}")
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(data.name, data)
    RETRO.objects.link(obj)
    obj.data.materials.append(WOOD)
    obj["author"] = "Original 3D board, CC0 photographic cedar-derived PBR atlas"
    uv = data.uv_layers.new(name="UV0")
    u0 = index / 14
    u1 = (index + 1) / 14
    for face in data.polygons:
        for li in face.loop_indices:
            v = data.vertices[data.loops[li].vertex_index].co
            frac = (v.x-xlo)/(xhi-xlo)
            uv.data[li].uv = (u0 + (u1-u0)*frac, (v.z-zlo)/(zhi-zlo))
    return obj


for side in (-1, 1):
    for board in range(7):
        index = (0 if side == -1 else 7) + board
        plank(index, side, board)
    center = side * .706
    for z in (1.14, 2.06, 2.98):
        # The three forged straps are not perfectly equal: the center strap
        # is slightly thicker where the pull loads the door.
        strap = box(f"Hammered_Strap_{side}_{z}", (center,-3.159,z),
                    (1.31,.035,.075 if z != 2.06 else .09), IRON, .004)
        for xoffset in (-.54, -.21, .21, .54):
            cylinder(f"Peened_Rivet_{side}_{z}_{xoffset}",
                     (center+xoffset,-3.185,z), .016, .016, IRON, 12)
    cylinder(f"Pull_Backplate_{side}", (side*.20,-3.194,2.04),
             .098,.018,IRON,24)
    bpy.ops.mesh.primitive_torus_add(major_segments=32, minor_segments=8,
                                    location=(side*.20,-3.222,2.01),
                                    rotation=(math.pi/2,0,0),
                                    major_radius=.058, minor_radius=.009)
    register(bpy.context.object, f"Forged_PullRing_{side}", IRON)

# One lowered, warped rain-board sits below the sign and helps the front wall
# read as layered timber and plaster at eye level rather than a flat swatch.
box("Doorhead_RainBoard",(0,-3.142,3.52),(3.14,.10,.068),TIMBER,.005)
for x in (-1.46,0,1.46):
    cylinder(f"RainBoard_Peg_{x}",(x,-3.203,3.52),.022,.016,IRON,12)

# Export only the parent architectural source and the new editable front. The
# base Kura blend and main runtime remain unchanged; imported collision must
# be disabled because the existing WorldBuilder boxes retain gameplay truth.
source = [o for coll in (EDITABLE,RETRO) for o in coll.objects if o.type=="MESH"]
triangles = sum(len(p.vertices)-2 for o in source for p in o.data.polygons)
corners = [o.matrix_world @ Vector(p) for o in source for p in o.bound_box]
bounds = {"min":[round(min(p[i] for p in corners),3) for i in range(3)],
          "max":[round(max(p[i] for p in corners),3) for i in range(3)]}
bpy.ops.object.select_all(action="DESELECT")
for obj in source:
    obj.select_set(True)
bpy.context.view_layer.objects.active = source[0]
bpy.ops.object.duplicate()
copies = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join()
render = bpy.context.object
render.name = NAME
render["author"] = "Source-only Nyaagyu Kura facade candidate"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# The parent kura has a first UV channel named UVMap. Blender's join retains
# that channel before the new boards' UV0, and Unreal TextureSample reads
# channel 0 by default. Copy the board atlas coordinates onto the exported
# first channel only for cedar faces; leave every parent material's UVs alone.
cedar_index = next(i for i, mat in enumerate(render.data.materials)
                   if mat and mat.name == "M_KuraFront_CC0CedarAtlas")
assert render.data.uv_layers[0].name == "UVMap"
assert "UV0" in render.data.uv_layers
export_uv = render.data.uv_layers[0].data
board_uv = render.data.uv_layers["UV0"].data
cedar_polygons = [face for face in render.data.polygons
                  if face.material_index == cedar_index]
assert len(cedar_polygons) >= 400
for face in cedar_polygons:
    for loop_index in face.loop_indices:
        export_uv[loop_index].uv = board_uv[loop_index].uv
bpy.ops.object.select_all(action="DESELECT")
render.select_set(True)
bpy.context.view_layer.objects.active = render
fbx = OUT / f"{NAME}.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
    object_types={"MESH"},apply_unit_scale=True,global_scale=1,
    axis_forward="-Y",axis_up="Z",add_leaf_bones=False,
    bake_anim=False,path_mode="STRIP")
bpy.data.objects.remove(render,do_unlink=True)

def area(name, loc, energy, color, size, target):
    bpy.ops.object.light_add(type="AREA",location=loc)
    ob=bpy.context.object
    ob.name=name
    ob.data.energy=energy
    ob.data.color=color
    ob.data.shape="DISK"
    ob.data.size=size
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler()

area("EyeHeight_WarmSky",(-4.6,-7,7.5),1600,(1,.79,.61),6,(0,-3,2))
area("EyeHeight_CoolBounce",(4,-5,5.5),950,(.69,.82,1),5,(0,-3,2))
bpy.ops.object.camera_add(location=(4.8,-10,1.58))
camera=bpy.context.object
camera.name="KuraFront_Close_EyeHeight"
camera.rotation_euler=(Vector((0,-3.1,2.25))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="PERSP"
camera.data.lens=32
SCENE.camera=camera
SCENE.world.color=(.16,.17,.19)
SCENE.render.engine="CYCLES"
SCENE.cycles.samples=48
SCENE.cycles.use_denoising=True
SCENE.render.resolution_x=1400
SCENE.render.resolution_y=900
SCENE.render.resolution_percentage=100
SCENE.view_settings.view_transform="AgX"
SCENE.view_settings.exposure=-.4
preview=OUT/"KuraFront_Close_EyeHeight_Source.png"
SCENE.render.filepath=str(preview)
SCENE.render.image_settings.file_format="PNG"
bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source=="FILE":
        # Save-as remaps absolute paths relative to the new blend location.
        # Precomputing // paths here would be remapped from the old Kura blend.
        image.filepath=bpy.path.abspath(image.filepath)
blend=OUT/"Nyaagyu_KuraFront_Candidate.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend),relative_remap=True)

manifest = {
    "schema_version":1,"name":NAME,
    "generator":"scripts/art/create_nyaagyu_kura_front.py",
    "generator_sha256":sha(ROOT/"scripts/art/create_nyaagyu_kura_front.py"),
    "base_source":"Content/SourceArt/Environment/NyaagyuKura/Nyaagyu_ProvisionKura.blend",
    "base_source_sha256":sha(BASE),
    "blender_version":bpy.app.version_string,
    "source_blend":blend.name,"source_blend_sha256":sha(blend),
    "fbx":fbx.name,"fbx_sha256":sha(fbx),
    "preview":preview.name,"preview_sha256":sha(preview),
    "baseline_preview":BASELINE_PREVIEW.name,
    "baseline_preview_sha256":sha(BASELINE_PREVIEW),
    "texture_manifest":"texture_manifest.json",
    "texture_manifest_sha256":sha(OUT/"texture_manifest.json"),
    "source_parts":len(source),"source_triangles":triangles,
    "removed_flat_door_parts":len(removed),
    "new_front_parts":len([o for o in RETRO.objects if o.type=="MESH"]),
    "door_board_count":14,"door_uv_layer":"UV0",
    "bounds_m":bounds,
    "collision":"Visual only. Preserve established WorldBuilder building collision; this FBX includes no UCX or newly authoritative hit surface.",
    "placement":"Candidate one-off visual replacement for the southern first visible provision Kura at (-1000,-1800,0) cm, yaw 180 degrees; not runtime admitted.",
    "licenses":"Base kura geometry is original project-owned; SORA mark is exact user-supplied SVG. Cedar PBR atlas derives from pinned CC0 Poly Haven Wood Planks Dirt; forge-iron maps derive from pinned CC0 Poly Haven Rusty Metal 02. Existing plaster, roof and stone PBR are pinned CC0 Poly Haven. No purchased assets.",
    "scope":"Source-only close eye-height art review. Packaged first-person composition and performance gate still required; no AAA claim.",
}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("NYAAGYU_KURA_FRONT_SOURCE_READY",len(source),triangles,bounds,flush=True)
