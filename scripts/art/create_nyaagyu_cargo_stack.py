"""Author an original Edo-inspired Estate cargo/cover visual in Blender.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_cargo_stack.py
Coordinates are meters; origin is the center of its ground footprint. The
existing 230 x 180 x 140 cm C++ collision box remains authoritative.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuCargoStack"
PBR = OUT / "PBR"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_CargoStack"
BLEND = OUT / "Nyaagyu_CargoStack.blend"
FBX = OUT / f"{NAME}.fbx"
BEFORE = OUT / "Nyaagyu_CoverProxy_Before_Blender.png"
AFTER = OUT / "Nyaagyu_CargoStack_Blender.png"
MANIFEST = OUT / "manifest.json"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
LOGO_RECORD = json.loads((LOGO.parent / "sora_logo_manifest.json").read_text())
PBR_RECORD = json.loads((PBR / "manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(LOGO) == LOGO_RECORD["source_sha256"]
assert PBR_RECORD["generator_sha256"] == sha(ROOT / PBR_RECORD["generator"])
assert PBR_RECORD["origin"].startswith("Original project-authored deterministic")
for texture_set in PBR_RECORD["sets"]:
    for item in texture_set["maps"]:
        assert sha(PBR / item["file"]) == item["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
parts = bpy.data.collections.new("NyaagyuCargo_Editable")
scene.collection.children.link(parts)
studio = bpy.data.collections.new("Blender_Review_Only")
scene.collection.children.link(studio)


def move(obj, name, collection=parts):
    obj.name = name
    for existing in tuple(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)
    obj["provenance"] = "Original SORA Arena procedural cargo geometry"
    return obj


def flat_material(name, color, roughness, metallic=0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1)
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


sets = {item["name"]: {entry["channel"]: PBR / entry["file"] for entry in item["maps"]}
        for item in PBR_RECORD["sets"]}


def pbr_material(slot, definition):
    material = bpy.data.materials.new(slot)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    images = sets[definition["surface"]]
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = bpy.data.images.load(str(images["Albedo"]), check_existing=True)
    albedo.name = "Original_project_albedo"
    albedo.location = (-720, 210)
    tint = nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = 1
    tint.inputs[2].default_value = (*definition["tint"], 1)
    tint.location = (-430, 210)
    links.new(albedo.outputs["Color"], tint.inputs[1])
    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(images["ORM"]), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    orm.name = "Original_project_ORM"
    orm.location = (-720, -80)
    split_orm = nodes.new("ShaderNodeSeparateColor")
    split_orm.mode = "RGB"
    links.new(orm.outputs["Color"], split_orm.inputs["Color"])
    links.new(split_orm.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split_orm.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(images["NormalDX"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.name = "Original_project_NormalDX"
    normal.location = (-720, -340)
    split_normal = nodes.new("ShaderNodeSeparateColor")
    split_normal.mode = "RGB"
    links.new(normal.outputs["Color"], split_normal.inputs["Color"])
    reverse_green = nodes.new("ShaderNodeMath")
    reverse_green.operation = "SUBTRACT"
    reverse_green.inputs[0].default_value = 1
    links.new(split_normal.outputs["Green"], reverse_green.inputs[1])
    combine = nodes.new("ShaderNodeCombineColor")
    combine.mode = "RGB"
    links.new(split_normal.outputs["Red"], combine.inputs["Red"])
    links.new(reverse_green.outputs[0], combine.inputs["Green"])
    links.new(split_normal.outputs["Blue"], combine.inputs["Blue"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = .52
    links.new(combine.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    return material


PBR_MATS = {name: pbr_material(name, definition)
            for name, definition in PBR_RECORD["material_slots"].items()}
WOOD = PBR_MATS["M_Cargo_AgedTimber"]
DARK = PBR_MATS["M_Cargo_DarkInterior"]
WORN = PBR_MATS["M_Cargo_WornEdge"]
STRAW = PBR_MATS["M_Cargo_StrawWrap"]
ROPE = PBR_MATS["M_Cargo_HempRope"]
INDIGO = PBR_MATS["M_Cargo_IndigoCloth"]
IRON = flat_material("M_Cargo_BlackIron", (.09, .087, .079), .49, .81)
SORA = flat_material("M_Cargo_SORA_Red", (.67, .025, .035), .74)
GROUND = flat_material("M_Review_Ground", (.032, .041, .047), .88)
PROXY = flat_material("M_Review_PlainCover", (.27, .25, .20), .83)


def box(name, center, size, material, bevel=.004, collection=parts):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = move(bpy.context.object, name, collection)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("Softened_handmade_edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def tube(name, points, radius, material, cyclic=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    parts.objects.link(obj)
    obj.data.materials.append(material)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return move(bpy.context.object, name)


def nail(name, center, normal):
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=.006, depth=.003,
                                        location=center)
    obj = move(bpy.context.object, name)
    obj.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    obj.data.materials.append(IRON)


def crate(label, center_x, height):
    width, depth = 1.06, 1.62
    low = .088
    high = low + height
    center_z = (low + high) / 2
    box(f"{label}_structural_core", (center_x, 0, center_z),
        (width-.09, depth-.09, height-.09), DARK, .014)
    for side in (-1, 1):
        front_y = side * (depth/2 + .015)
        for row in range(6):
            z = low + (row+.5)*height/6
            plank = box(f"{label}_front_{side}_plank_{row}",
                        (center_x, front_y, z),
                        (width-.032, .043, height/6-.008), WOOD, .006)
            # Named scuffed cut edges break the manufactured-cube silhouette.
            if row in (1, 4):
                box(f"{label}_front_{side}_edgewear_{row}",
                    (center_x + (-.24 if row==1 else .27),
                     front_y + side*.024, z+height/12-.012),
                    (.10, .0035, .012), WORN, .001)
            for xside in (-1, 1):
                nail(f"{label}_front_{side}_nail_{row}_{xside}",
                     (center_x+xside*(width/2-.065),front_y+side*.024,z),
                     (0,side,0))
        for xside in (-1, 1):
            box(f"{label}_front_{side}_cornerpost_{xside}",
                (center_x+xside*(width/2-.033),side*(depth/2+.015),center_z),
                (.063,.066,height+.015),WOOD,.007)
    for xside in (-1,1):
        x = center_x+xside*(width/2+.006)
        for row in range(6):
            z = low+(row+.5)*height/6
            box(f"{label}_side_{xside}_plank_{row}",
                (x,0,z),(.043,depth-.10,height/6-.008),WOOD,.005)
        for yside in (-1,1):
            box(f"{label}_side_{xside}_endpost_{yside}",
                (x,yside*(depth/2-.037),center_z),
                (.063,.065,height+.015),WOOD,.006)
    for lane in (-1,0,1):
        box(f"{label}_lid_slat_{lane}",
            (center_x+lane*.34,0,high+.022),
            (.335,depth+.024,.039),WOOD,.005)
    for xoffset in (-.25,.25):
        # Real loading lashings go down the front, over the lid and down the
        # rear; each end disappears under the palette rather than hovering.
        x=center_x+xoffset
        tube(f"{label}_lashing_{xoffset:+.2f}",
             [(x,-.85,.11),(x,-.85,high-.03),(x,-.82,high+.052),
              (x,.82,high+.052),(x,.85,high-.03),(x,.85,.11)],.008,ROPE)
    for side in (-1,1):
        for xoffset in (-.29,.29):
            box(f"{label}_iron_corner_band_{side}_{xoffset:+.2f}",
                (center_x+xoffset,side*.845,center_z),
                (.018,.010,height-.08),IRON,.002)
    return high


# Long runners and slatted base give the crates a contact shadow and place all
# visual geometry inside the pre-existing 2.30 x 1.80 m collision footprint.
for y in (-.70,0,.70):
    box(f"Pallet_runner_{y:+.2f}",(0,y,.034),(2.22,.110,.068),WOOD,.006)
for x in (-.79,-.27,.27,.79):
    box(f"Pallet_cross_slats_{x:+.2f}",(x,0,.081),(.36,1.72,.033),WOOD,.005)
crate("LeftRiceCrate",-.55,.91)
crate("RightClothCrate",.55,.92)


def bale(name, center, radii, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, location=center)
    obj = move(bpy.context.object, name)
    obj.scale = radii
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    # Restrained asymmetry follows a stuffed textile silhouette; its underside
    # sinks into the crate lid instead of balancing on a mathematically round
    # contact point.
    for vert in obj.data.vertices:
        x,y,z=vert.co
        vert.co.x += .008*math.sin(17*y+9*z)
        vert.co.y += .007*math.sin(13*x-7*z)
        if vert.co.z < -.7*radii[2]:
            vert.co.z = max(vert.co.z,-.84*radii[2])
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def bale_belt(name, center, radii, x_offset, material=ROPE):
    cx,cy,cz=center
    rx,ry,rz=radii
    section=math.sqrt(1-(x_offset/rx)**2)
    points=[]
    for step in range(48):
        angle=math.tau*step/48
        points.append((cx+x_offset,cy+(ry*section+.010)*math.cos(angle),
                       cz+(rz*section+.012)*math.sin(angle)))
    tube(name,points,.007,material,cyclic=True)


rice_a=((-0.62,-.37,1.19),(.42,.30,.17))
rice_b=((-0.62,.35,1.19),(.42,.30,.17))
cloth=((.50,0,1.20),(.49,.54,.17))
for index,(center,radii) in enumerate((rice_a,rice_b)):
    bale(f"Rice_tawara_inspired_bundle_{index}",center,radii,STRAW)
    for offset in (-.23,.23):
        bale_belt(f"Rice_bundle_{index}_hemp_belt_{offset:+.2f}",center,radii,offset)
bale("Indigo_craftspeople_cloth_bundle",cloth[0],cloth[1],INDIGO)
for offset in (-.29,.29):
    bale_belt(f"Indigo_bundle_hemp_belt_{offset:+.2f}",cloth[0],cloth[1],offset)
tube("Indigo_bundle_tied_knot",[(.48,-.05,1.355),(.52,0,1.377),
                               (.57,.047,1.35)],.009,ROPE)


def add_exact_sora_stamp():
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(LOGO))
    curves=[obj for obj in set(bpy.data.objects)-before if obj.type=="CURVE"]
    assert len(curves)==2
    corners=[obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
    x0=min(point.x for point in corners);x1=max(point.x for point in corners)
    y0=min(point.y for point in corners);y1=max(point.y for point in corners)
    scale=.17/max(x1-x0,y1-y0)
    for index,obj in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        obj=bpy.context.object
        for vertex in obj.data.vertices:
            p=obj.matrix_world @ vertex.co
            vertex.co=(-.55+(p.x-(x0+x1)/2)*scale,
                       -.87,
                       .53+(p.y-(y0+y1)/2)*scale)
        obj.matrix_world.identity()
        move(obj,f"SORA_kamon_exact_svg_cargo_{index}")
        obj.data.materials.clear()
        obj.data.materials.append(SORA)
        obj["source_svg_sha256"]=LOGO_RECORD["source_sha256"]


add_exact_sora_stamp()

# Explicit local UVs. Plank grain follows each horizontal board's length on
# front/side faces, and the cloth/bales retain their existing sphere UVs.
for obj in parts.objects:
    if obj.type != "MESH" or obj.data.uv_layers:
        continue
    uv=obj.data.uv_layers.new(name="Cargo_PBR_UV")
    for polygon in obj.data.polygons:
        normal=obj.matrix_world.to_3x3() @ polygon.normal
        axis=max(range(3),key=lambda i:abs(normal[i]))
        for loop_index in polygon.loop_indices:
            p=obj.matrix_world @ obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            if axis==0:
                u,v=p.y,p.z
            elif axis==1:
                u,v=p.x,p.z
            else:
                u,v=p.x,p.y
            uv.data[loop_index].uv=(u*3.3,v*3.3)

source_meshes=sorted((obj for obj in parts.objects if obj.type=="MESH"),key=lambda o:o.name)
triangles=sum(len(poly.vertices)-2 for obj in source_meshes for poly in obj.data.polygons)
points=[obj.matrix_world @ vertex.co for obj in source_meshes for vertex in obj.data.vertices]
bounds={"min":[round(min(p[i] for p in points),4) for i in range(3)],
        "max":[round(max(p[i] for p in points),4) for i in range(3)]}
assert bounds["min"][0]>=-1.15 and bounds["max"][0]<=1.15
assert bounds["min"][1]>=-.90 and bounds["max"][1]<=.90
assert bounds["min"][2]>=0 and bounds["max"][2]<=1.40

# Export one static visual mesh; the game keeps its separately authored simple
# collision cube, so the high-detail boards and lashings are never collision.
bpy.ops.object.select_all(action="DESELECT")
for obj in source_meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active=source_meshes[0]
bpy.ops.object.duplicate()
bpy.context.view_layer.objects.active=bpy.context.selected_objects[0]
bpy.ops.object.join()
export=bpy.context.object
export.name=NAME
export_collection=bpy.data.collections.new("Unreal_Export_Only")
scene.collection.children.link(export_collection)
for existing in tuple(export.users_collection):
    existing.objects.unlink(export)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX),use_selection=True,
                         object_types={"MESH"},add_leaf_bones=False,
                         apply_unit_scale=True,axis_forward="-Y",axis_up="Z",
                         path_mode="STRIP")
export.hide_render=True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")

# Same-camera proxy and replacement renders make the art delta inspectable.
floor=box("Review_ground",(0,0,-.027),(200,200,.045),GROUND,.0,studio)
proxy=box("Review_original_cover_cube",(0,0,.70),(2.30,1.80,1.40),PROXY,.0,studio)


def area(name, location, energy, size, color):
    light=bpy.data.lights.new(name,"AREA")
    light.energy=energy
    light.shape="DISK"
    light.size=size
    light.color=color
    obj=bpy.data.objects.new(name,light)
    studio.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,0,.68))-obj.location).to_track_quat("-Z","Y").to_euler()


area("Cloud_key",(2.9,-3.2,3.8),850,3.0,(1,.87,.70))
area("Cool_rim",(-2.5,2.4,2.7),590,2.5,(.57,.75,1))
area("Front_fill",(-2.4,-2.1,2.6),310,2.5,(1,.95,.85))
world=bpy.data.worlds.new("Overcast_Estate_Review")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.11,.13,.16,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.42
camera_data=bpy.data.cameras.new("Review_camera")
camera=bpy.data.objects.new("Review_camera",camera_data)
studio.objects.link(camera)
scene.camera=camera
camera_data.type="ORTHO"
camera_data.ortho_scale=3.25
camera.location=(3.05,-4.1,2.35)
camera.rotation_euler=(Vector((0,0,.70))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.engine="CYCLES"
scene.cycles.samples=40
scene.render.resolution_x=1500
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
for obj in source_meshes:
    obj.hide_render=True
scene.render.filepath=str(BEFORE)
bpy.ops.render.render(write_still=True)
for obj in source_meshes:
    obj.hide_render=False
proxy.hide_render=True
scene.render.filepath=str(AFTER)
bpy.ops.render.render(write_still=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

slots=sorted(material.name for material in export.data.materials)
record={
    "schema_version":1,"name":NAME,
    "generator":"scripts/art/create_nyaagyu_cargo_stack.py",
    "source_blend":BLEND.name,"blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "review_before":BEFORE.name,"review_before_sha256":sha(BEFORE),
    "review_after":AFTER.name,"review_after_sha256":sha(AFTER),
    "source_parts":len(source_meshes),"source_triangles":triangles,
    "bounds_m":bounds,"collision_envelope_m":[2.30,1.80,1.40],
    "collision":"Visual only; existing C++ cube remains the gameplay collision proxy",
    "nanite_windows":True,
    "mac_conventional_fallback":{"source_fbx":FBX.name,
                                 "fallback_percent_triangles":1.0,
                                 "fallback_target":"PercentTriangles",
                                 "generate_fallback":"Enabled",
                                 "render_config":"Config/Mac/MacEngine.ini"},
    "material_slots":slots,"pbr_manifest_sha256":sha(PBR / "manifest.json"),
    "insignia_source":"../../UI/sora_logo_NOtext2.svg",
    "insignia_sha256":LOGO_RECORD["source_sha256"],
    "exact_sora_kamon_objects":[obj.name for obj in source_meshes if obj.name.startswith("SORA_kamon_exact_svg_cargo_")],
    "unreal_asset":f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "license":"Original project-owned geometry, deterministic project-generated PBR textures, and user-supplied exact SORA SVG relief; no paid or third-party texture assets",
    "reference_notes":[
        {"url":"https://www.metmuseum.org/art/collection/search/44674",
         "use":"Edo farming screen depicts baled rice and warehouse storage; no geometry copied"},
        {"url":"https://www.britishmuseum.org/blog/historical-city-travel-guide-osaka-early-19th-century",
         "use":"Edo Osaka grain storage and straw bags context; fictional workshop cargo interpretation"},
    ],
    "limitations":"Static visual replacement art study, not a documented reconstruction of one Edo chest or bale. Rope tension, cloth deformation, weathering, game placement and UE 5.8.2 runtime performance remain unqualified.",
}
MANIFEST.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_CARGO_STACK_CREATED",len(source_meshes),triangles,bounds,slots)
