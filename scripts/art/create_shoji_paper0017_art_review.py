"""A/B the original Dojo's one shoji bay with TextureCan Paper 0017.

Source-only Blender study. The original paper and cedar lattice geometry is
appended from the Dojo .blend and duplicated without changing its mesh vertices.
Only the candidate paper UV and material differ. The fiber scale and
transmission are artistic assumptions, not measured or historically certified.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Environment/ShojiPaperArtReview"
TEX = OUT / "Textures"
DOJO = ROOT / "Content/SourceArt/Environment/NyaagyuDojo"
OUT.mkdir(parents=True, exist_ok=True)
BLEND = OUT / "Nyaagyu_ShojiPaper0017_OneBayArtReview.blend"
MANIFEST = OUT / "manifest.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


dojo_record = json.loads((DOJO / "manifest.json").read_text())
dojo_blend = DOJO / dojo_record["source_blend"]
assert sha(dojo_blend) == dojo_record["blend_sha256"]
source_maps = {
    "Color":"paper_0017_color_2k.jpg",
    "Height":"paper_0017_height_2k.png",
    "NormalDX":"paper_0017_normal_directx_2k.png",
    "Roughness":"paper_0017_roughness_2k.jpg",
}
assert all((TEX / filename).is_file() for filename in source_maps.values())
derived_translucency = "paper_0017_translucency_ART_ESTIMATE_2k.png"
assert (TEX / derived_translucency).is_file()
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0


def collection(name):
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


BASE = collection("ArtReview_OriginalDojoBay_Baseline")
CAND = collection("ArtReview_Paper0017_OneBay_Candidate")
STUDIO = collection("ArtReview_CamerasAndLights")
SCOPE = collection("ArtReview_NeutralStage")


def in_bay(name):
    return (name == "Shoji_Paper_0" or name == "Shoji_Pull_0" or
            name.startswith("Shoji_Jamb_0_") or
            name.startswith("Shoji_KumikoV_0_") or
            name.startswith("Shoji_KumikoH_0_"))


with bpy.data.libraries.load(str(dojo_blend),link=False) as (source,dest):
    dest.objects = [name for name in source.objects if in_bay(name)]
for obj in dest.objects:
    if obj is None or obj.type != "MESH":
        continue
    BASE.objects.link(obj)
assert len(BASE.objects) == 16, [obj.name for obj in BASE.objects]
source_names = sorted(obj.name for obj in BASE.objects)
source_geometry = {}
for obj in BASE.objects:
    source_geometry[obj.name] = {
        "vertices":len(obj.data.vertices),
        "polygons":len(obj.data.polygons),
        "world_bounds": [list(map(float,obj.matrix_world @ Vector(corner)))
                         for corner in obj.bound_box],
    }
    clone = obj.copy()
    if obj.name == "Shoji_Paper_0":
        clone.data = obj.data.copy()
    CAND.objects.link(clone)
    clone.name = "Candidate_" + obj.name


def image(path,noncolor):
    img = bpy.data.images.load(str(path),check_existing=True)
    img.colorspace_settings.name = "Non-Color" if noncolor else "sRGB"
    return img


def new_paper_material():
    mat = bpy.data.materials.new("M_ArtReview_Paper0017_FiberTranslucency")
    mat.use_nodes = True
    nodes,links = mat.node_tree.nodes,mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    surface = nodes.new("ShaderNodeBsdfPrincipled")
    surface.inputs["Metallic"].default_value = 0
    surface.inputs["Coat Weight"].default_value = 0
    translucent = nodes.new("ShaderNodeBsdfTranslucent")
    mix_shader = nodes.new("ShaderNodeMixShader")
    links.new(surface.outputs["BSDF"],mix_shader.inputs[1])
    links.new(translucent.outputs["BSDF"],mix_shader.inputs[2])
    links.new(mix_shader.outputs[0],out.inputs["Surface"])
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UV0"
    tex = {}
    for channel,filename in source_maps.items():
        node = nodes.new("ShaderNodeTexImage")
        node.name = "Paper0017_" + channel
        node.image = image(TEX / filename, channel != "Color")
        node.extension = "REPEAT"
        links.new(uv.outputs["UV"],node.inputs["Vector"])
        tex[channel] = node
    # Source Color is solid white. Tint is an explicit design choice, not a
    # scanned washi color measurement.
    warm = nodes.new("ShaderNodeMixRGB")
    warm.blend_type = "MULTIPLY"
    warm.inputs[0].default_value = 1
    warm.inputs[2].default_value = (.72,.67,.57,1)
    links.new(tex["Color"].outputs["Color"],warm.inputs[1])
    links.new(warm.outputs["Color"],surface.inputs["Base Color"])
    links.new(warm.outputs["Color"],translucent.inputs["Color"])
    # The source roughness is nearly constant 0.50. Dry paper is made matte
    # by a visible, editable scale/bias rather than hiding a fabricated map.
    rough = nodes.new("ShaderNodeMapRange")
    rough.inputs["From Min"].default_value = .45
    rough.inputs["From Max"].default_value = .55
    rough.inputs["To Min"].default_value = .80
    rough.inputs["To Max"].default_value = .91
    links.new(tex["Roughness"].outputs["Color"],rough.inputs["Value"])
    links.new(rough.outputs["Result"],surface.inputs["Roughness"])
    # DirectX green channel is flipped for Blender. The same original map is
    # suitable for a future Unreal review after independent importer checks.
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(tex["NormalDX"].outputs["Color"],split.inputs["Color"])
    flip = nodes.new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1
    links.new(split.outputs["Green"],flip.inputs[1])
    normal_rgb = nodes.new("ShaderNodeCombineColor")
    links.new(split.outputs["Red"],normal_rgb.inputs["Red"])
    links.new(flip.outputs[0],normal_rgb.inputs["Green"])
    links.new(split.outputs["Blue"],normal_rgb.inputs["Blue"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = .48
    links.new(normal_rgb.outputs["Color"],normal.inputs["Color"])
    links.new(normal.outputs["Normal"],surface.inputs["Normal"])
    # NO transmission/opacity was provided. The separately generated 2K art
    # estimate remaps source height as a review-only shader mixture.
    transmission = nodes.new("ShaderNodeTexImage")
    transmission.name = "ArtEstimate_Translucency"
    transmission.label = "Art estimate, NOT measured paper transmission"
    transmission.image = image(TEX / derived_translucency, True)
    transmission.extension = "REPEAT"
    links.new(uv.outputs["UV"],transmission.inputs["Vector"])
    links.new(transmission.outputs["Color"],mix_shader.inputs[0])
    return mat


paper = next(obj for obj in CAND.objects if obj.name == "Candidate_Shoji_Paper_0")
paper.data.materials.clear()
paper.data.materials.append(new_paper_material())
# The 2K procedural map has no real-world size metadata. A 0.64 m tile is an
# art-scale assumption; only candidate paper UVs change. All original lattice
# meshes (and the paper's vertices) stay byte-for-byte identical.
while paper.data.uv_layers:
    paper.data.uv_layers.remove(paper.data.uv_layers[0])
uv = paper.data.uv_layers.new(name="UV0")
for poly in paper.data.polygons:
    n = poly.normal
    for li in poly.loop_indices:
        vertex = paper.matrix_world @ paper.data.vertices[paper.data.loops[li].vertex_index].co
        if abs(n.y) > .5:
            coord = ((vertex.x+2.13)/.64,(vertex.z-.94)/.64)
        elif abs(n.x) > .5:
            coord = ((vertex.y+2.765)/.64,(vertex.z-.94)/.64)
        else:
            coord = ((vertex.x+2.13)/.64,(vertex.y+2.765)/.64)
        uv.data[li].uv = coord


def aim(obj,target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()


def camera(name,distance):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name,data)
    STUDIO.objects.link(obj)
    obj.location = (-2.13,-2.765-distance,2.08)
    aim(obj,(-2.13,-2.765,2.08))
    data.lens = 26
    return obj


cam1 = camera("Camera_1m_Frontage",1.0)
cam3 = camera("Camera_3m_Frontage",3.0)


def light(name,kind,position,target,power,size):
    data = bpy.data.lights.new(name,kind)
    obj = bpy.data.objects.new(name,data)
    STUDIO.objects.link(obj)
    obj.location = position
    aim(obj,target)
    data.energy = power
    if kind == "AREA":
        data.shape = "DISK"
        data.size = size
    else:
        data.angle = math.radians(size)
    return obj


sun = light("FrontDaylight_Sun","SUN",(-3.5,-6.0,5.0),
            (-2.13,-2.765,2.08),1.1,4)
back = light("InteriorBacklight_Area","AREA",(-2.13,-1.65,2.08),
             (-2.13,-2.765,2.08),0,1.55)
scene.world.color = (.085,.085,.085)
scene.render.engine = "CYCLES"
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.camera = cam3
BASE.hide_render = False
CAND.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))


def render(name, use_candidate, distance, lighting):
    BASE.hide_render = use_candidate
    CAND.hide_render = not use_candidate
    scene.camera = cam1 if distance == 1 else cam3
    sun.data.energy = 1.1 if lighting == "Sun" else .06
    back.data.energy = 0 if lighting == "Backlit" else 0
    if lighting == "Backlit":
        back.data.energy = 180
    path = OUT / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


renders = []
for light_mode in ("Sun","Backlit"):
    for metres in (1,3):
        for role,use_candidate in (("Baseline",False),("Candidate",True)):
            renders.append(render(f"Shoji_{metres}m_{light_mode}_{role}",
                                  use_candidate,metres,light_mode))

record = {
    "schema_version":1,
    "name":"Nyaagyu one-bay Shoji Paper0017 source ArtReview",
    "status":"source-only material study, no runtime/UE import",
    "generator":"scripts/art/create_shoji_paper0017_art_review.py",
    "source_dojo_blend":str(dojo_blend.relative_to(ROOT)),
    "source_dojo_blend_sha256":sha(dojo_blend),
    "source_archive_url":"https://www.texturecan.com/downloads/paper_0017/paper_0017_2k_tZ5978.zip",
    "source_archive_sha256":"7e2a6fa92d0deaf187e00446108aed57af36f89535727097470d39418dc65dc9",
    "source_page":"https://www.texturecan.com/details/281/",
    "license_page":"https://www.texturecan.com/terms/",
    "license":"TextureCan states CC0 1.0, commercial use and redistribution with projects allowed",
    "source_type":"Procedural paper-only PBR; not photographed or historically certified washi",
    "source_maps":{key:{"file":str((TEX/file).relative_to(OUT)),"sha256":sha(TEX/file)}
                   for key,file in source_maps.items()},
    "derived_translucency":{"file":str((TEX/derived_translucency).relative_to(OUT)),
                            "sha256":sha(TEX/derived_translucency),
                            "generator":"scripts/art/derive_shoji_paper0017_translucency.py",
                            "interpretation":"No publisher opacity/transmission map. Source height remapped to 0.22–0.52 2K translucent shader mix as explicit art estimate, not physical calibration."},
    "assumed_tile_size_m":.64,
    "bay_source_names":source_names,
    "bay_geometry":source_geometry,
    "source_blend":BLEND.name,
    "source_blend_sha256":sha(BLEND),
    "renders":{p.name:sha(p) for p in renders},
}
MANIFEST.write_text(json.dumps(record,indent=2)+"\n")
print("SHOJI_PAPER_ART_REVIEW_RENDERED",len(renders),len(source_names),flush=True)
