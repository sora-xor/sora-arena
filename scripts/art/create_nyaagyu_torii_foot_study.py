"""Sculpt a scan-backed, fitted stone-foot study for the Estate entrance torii.

This is an *additive review candidate*. The historical gate mesh and gameplay
collision are left intact. The first-person Unreal A/B decides whether these
stones should replace the visible blockout foot; Blender previews do not.

  blender -b --factory-startup --python scripts/art/create_nyaagyu_torii_foot_study.py
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuToriiFootStudy"
SCAN = OUT / "MossyRock"
SCAN_FILES = {
    "diffuse": "mossy_rock_diff_2k.jpg",
    "normal_dx": "mossy_rock_nor_dx_2k.png",
    "arm": "mossy_rock_arm_2k.png",
    "displacement": "mossy_rock_disp_2k.png",
}
OUT.mkdir(parents=True, exist_ok=True)
for name in SCAN_FILES.values():
    assert (SCAN / name).is_file(), f"Missing pinned CC0 scan {name}"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.render.resolution_x = 1400
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (.38, .42, .47)

editable = bpy.data.collections.new("Torii_FittedFoot_Editable")
scene.collection.children.link(editable)
review = bpy.data.collections.new("Review_Only_NotForFBX")
scene.collection.children.link(review)


def move(obj, name, collection=editable):
    obj.name = name
    for existing in tuple(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)
    obj["art_role"] = "visual-only hewn stone foot; no combat collision"
    return obj


def scan_material():
    mat = bpy.data.materials.new("M_ToriiFoot_MossyRock_CC0")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = .82
    uv = nodes.new("ShaderNodeTexCoord")
    uv.location = (-900, 200)
    images = {}
    for i, (channel, file_name) in enumerate(SCAN_FILES.items()):
        if channel == "displacement":
            continue
        image = bpy.data.images.load(str(SCAN / file_name), check_existing=True)
        image.filepath = bpy.path.relpath(str(SCAN / file_name))
        image.colorspace_settings.name = "sRGB" if channel == "diffuse" else "Non-Color"
        tex = nodes.new("ShaderNodeTexImage")
        tex.name = channel
        tex.location = (-650, 250 - 280*i)
        tex.image = image
        links.new(uv.outputs["UV"], tex.inputs["Vector"])
        images[channel] = tex
    links.new(images["diffuse"].outputs["Color"], bsdf.inputs["Base Color"])
    arm = nodes.new("ShaderNodeSeparateColor")
    links.new(images["arm"].outputs["Color"], arm.inputs["Color"])
    links.new(arm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(arm.outputs["Blue"], bsdf.inputs["Metallic"])
    # The downloaded normal is DirectX; Blender needs the green channel reversed.
    nsplit = nodes.new("ShaderNodeSeparateColor")
    links.new(images["normal_dx"].outputs["Color"], nsplit.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1.0
    links.new(nsplit.outputs["Green"], flip.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(nsplit.outputs["Red"], combine.inputs["Red"])
    links.new(flip.outputs[0], combine.inputs["Green"])
    links.new(nsplit.outputs["Blue"], combine.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .75
    links.new(combine.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


STONE = scan_material()


def matte(name, rgb, roughness=1.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*rgb, 1)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*rgb, 1)
    principled.inputs["Roughness"].default_value = roughness
    return material


EARTH = matte("M_Review_Earth", (.14, .145, .115))
OLD_STONE = matte("M_Review_OldBlockFoot", (.28, .28, .25))
POST = matte("M_Review_VermilionPost", (.30, .040, .025), .4)


def foot(side: int):
    """Many rings of uneven hewn contour; real geometry at silhouette scale."""
    rng = random.Random(18091 + side*17)
    cx = side * 2.35
    segments = 96
    elevations = [-.012, .006, .032, .055, .082, .113, .143, .174,
                  .205, .236, .267, .297, .326, .354, .379, .402, .425, .444]
    verts = []
    for ri, z in enumerate(elevations):
        taper = (z + .012) / .456
        for j in range(segments):
            angle = math.tau * j / segments
            ca, sa = math.cos(angle), math.sin(angle)
            power = 9.0
            squarish_x = math.copysign(abs(ca)**(2/power), ca)
            squarish_y = math.copysign(abs(sa)**(2/power), sa)
            # Chisel chips are coherent vertically; broad corners are not smooth
            # bevels. Keep stone larger than the original .55 x .53 m cube.
            chip = (.008*math.sin(11*angle + side*.8 + z*7.1)
                    + .005*math.sin(29*angle - z*17.3)
                    + .0025*math.sin(73*angle + z*23.0))
            hx = .373 - .045*taper + chip
            hy = .365 - .038*taper + chip*.8
            weather = .0035*math.sin(z*57 + j*.77) + .002*math.sin(z*91-j*2.11)
            verts.append((cx + hx*squarish_x + weather*ca,
                          hy*squarish_y + weather*sa,
                          z + (.003 if ri in (0, len(elevations)-1) else .0018)*
                          math.sin(j*.91 + side*.3)))
    faces = []
    for ri in range(len(elevations)-1):
        for j in range(segments):
            a = ri*segments+j
            b = ri*segments+(j+1)%segments
            faces.append((a, b, b+segments, a+segments))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple((len(elevations)-1)*segments+j for j in range(segments)))
    mesh = bpy.data.meshes.new(f"ToriiFoot_{side}_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(f"Hewn_StoneFoot_{side}", mesh)
    editable.objects.link(obj)
    mesh.materials.append(STONE)
    layer = mesh.uv_layers.new(name="UVMap")
    # One side-wrap; the stone scan covers 1.9m in Poly Haven. The 2.8m
    # perimeter gets ~1.5 texture repeats. Top projects in plan.
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            v = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if polygon.index < (len(elevations)-1)*segments:
                theta = math.atan2(v.y, v.x-cx)
                layer.data[loop_index].uv = ((theta+math.pi)/math.tau*1.45,
                                             v.z/.90)
            else:
                layer.data[loop_index].uv = ((v.x-cx)/1.0 + .5, v.y/1.0 + .5)
    obj["source_scan"] = "Poly Haven mossy_rock CC0 2K"
    obj["art_role"] = "visual-only hewn stone foot; no combat collision"
    obj["slot_origin_m"] = (cx, 0.0, 0.0)
    obj["covers_original_foot"] = True
    # A raised, chipped stone annulus makes the cylindrical timber-to-stone
    # socket physically legible instead of a post simply passing through a cube.
    verts = []
    ring_count = 64
    for radius, z in ((.236, .450), (.292, .450), (.299, .461), (.238, .461)):
        for j in range(ring_count):
            a = math.tau*j/ring_count
            wobble = .002*math.sin(j*1.73 + side)
            verts.append((cx + (radius+wobble)*math.cos(a),
                          (radius+wobble)*math.sin(a), z))
    annulus_faces = []
    for r in range(4):
        for j in range(ring_count):
            n = (r+1)%4
            annulus_faces.append((r*ring_count+j,
                                  r*ring_count+(j+1)%ring_count,
                                  n*ring_count+(j+1)%ring_count,
                                  n*ring_count+j))
    rim_mesh = bpy.data.meshes.new(f"SocketRim_{side}_mesh")
    rim_mesh.from_pydata(verts, [], annulus_faces)
    rim_mesh.update()
    rim = bpy.data.objects.new(f"Chiseled_PostSocket_{side}", rim_mesh)
    editable.objects.link(rim)
    rim["art_role"] = "visual-only hewn stone foot; no combat collision"
    rim_mesh.materials.append(STONE)
    uv = rim_mesh.uv_layers.new(name="UVMap")
    for poly in rim_mesh.polygons:
        for li in poly.loop_indices:
            p = rim_mesh.vertices[rim_mesh.loops[li].vertex_index].co
            uv.data[li].uv = ((p.x-cx)/1.0+.5,p.y/1.0+.5)
    # Loose chips sit against the footing rather than a tidy lens-shaped soil
    # decal. Their tiny silhouettes improve grounding in a near camera.
    for index in range(13):
        angle = rng.uniform(-math.pi, math.pi)
        radius = rng.uniform(.46, .62)
        if abs(math.sin(angle)) < .28:
            continue  # avoid spilling rock onto the center road
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1,
            location=(cx+math.cos(angle)*radius, math.sin(angle)*radius, .014))
        chip = move(bpy.context.object, f"Foot_Talus_{side}_{index}")
        chip.scale = (rng.uniform(.032,.075),rng.uniform(.025,.060),rng.uniform(.010,.027))
        chip.rotation_euler.z = rng.uniform(-math.pi,math.pi)
        chip.data.materials.append(STONE)
        # Icosphere default generated UV supports a review texture; Unreal
        # importer can choose the same scan from this material identity.
        bpy.context.view_layer.objects.active=chip
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


left = foot(-1)
right = foot(1)
source_objects = tuple(editable.objects)
source_triangles = sum(len(poly.vertices)-2 for obj in source_objects if obj.type=="MESH"
                       for poly in obj.data.polygons)

# Export a single visual mesh at the same local origin as the original torii.
bpy.ops.object.select_all(action="DESELECT")
for obj in source_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = left
bpy.ops.object.duplicate()
duplicates = list(bpy.context.selected_objects)
bpy.context.view_layer.objects.active = duplicates[0]
bpy.ops.object.join()
export_obj = bpy.context.object
export_obj.name = "SM_Nyaagyu_ToriiFoot_Study"
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
fbx_path = OUT / "SM_Nyaagyu_ToriiFoot_Study.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True,
    object_types={"MESH"}, apply_unit_scale=True, global_scale=1.0,
    axis_forward="-Y", axis_up="Z", add_leaf_bones=False,
    bake_anim=False, path_mode="STRIP")
bpy.data.objects.remove(export_obj, do_unlink=True)

# Material-close source preview. All review geometry stays separate from FBX.
def cube(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = move(bpy.context.object, name, review)
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


ground = cube("Review_Ground", (0,0,-.055), (7.0,3.4,.10), EARTH)
for side in (-1,1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=.227, depth=2.6,
        location=(side*2.35,0,1.73))
    post = move(bpy.context.object, f"Review_GatePost_{side}", review)
    post.data.materials.append(POST)
    cube(f"Review_OldBlockFoot_{side}", (side*2.35,0,.22), (.55,.53,.44), OLD_STONE)


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.object.camera_add(location=(.7,-7.3,1.85))
camera = move(bpy.context.object, "Review_Camera", review)
aim(camera,(0,0,.63))
camera.data.lens=36
scene.camera=camera
for location, energy, size in (((-3.5,-3.2,5),1500,4.5),((4,1,3.5),900,3.2)):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp=move(bpy.context.object,"Review_Softbox",review)
    lamp.data.energy=energy
    lamp.data.shape="DISK"
    lamp.data.size=size
    aim(lamp,(0,0,.4))

for obj in source_objects:
    obj.hide_render = True
scene.render.filepath=str(OUT/"ToriiFoot_Before_Blender.png")
bpy.ops.render.render(write_still=True)
for obj in source_objects:
    obj.hide_render = False
for obj in review.objects:
    if obj.name.startswith("Review_OldBlockFoot_"):
        obj.hide_render=True
scene.render.filepath=str(OUT/"ToriiFoot_After_Blender.png")
bpy.ops.render.render(write_still=True)

blend_path=OUT/"Nyaagyu_ToriiFoot_Study.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
manifest={
    "schema_version":1,
    "generator":"scripts/art/create_nyaagyu_torii_foot_study.py",
    "source_blend":blend_path.name,
    "fbx":fbx_path.name,
    "fbx_sha256":hashlib.sha256(fbx_path.read_bytes()).hexdigest(),
    "editable_parts":len(source_objects),
    "source_triangles":source_triangles,
    "material_slots":["M_ToriiFoot_MossyRock_CC0"],
    "scan_asset":"https://polyhaven.com/a/mossy_rock",
    "scan_license":"CC0",
    "scan_files":{k:{"file":v,"sha256":hashlib.sha256((SCAN/v).read_bytes()).hexdigest()}
                  for k,v in SCAN_FILES.items()},
    "placement":"local gate origin: centers x=+-2.35 m, y=0; no gameplay collision",
    "visual_gate":"source-only pending fixed-camera packaged UE5.8.3 A/B; not AAA-qualified",
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("NYAAGYU_TORII_FOOT_STUDY_READY",len(source_objects),source_triangles)
