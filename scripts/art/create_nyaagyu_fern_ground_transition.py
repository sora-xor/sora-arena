"""Author an isolated, visual-only Fern 02 ground-transition study.

Run with Blender 5.2: blender -b --factory-startup --python-exit-code 1 \
    --python scripts/art/create_nyaagyu_fern_ground_transition.py

This source art does not place anything in WorldBuilder. Dimensions are metres.
Local X follows the Estate road; local +Y points into the north shoulder.
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
FERN = ROOT / "Content/SourceArt/Environment/PolyHaven/Fern02"
OUT = FERN / "GroundTransition"
OUT.mkdir(parents=True, exist_ok=True)
GROUND_RECORD = json.loads((ROOT / "Content/SourceArt/Environment/NyaagyuGroundDressing/manifest.json").read_text())
FERN_RECORD = json.loads((FERN / "manifest.json").read_text())
DEPENDENCIES = GROUND_RECORD["dependencies"]
NAME = "SM_NyaagyuFernGroundTransition"
RNG = random.Random(0xF3025107)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


for surface, dep in DEPENDENCIES.items():
    assert dep["license"] == "CC0-1.0", surface
    for item in dep["files"].values():
        assert sha(ROOT / item["repo_path"]) == item["sha256"], item["repo_path"]
for item in FERN_RECORD["meshes"]:
    assert sha(FERN / item["fbx"]) == item["fbx_sha256"], item["fbx"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
editable = bpy.data.collections.new("FernGroundTransition_Editable")
scene.collection.children.link(editable)
studio = bpy.data.collections.new("EyeHeight_ReviewOnly")
scene.collection.children.link(studio)


def image(path: Path, non_color=False):
    result = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        result.colorspace_settings.name = "Non-Color"
    return result


def ground_mat(name, surface, tint):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
    files = DEPENDENCIES[surface]["files"]
    albedo = nodes.new("ShaderNodeTexImage")
    albedo.image = image(ROOT / files["Albedo"]["repo_path"])
    color = nodes.new("ShaderNodeMixRGB")
    color.blend_type = "MULTIPLY"
    color.inputs[0].default_value = 1
    color.inputs[2].default_value = (*tint, 1)
    links.new(albedo.outputs["Color"], color.inputs[1])
    links.new(color.outputs["Color"], bsdf.inputs["Base Color"])
    arm = nodes.new("ShaderNodeTexImage")
    arm.image = image(ROOT / files["ORM"]["repo_path"], True)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(arm.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = image(ROOT / files["NormalDX"]["repo_path"], True)
    separate = nodes.new("ShaderNodeSeparateColor")
    invert = nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1
    combine = nodes.new("ShaderNodeCombineColor")
    links.new(normal.outputs["Color"], separate.inputs["Color"])
    links.new(separate.outputs["Green"], invert.inputs[1])
    links.new(separate.outputs["Red"], combine.inputs["Red"])
    links.new(invert.outputs[0], combine.inputs["Green"])
    links.new(separate.outputs["Blue"], combine.inputs["Blue"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = .65
    links.new(combine.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    if name.endswith("Soil") or name.endswith("Litter"):
        mat.surface_render_method = "DITHERED"
        vertex = nodes.new("ShaderNodeVertexColor")
        vertex.layer_name = "EdgeBlend"
        links.new(vertex.outputs["Alpha"], bsdf.inputs["Alpha"])
    return mat


MATS = {
    "soil": ground_mat("M_FernGround_Soil", "DampSilt", (.50, .50, .49)),
    "litter": ground_mat("M_FernGround_Litter", "ForestLitter", (.68, .65, .61)),
    "stone": ground_mat("M_FernGround_Stone", "RiverStone", (.73, .71, .66)),
    "root": ground_mat("M_FernGround_Root", "ForestLitter", (.48, .38, .31)),
}


def fern_mat(tier):
    mat = bpy.data.materials.new("M_Fern02_4K" if tier == "hi" else "M_Fern02_2K")
    mat.use_nodes = True
    mat.surface_render_method = "DITHERED"
    mat.use_backface_culling = False
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    res = "4k" if tier == "hi" else "2k"
    paths = {key: FERN / "Upstream/textures" / f"fern_02_{key}_{res}.{ext}"
             for key, ext in (("diff", "jpg"), ("alpha", "png"),
                              ("arm", "jpg"), ("nor_gl", "jpg"))}
    for key, pin in (("diff", "Base Color"), ("alpha", "Alpha")):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image(paths[key], key == "alpha")
        links.new(tex.outputs["Color"], shader.inputs[pin])
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image(paths["arm"], True)
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(tex.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], shader.inputs["Roughness"])
    normal = nodes.new("ShaderNodeTexImage")
    normal.image = image(paths["nor_gl"], True)
    normap = nodes.new("ShaderNodeNormalMap")
    links.new(normal.outputs["Color"], normap.inputs["Color"])
    links.new(normap.outputs["Normal"], shader.inputs["Normal"])
    return mat


MATS["fern_hi"] = fern_mat("hi")
MATS["fern_mac"] = fern_mat("mac")


def relief(x, y):
    # Gently raised centre; the irregular perimeter is buried below terrain.
    radial = (x / 1.58) ** 2 + (y / .61) ** 2
    dome = .054 * max(0.0, 1.0 - radial) ** 1.4
    detail = .006 * math.sin(7.5*x + 3.2*y) * math.cos(9.2*y - 2.1*x)
    return .018 + dome + detail


def part(name, verts, faces, mat, uv_scale, edge_alpha=None):
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    editable.objects.link(obj)
    obj.data.materials.append(mat)
    mesh.color_attributes.new(name="EdgeBlend", type="FLOAT_COLOR", domain="CORNER")
    for loop in mesh.loops:
        alpha = edge_alpha[loop.vertex_index] if edge_alpha else 1.0
        mesh.color_attributes["EdgeBlend"].data[loop.index].color = (1,1,1,alpha)
    uv = mesh.uv_layers.new(name="UVMap")
    for face in mesh.polygons:
        for index in face.loop_indices:
            v = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = (v.x * uv_scale + .18, v.y * uv_scale + .37)
    return obj


def island(name, x, y, rx, ry, slot, phase, height_bias=0):
    sides, rings = 48, 6
    verts = [(x, y, relief(x,y) + height_bias + .003)]
    alpha = [1.0]
    offset = [RNG.uniform(-.09,.09) for _ in range(sides)]
    irregular = [RNG.uniform(.87,1.09) for _ in range(sides)]
    for r in range(1,rings+1):
        t = r/rings
        for s in range(sides):
            a = math.tau*s/sides + phase + offset[s]
            radius = t*irregular[s]*(1+.04*math.sin(7*a+1.8*x))
            px, py = x+rx*radius*math.cos(a), y+ry*radius*math.sin(a)
            z = relief(px,py) + height_bias + .002*(1-t)
            if r == rings:
                z = -.013 + .002*math.sin(a*7+x)
            verts.append((px,py,z))
            alpha.append(0.0 if r == rings else (0.58 if r == rings-1 else 1.0))
    faces = [(0,1+s,1+(s+1)%sides) for s in range(sides)]
    for r in range(rings-1):
        a,b=1+r*sides,1+(r+1)*sides
        for s in range(sides):
            n=(s+1)%sides
            faces.append((a+s,b+s,b+n,a+n))
    return part(name,verts,faces,MATS[slot],1.25 if slot=="soil" else 2.2,alpha)


# One irregular damp core and three smaller litter veils avoid a repeated
# rectangular carpet. Their edge vertices disappear into the existing terrain.
island("Buried_damp_soil",0,0,1.58,.58,"soil",.14)
for i,args in enumerate(((-.72,.16,.52,.32,.1),(.13,-.20,.66,.25,-.4),(.90,.12,.43,.30,.6))):
    island(f"Leaf_litter_veil_{i}",*args[:4],"litter",args[4],.0025)


def stone(i,x,y,rx,ry,rz):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(0,0,0))
    obj=bpy.context.object
    obj.name=f"Half_buried_stone_{i:02}"
    for old in tuple(obj.users_collection):
        old.objects.unlink(obj)
    editable.objects.link(obj)
    obj.data.materials.append(MATS["stone"])
    for v in obj.data.vertices:
        p=v.co
        n=1+.12*math.sin(3*p.x+5*p.y+i)+.07*math.cos(5*p.z+2*p.x+i)
        p.x=x+rx*p.x*n
        p.y=y+ry*p.y*n
        p.z=relief(x,y)+rz*(p.z+.17)*n-.008
    uv=obj.data.uv_layers.new(name="UVMap")
    for face in obj.data.polygons:
        face.use_smooth=True
        for index in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv=(p.x*5.4+.15,p.y*5.4+.41)


for i,(x,y,rx,ry,rz) in enumerate((
    (-1.17,.04,.065,.043,.036),(-.84,-.31,.085,.06,.038),
    (-.50,.34,.045,.036,.023),(-.14,-.38,.061,.044,.028),
    (.23,.34,.070,.050,.029),(.64,-.16,.094,.053,.039),
    (1.12,.20,.054,.052,.028),(1.25,-.17,.045,.035,.022))):
    stone(i,x,y,rx,ry,rz)


def root(i,points,width):
    verts=[]
    sides=6
    for j,(x,y) in enumerate(points):
        radius=width*(1-j/len(points)*.6)
        tangent=Vector((points[min(j+1,len(points)-1)][0]-points[max(j-1,0)][0],
                        points[min(j+1,len(points)-1)][1]-points[max(j-1,0)][1],0)).normalized()
        normal=Vector((-tangent.y,tangent.x,0))
        for k in range(sides):
            a=math.tau*k/sides
            verts.append((x+normal.x*radius*math.cos(a),
                          y+normal.y*radius*math.cos(a),
                          relief(x,y)+.001+radius*.65*math.sin(a)))
    faces=[]
    for j in range(len(points)-1):
        for k in range(sides):
            n=(k+1)%sides
            faces.append((j*sides+k,j*sides+n,(j+1)*sides+n,(j+1)*sides+k))
    part(f"Shallow_root_{i:02}",verts,faces,MATS["root"],4.7)


for i,points in enumerate((
    ((-.75,.13),(-.84,.21),(-1.03,.26),(-1.15,.29)),
    ((-.75,.13),(-.68,.25),(-.58,.31),(-.45,.32)),
    ((-.22,-.10),(-.34,-.21),(-.47,-.27),(-.57,-.37)),
    ((.23,.06),(.33,.17),(.50,.25),(.65,.29)),
    ((.88,-.08),(.99,-.19),(1.10,-.23),(1.22,-.24)),
)):
    root(i,points,.014 if i%2 else .019)


with bpy.data.libraries.load(str(FERN / FERN_RECORD["source_blend"]), link=False) as (source,dest):
    dest.objects=[f"SM_NyaagyuFern02_{letter.upper()}_{tier}"
                  for tier in ("HI","MAC_LOD1") for letter in "abcd"]
fern_sources={obj.name:obj for obj in dest.objects}
assert len(fern_sources)==8

placements = [
    ("B",(-.93,-.05),.18,.78),
    ("A",(-.54,.19),1.32,.77),
    ("C",(-.13,-.06),-.69,.79),
    ("D",(.27,.25),1.84,.96),
    ("B",(.72,-.05),2.19,.69),
    ("A",(1.12,.11),-.40,.82),
]


def make_fern(letter,tier,index,xy,angle,scale):
    source=fern_sources[f"SM_NyaagyuFern02_{letter}_{'HI' if tier=='hi' else 'MAC_LOD1'}"]
    obj=source.copy()
    obj.data=source.data.copy()
    editable.objects.link(obj)
    obj.name=f"Fern_{tier}_{index}_{letter}"
    obj.data.materials.clear()
    obj.data.materials.append(MATS["fern_hi" if tier=="hi" else "fern_mac"])
    obj.hide_render=False
    obj.location=(xy[0],xy[1],relief(*xy)-.004)
    obj.rotation_euler.z=angle
    obj.scale=(scale,scale,scale)
    return obj


high=[make_fern(letter,"hi",i,xy,angle,scale) for i,(letter,xy,angle,scale) in enumerate(placements)]
mac=[make_fern(letter,"mac",i,xy,angle,scale) for i,(letter,xy,angle,scale) in enumerate(placements)]
for obj in mac: obj.hide_render=True
ground=[obj for obj in editable.objects if obj.type=="MESH" and not obj.name.startswith("Fern_")]


def export(objects,tier):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.duplicate()
    copies=list(bpy.context.selected_objects)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.join()
    united=bpy.context.object
    united.name=f"{NAME}_{tier}"
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    path=OUT/(united.name+".fbx")
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={"MESH"},
                             apply_unit_scale=True,axis_forward="-Y",axis_up="Z",
                             bake_anim=False,add_leaf_bones=False,path_mode="STRIP",
                             mesh_smooth_type="FACE",use_tspace=True,embed_textures=False)
    tri=sum(len(poly.vertices)-2 for poly in united.data.polygons)
    bounds={"min":[round(min(v.co[i] for v in united.data.vertices),4) for i in range(3)],
            "max":[round(max(v.co[i] for v in united.data.vertices),4) for i in range(3)]}
    slots=[mat.name for mat in united.data.materials]
    assert bounds["min"][0] > -1.9 and bounds["max"][0] < 1.9
    assert bounds["min"][1] > -.9 and bounds["max"][1] < .9
    assert bounds["min"][2] >= -.02 and bounds["max"][2] < .55
    united.hide_render=True
    united.hide_set(True)
    return {"fbx":path.name,"sha256":sha(path),"triangles":tri,"bounds_m":bounds,
            "material_slots":slots,"nanite_candidate":tier=="HI"}


mesh_high=export(ground+high,"HI")
mesh_mac=export(ground+mac,"MAC_LOD1")
bpy.ops.object.select_all(action="DESELECT")

# A deliberately low view checks whether the fern/soil contacts read as
# grounded at player eye level, not only from an orthographic catalog angle.
bpy.ops.mesh.primitive_plane_add(size=2)
plane=bpy.context.object
plane.name="Review_only_existing_Estate_terrain"
for old in tuple(plane.users_collection): old.objects.unlink(plane)
studio.objects.link(plane)
plane.dimensions=(8,5,0)
plane.location.z=.005
plane.data.materials.append(ground_mat("Review_only_surrounding_soil","DampSilt",(.78,.77,.74)))
for loop in plane.data.uv_layers.active.data:
    loop.uv[0]*=3
    loop.uv[1]*=2

world=bpy.data.worlds.new("Cool_overcast_studio")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.25,.28,.32,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.52
for name,location,energy,size,color in (
    ("Cloud_key",(-2.2,-2.8,3.5),680,2.8,(1,.88,.76)),
    ("Sky_fill",(2.6,1.8,4),400,3.2,(.72,.82,1)),
):
    lamp=bpy.data.lights.new(name,"AREA")
    lamp.energy=energy
    lamp.shape="DISK"
    lamp.size=size
    lamp.color=color
    obj=bpy.data.objects.new(name,lamp)
    studio.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,0,.15))-obj.location).to_track_quat("-Z","Y").to_euler()
camera_data=bpy.data.cameras.new("EyeHeight_65mm_Review")
camera=bpy.data.objects.new("EyeHeight_65mm_Review",camera_data)
studio.objects.link(camera)
scene.camera=camera
camera.location=(-2.55,-1.35,1.56)
camera.rotation_euler=(Vector((0,0,.12))-camera.location).to_track_quat("-Z","Y").to_euler()
camera_data.type="PERSP"
camera_data.lens=43
scene.render.engine="CYCLES"
scene.cycles.samples=32
scene.render.resolution_x=1500
scene.render.resolution_y=850
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
preview=OUT/"Preview_FernGroundTransition_EyeHeight.png"
scene.render.filepath=str(preview)
bpy.ops.render.render(write_still=True)

for obj in high: obj.hide_render=True
for obj in mac: obj.hide_render=False
mac_preview=OUT/"Preview_FernGroundTransition_MacFallback.png"
scene.render.filepath=str(mac_preview)
bpy.ops.render.render(write_still=True)
for obj in high: obj.hide_render=False
for obj in mac: obj.hide_render=True

bpy.ops.file.pack_all()
blend=OUT/"Nyaagyu_FernGroundTransition.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
manifest={
    "schema_version":1,"name":NAME,
    "generator":"scripts/art/create_nyaagyu_fern_ground_transition.py",
    "generator_sha256":sha(ROOT/"scripts/art/create_nyaagyu_fern_ground_transition.py"),
    "source_blend":blend.name,"source_blend_sha256":sha(blend),
    "meshes":{"hi":mesh_high,"mac_lod1":mesh_mac},
    "previews":{"hi":{"file":preview.name,"sha256":sha(preview)},
                "mac_lod1":{"file":mac_preview.name,"sha256":sha(mac_preview)}},
    "placements_local_m":[{"variant":v,"xy":list(xy),"yaw_rad":angle,"scale":scale}
                          for v,xy,angle,scale in placements],
    "recommended_review_origin_cm":[-1950,335,0],
    "orientation":"Local X follows Estate road; +Y points into north shoulder; +Z up",
    "gameplay_collision":False,
    "nanite_windows":True,
    "mac_conventional_fallback":{"source_fbx":mesh_mac["fbx"],
                                 "render_config":"Config/Mac/MacEngine.ini"},
    "scan_dependencies":DEPENDENCIES,
    "ground_dressing_manifest_sha256":sha(ROOT/"Content/SourceArt/Environment/NyaagyuGroundDressing/manifest.json"),
    "fern_source_manifest_sha256":sha(FERN/"manifest.json"),
    "license":"Original geometry plus pinned Poly Haven CC0-1.0 Fern 02 and PBR surface scans; no paid assets",
    "limitations":"Source-art candidate until fixed-camera packaged A/B and release-engine QA; visual-only collision policy.",
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
print("NYAAGYU_FERN_GROUND_TRANSITION_CREATED",mesh_high["triangles"],mesh_mac["triangles"],mesh_high["bounds_m"])
