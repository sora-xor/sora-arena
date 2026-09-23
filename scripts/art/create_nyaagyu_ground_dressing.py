"""Author the visual-only Nyaagyu Estate roadside leaf/silt/stone module.

Run: blender -b --factory-startup --python scripts/art/create_nyaagyu_ground_dressing.py
Meters. Local X follows the road; local Y points away from its center. The
module is a scattering accent, not gameplay terrain or collision.
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
OUT = ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "SM_Nyaagyu_RoadsideLeafSilt_4m"
BLEND = OUT / "Nyaagyu_RoadsideLeafSilt.blend"
FBX = OUT / f"{NAME}.fbx"
REVIEW = OUT / "Nyaagyu_RoadsideLeafSilt_Blender.png"
SCATTER_REVIEW = OUT / "Nyaagyu_RoadsideLeafSilt_ThreePlacements_Blender.png"
MANIFEST = OUT / "manifest.json"
PH = ROOT / "Content/SourceArt/Environment/PolyHaven"
PH_GLOBAL = json.loads((PH / "manifest.json").read_text())
FOREST = json.loads((OUT / "ScanForestLeaves02/manifest.json").read_text())
ROCK = json.loads((ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01/manifest.json").read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependency_record(asset_id, upstream, folder):
    assert upstream["asset_id"] == asset_id and upstream["license"] == "CC0-1.0"
    files = {}
    for item in upstream["files"]:
        channel = {"Diffuse": "Albedo", "nor_dx": "NormalDX", "arm": "ORM"}[item["channel"]]
        path = folder / item["file"]
        assert sha(path) == item["sha256"]
        files[channel] = {"repo_path": str(path.relative_to(ROOT)),
                          "sha256": item["sha256"], "upstream_url": item["url"]}
    assert set(files) == {"Albedo", "NormalDX", "ORM"}
    return {"asset_id": asset_id, "source_url": upstream["asset_url"],
            "license": upstream["license"], "license_url": upstream["license_url"],
            "authors": upstream["authors"], "files": files}


MUD = next(item for item in PH_GLOBAL["assets"] if item["asset_id"] == "brown_mud_leaves_01")
DEPENDENCIES = {
    "DampSilt": dependency_record("brown_mud_leaves_01", MUD, PH),
    "ForestLitter": dependency_record("forest_leaves_02", FOREST, OUT / "ScanForestLeaves02"),
    "RiverStone": dependency_record("rock_01", ROCK,
                                    ROOT / "Content/SourceArt/Environment/NyaagyuEstateWall/ScanRock01"),
}

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
editable = bpy.data.collections.new("NyaagyuRoadside_Editable")
scene.collection.children.link(editable)
studio = bpy.data.collections.new("Blender_Review_Only")
scene.collection.children.link(studio)
rng = random.Random(0x51A75117)


def pbr(name, source, tint, roughness_bias=0.0, two_sided=False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*tint, 1)
    material.use_backface_culling = not two_sided
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    files = DEPENDENCIES[source]["files"]
    base = nodes.new("ShaderNodeTexImage")
    base.image = bpy.data.images.load(str(ROOT / files["Albedo"]["repo_path"]), check_existing=True)
    base.name = "Pinned_CC0_Albedo"
    mult = nodes.new("ShaderNodeMixRGB")
    mult.blend_type = "MULTIPLY"
    mult.inputs[0].default_value = 1
    mult.inputs[2].default_value = (*tint, 1)
    links.new(base.outputs["Color"], mult.inputs[1])
    links.new(mult.outputs["Color"], bsdf.inputs["Base Color"])
    orm = nodes.new("ShaderNodeTexImage")
    orm.image = bpy.data.images.load(str(ROOT / files["ORM"]["repo_path"]), check_existing=True)
    orm.image.colorspace_settings.name = "Non-Color"
    orm.name = "Pinned_CC0_ORM"
    sep = nodes.new("ShaderNodeSeparateColor")
    sep.mode = "RGB"
    links.new(orm.outputs["Color"], sep.inputs["Color"])
    rough = nodes.new("ShaderNodeMath")
    rough.operation = "ADD"
    rough.inputs[1].default_value = roughness_bias
    links.new(sep.outputs["Green"], rough.inputs[0])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = bpy.data.images.load(str(ROOT / files["NormalDX"]["repo_path"]), check_existing=True)
    normal.image.colorspace_settings.name = "Non-Color"
    normal.name = "Pinned_CC0_NormalDX"
    ns = nodes.new("ShaderNodeSeparateColor")
    ns.mode = "RGB"
    links.new(normal.outputs["Color"], ns.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(ns.outputs["Green"], flip.inputs[1])
    nc = nodes.new("ShaderNodeCombineColor")
    nc.mode = "RGB"
    links.new(ns.outputs["Red"], nc.inputs["Red"])
    links.new(flip.outputs[0], nc.inputs["Green"])
    links.new(ns.outputs["Blue"], nc.inputs["Blue"])
    bump = nodes.new("ShaderNodeNormalMap")
    bump.inputs["Strength"].default_value = 0.55
    links.new(nc.outputs["Color"], bump.inputs["Color"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if name in {"M_Ground_DampSilt", "M_Ground_Moss"}:
        material.surface_render_method = "DITHERED"
        vertex = nodes.new("ShaderNodeVertexColor")
        vertex.layer_name = "EdgeBlend"
        links.new(vertex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return material


SLOTS = {
    "M_Ground_DampSilt": {"source": "DampSilt", "tint": [.79, .76, .72], "roughness_bias": -.08},
    "M_Ground_LeafUmber": {"source": "ForestLitter", "tint": [.69, .48, .32], "roughness_bias": .06, "two_sided": True},
    "M_Ground_LeafOchre": {"source": "ForestLitter", "tint": [.85, .69, .43], "roughness_bias": .04, "two_sided": True},
    "M_Ground_Moss": {"source": "ForestLitter", "tint": [.57, .68, .49], "roughness_bias": .08, "two_sided": True},
    "M_Ground_RiverStone": {"source": "RiverStone", "tint": [.78, .75, .68], "roughness_bias": .07},
    "M_Ground_WetStone": {"source": "RiverStone", "tint": [.49, .51, .49], "roughness_bias": -.09},
}
MATS = {name: pbr(name, **data) for name, data in SLOTS.items()}


def mesh_part(name, vertices, faces, slot, uv_scale=1.0, edge_alpha=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    editable.objects.link(obj)
    obj.data.materials.append(MATS[slot])
    obj["provenance"] = "Original project-authored organic roadside geometry"
    colors = mesh.color_attributes.new(name="EdgeBlend", type="FLOAT_COLOR", domain="CORNER")
    for li, loop in enumerate(mesh.loops):
        alpha = edge_alpha[loop.vertex_index] if edge_alpha else 1.0
        colors.data[li].color = (1.0, 1.0, 1.0, alpha)
    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        axis = max(range(3), key=lambda n: abs(poly.normal[n]))
        for li in poly.loop_indices:
            p = mesh.vertices[mesh.loops[li].vertex_index].co
            if axis == 0:
                u, v = p.y, p.z
            elif axis == 1:
                u, v = p.x, p.z
            else:
                u, v = p.x, p.y
            uv.data[li].uv = (u * uv_scale + .31, v * uv_scale + .18)
    return obj


def silt_lens(i, x, y, rx, ry, phase=0):
    sides, rings = 32, 4
    verts = [(x, y, .025 + .006*rng.random())]
    alpha = [1.0]
    theta_jitter = [rng.uniform(-.07,.07) for _ in range(sides)]
    radial = [rng.uniform(.85,1.11) for _ in range(sides)]
    for ring in range(1, rings+1):
        t = ring/rings
        for s in range(sides):
            angle = math.tau*s/sides + phase + theta_jitter[s]
            r = t * radial[s]
            scallop = 1 + .055*math.sin(angle*5+i) + .03*math.cos(angle*9+2*i)
            px = x + rx*r*math.cos(angle)*scallop
            py = y + ry*r*math.sin(angle)*scallop
            z = .006 + .021*(1-t)**2 + .0035*math.sin(px*11+py*4)*math.sin(py*7)
            if ring == rings:
                z = -.006 + .0015*math.sin(angle*7+i)
            verts.append((px, py, z))
            alpha.append((1.0, 1.0, .55, 0.0)[ring-1])
    faces = [(0,1+s,1+(s+1)%sides) for s in range(sides)]
    for ring in range(rings-1):
        a = 1+ring*sides
        b = a+sides
        for s in range(sides):
            n = (s+1)%sides
            faces.append((a+s,b+s,b+n,a+n))
    return mesh_part(f"Silt_lens_{i:02}", verts, faces, "M_Ground_DampSilt", 1.2, alpha)


# Five offset damp lenses avoid the ruler-straight edge of a flat rectangular
# decal. Each outer ring tapers almost to the road substrate.
for i, args in enumerate([
    (-1.27,-.36,.72,.61,.2), (-.38,.22,1.10,.69,.6),
    (.95,-.16,.83,.73,.5), (1.42,.52,.47,.45,1.2),
    (-1.54,.39,.44,.43,.7),
]):
    silt_lens(i, *args)


def moss_hummock(i,x,y,rx,ry):
    sides, rings = 15, 3
    verts = [(x,y,.038)]
    alpha = [1.0]
    jitter = [rng.uniform(.8,1.14) for _ in range(sides)]
    for ring in range(1,rings+1):
        t = ring/rings
        for s in range(sides):
            a = math.tau*s/sides
            j = jitter[s]
            h = .008 + .034*(1-t*t) + .004*math.sin(a*5+i)
            if ring == rings:
                h = -.003
            verts.append((x+rx*t*j*math.cos(a),y+ry*t*j*math.sin(a),h))
            alpha.append((1.0,.55,0.0)[ring-1])
    faces = [(0,1+s,1+(s+1)%sides) for s in range(sides)]
    for ring in range(rings-1):
        a,b = 1+ring*sides,1+(ring+1)*sides
        for s in range(sides):
            n=(s+1)%sides
            faces.append((a+s,b+s,b+n,a+n))
    mesh_part(f"Moss_hummock_{i:02}",verts,faces,"M_Ground_Moss",1.55,alpha)


moss_centers = []
for i in range(17):
    x,y = rng.uniform(-1.78,1.78), rng.uniform(-.90,.90)
    rx,ry = rng.uniform(.11,.31),rng.uniform(.09,.25)
    moss_centers.append((x,y,rx,ry))
    moss_hummock(i,x,y,rx,ry)


for i in range(22):
    x,y = rng.uniform(-1.9,1.9),rng.uniform(-.98,.98)
    radius = rng.uniform(.045,.085)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x,y,0))
    obj = bpy.context.object
    obj.name = f"Irregular_stone_{i:02}"
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    editable.objects.link(obj)
    obj.data.materials.append(MATS["M_Ground_WetStone" if i%4==0 else "M_Ground_RiverStone"])
    obj["provenance"] = "Original project-authored organic roadside geometry"
    sx,sy,sz = radius*rng.uniform(1.15,1.8), radius*rng.uniform(.78,1.2),radius*rng.uniform(.43,.72)
    angle = rng.uniform(0,math.tau)
    ca,sa=math.cos(angle),math.sin(angle)
    for v in obj.data.vertices:
        q=v.co
        r=1+.13*math.sin(5*q.x+3*q.y+i)+.08*math.cos(7*q.z-2*q.y+i)
        r+=.025*math.sin(19*q.x+11*q.z+i*2.1)*math.cos(15*q.y-8*q.z)
        px,py=sx*q.x*r,sy*q.y*r
        q.x=ca*px-sa*py
        q.y=sa*px+ca*py
        q.z=max(.007,sz*(q.z+.30)*r)
    colors=obj.data.color_attributes.new(name="EdgeBlend",type="FLOAT_COLOR",domain="CORNER")
    for datum in colors.data:
        datum.color=(1,1,1,1)
    uv=obj.data.uv_layers.new(name="UVMap")
    for p in obj.data.polygons:
        p.use_smooth = True
        axis=max(range(3),key=lambda n:abs(p.normal[n]))
        for li in p.loop_indices:
            v=obj.data.vertices[obj.data.loops[li].vertex_index].co
            u,w=(v.y,v.z) if axis==0 else ((v.x,v.z) if axis==1 else (v.x,v.y))
            uv.data[li].uv=(u*4.8+.44,w*4.8+.16)


def leaf(i, x, y, angle, length, width, slot):
    ca,sa=math.cos(angle),math.sin(angle)
    verts=[]
    for j in range(5):
        t=j/4
        axis=(t-.5)*length
        taper=(math.sin(math.pi*t)**.7 if j not in (0,4) else .04)
        axis_y=.09*length*math.sin(math.pi*t*1.5)
        for side in (-1,0,1):
            lateral=side*width*taper*.5
            px=axis
            py=axis_y+lateral
            z=.012 + .004*math.sin(math.pi*t) + (.003 if side==0 else .0015*math.sin(t*7+i))
            verts.append((x+ca*px-sa*py,y+sa*px+ca*py,z))
    faces=[]
    for j in range(4):
        a,b=j*3,(j+1)*3
        faces += [(a,b,b+1,a+1),(a+1,b+1,b+2,a+2)]
    obj=mesh_part(f"Fallen_leaf_{i:03}",verts,faces,slot,6.0)
    for p in obj.data.polygons:
        p.use_smooth=False


for i in range(126):
    x,y=rng.uniform(-1.95,1.95),rng.uniform(-1.03,1.03)
    leaf(i,x,y,rng.uniform(0,math.tau),rng.uniform(.065,.13),rng.uniform(.025,.056),
         "M_Ground_LeafOchre" if i%3==0 else "M_Ground_LeafUmber")


def twig(i,x,y,length,angle):
    ca,sa=math.cos(angle),math.sin(angle)
    vertices=[]
    rings=5
    for j in range(rings):
        t=j/(rings-1)
        cx=x+ca*(t-.5)*length-.023*sa*math.sin(t*5+i)
        cy=y+sa*(t-.5)*length+.023*ca*math.sin(t*5+i)
        radius=(.0035+.0045*(1-t))*(.84+.16*math.sin(t*8+i))
        for k in range(5):
            a=math.tau*k/5
            vertices.append((cx-sa*radius*math.cos(a),cy+ca*radius*math.cos(a),
                             .015+radius*math.sin(a)+.009*math.sin(t*math.pi)))
    faces=[]
    for j in range(rings-1):
        for k in range(5):
            n=(k+1)%5
            faces.append((j*5+k,j*5+n,(j+1)*5+n,(j+1)*5+k))
    mesh_part(f"Twig_{i:02}",vertices,faces,"M_Ground_LeafUmber",4.0)


for i in range(22):
    twig(i,rng.uniform(-1.85,1.85),rng.uniform(-.93,.93),rng.uniform(.13,.39),rng.uniform(0,math.tau))


# Fine individual sprigs are actual geometry rather than an opacity billboard.
for i,(x,y,rx,ry) in enumerate(moss_centers):
    verts=[]
    faces=[]
    count=13 if i%3 else 18
    for j in range(count):
        a=rng.uniform(0,math.tau)
        bx=x+rng.uniform(.12,.81)*rx*math.cos(a)
        by=y+rng.uniform(.12,.81)*ry*math.sin(a)
        az=rng.uniform(.013,.032)
        h=rng.uniform(.016,.048)
        w=rng.uniform(.003,.006)
        theta=rng.uniform(0,math.tau)
        u,v=w*math.cos(theta),w*math.sin(theta)
        start=len(verts)
        verts += [(bx-u,by-v,az),(bx+u,by+v,az),
                  (bx+.7*u+.008*math.cos(theta),by+.7*v+.008*math.sin(theta),az+h)]
        faces.append((start,start+1,start+2))
    mesh_part(f"Moss_sprigs_{i:02}",verts,faces,"M_Ground_Moss",7.0)


source_meshes=sorted((obj for obj in editable.objects if obj.type=="MESH"), key=lambda o:o.name)
triangles=sum(len(poly.vertices)-2 for obj in source_meshes for poly in obj.data.polygons)
points=[obj.matrix_world @ v.co for obj in source_meshes for v in obj.data.vertices]
bounds={"min":[round(min(p[i] for p in points),4) for i in range(3)],
        "max":[round(max(p[i] for p in points),4) for i in range(3)]}
assert -2.2<bounds["min"][0]<-1.8 and 1.8<bounds["max"][0]<2.2
assert -1.3<bounds["min"][1]<-1.0 and 1.0<bounds["max"][1]<1.3
assert -.02<=bounds["min"][2] and bounds["max"][2]<.2

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
for collection in tuple(export.users_collection):
    collection.objects.unlink(export)
export_collection.objects.link(export)
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, add_leaf_bones=False,
                         apply_unit_scale=True, axis_forward="-Y", axis_up="Z",
                         path_mode="STRIP")
export.hide_render=True
export.hide_set(True)
bpy.ops.object.select_all(action="DESELECT")


def review_material(name,color):
    material=bpy.data.materials.new(name)
    material.diffuse_color=(*color,1)
    material.use_nodes=True
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(*color,1)
    material.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value=.94
    return material


bpy.ops.mesh.primitive_plane_add(size=2)
ground=bpy.context.object
ground.name="Review_existing_terrain_only"
for collection in tuple(ground.users_collection):
    collection.objects.unlink(ground)
studio.objects.link(ground)
ground.dimensions=(9,6,0)
ground.location.z=-.002
ground.data.materials.append(pbr("Review_Estate_soil", "DampSilt", (.72,.70,.66), .02))
uv=ground.data.uv_layers.active
for loop in uv.data:
    loop.uv[0] *= 2.8
    loop.uv[1] *= 1.9


def area(name,location,energy,size,color):
    light=bpy.data.lights.new(name,"AREA")
    light.energy=energy
    light.shape="DISK"
    light.size=size
    light.color=color
    obj=bpy.data.objects.new(name,light)
    studio.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,0,0))-obj.location).to_track_quat("-Z","Y").to_euler()


area("Cloud_key",(1.6,-2.5,4.2),620,3.0,(1,.92,.81))
area("Cool_sky",(-2.5,1.9,3.1),300,3.0,(.75,.84,1))
world=bpy.data.worlds.new("Estate_ground_overcast_review")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.18,.20,.22,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.38
camdata=bpy.data.cameras.new("Review_camera")
camera=bpy.data.objects.new("Review_camera",camdata)
studio.objects.link(camera)
scene.camera=camera
camdata.type="ORTHO"
camdata.ortho_scale=5.4
camera.location=(3.1,-4.6,4.5)
camera.rotation_euler=(Vector((0,0,.03))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.engine="CYCLES"
scene.cycles.samples=40
scene.render.resolution_x=1600
scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
scene.render.filepath=str(REVIEW)
bpy.ops.render.render(write_still=True)

# A second review demonstrates non-repeating placement from one mesh: natural
# angular variation and modest size changes keep the silhouette from reading
# as a tiled rectangle. These are review instances, never part of the FBX.
PLACEMENT_VARIANTS=[
    {"yaw_deg":14.0,"uniform_scale":.92,"review_x_m":-4.25,"review_y_m":.35},
    {"yaw_deg":171.0,"uniform_scale":1.04,"review_x_m":0.0,"review_y_m":-.22},
    {"yaw_deg":-22.0,"uniform_scale":.87,"review_x_m":4.18,"review_y_m":.40},
]
for obj in source_meshes:
    obj.hide_render=True
review_instances=[]
for i,v in enumerate(PLACEMENT_VARIANTS):
    instance=bpy.data.objects.new(f"Review_variant_{i+1}",export.data)
    studio.objects.link(instance)
    instance.location=(v["review_x_m"],v["review_y_m"],0)
    instance.rotation_euler.z=math.radians(v["yaw_deg"])
    instance.scale=(v["uniform_scale"],)*3
    review_instances.append(instance)
ground.dimensions=(17,8,0)
camdata.ortho_scale=13.4
camera.location=(5.5,-9.5,7.2)
camera.rotation_euler=(Vector((0,0,.03))-camera.location).to_track_quat("-Z","Y").to_euler()
scene.render.filepath=str(SCATTER_REVIEW)
bpy.ops.render.render(write_still=True)
for obj in review_instances:
    obj.hide_render=True
for obj in source_meshes:
    obj.hide_render=False
ground.dimensions=(9,6,0)
camdata.ortho_scale=5.4
camera.location=(3.1,-4.6,4.5)
camera.rotation_euler=(Vector((0,0,.03))-camera.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

slots=sorted(material.name for material in export.data.materials)
record={
    "schema_version":1,
    "name":NAME,
    "generator":"scripts/art/create_nyaagyu_ground_dressing.py",
    "generator_sha256":sha(ROOT/"scripts/art/create_nyaagyu_ground_dressing.py"),
    "source_blend":BLEND.name,"blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "review":REVIEW.name,"review_sha256":sha(REVIEW),
    "scatter_review":SCATTER_REVIEW.name,"scatter_review_sha256":sha(SCATTER_REVIEW),
    "source_parts":len(source_meshes),"source_triangles":triangles,
    "bounds_m":bounds,"nominal_road_length_m":4.0,
    "orientation":"Local X follows Estate road; +Y points outward from road center; +Z up",
    "placement_variants":PLACEMENT_VARIANTS,
    "collision":"Visual only; flat Estate terrain collision remains authoritative; no asset or runtime collision",
    "nanite_windows":True,
    "mac_conventional_fallback":{"source_fbx":FBX.name,
                                 "fallback_percent_triangles":1.0,
                                 "fallback_target":"PercentTriangles",
                                 "generate_fallback":"Enabled",
                                 "render_config":"Config/Mac/MacEngine.ini"},
    "material_slots":slots,"slot_definitions":SLOTS,
    "dependencies":DEPENDENCIES,
    "new_scan_manifest_sha256":sha(OUT/"ScanForestLeaves02/manifest.json"),
    "unreal_asset":f"/Game/Generated/Environment/Props/{NAME}.{NAME}",
    "license":"Original project-owned geometry and locally pinned Poly Haven CC0-1.0 PBR scans; no paid assets",
    "limitations":"Vegetation/stone scattering study. The source review is a Blender render, not an Unreal runtime image; repeated tiling, terrain height fit, 5.8.2 shader import, and frame cost remain to be measured. Tiny stones are visual and non-colliding.",
}
MANIFEST.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_GROUND_DRESSING_CREATED",len(source_meshes),triangles,bounds,slots)
