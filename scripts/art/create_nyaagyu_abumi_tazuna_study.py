"""Original, source-only Nyaakoto abumi and tazuna contact art study.

Run after create_nyaagyu_abumi_tazuna_textures.py:
  blender -b --factory-startup --python scripts/art/create_nyaagyu_abumi_tazuna_study.py

Coordinates match the current source horse: +X forward, +/-Y left/right,
+Z up, metres. This is an Edo-informed fictional game prop, not a replica.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Content/SourceArt/Horses/NyaagyuAbumiTazunaStudy"
BLEND = OUT / "Nyaagyu_AbumiTazuna_Study.blend"
FBX = OUT / "SM_Nyaagyu_AbumiTazuna_Study.fbx"
LOGO = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
TEX = json.loads((OUT / "textures_manifest.json").read_text())
assert hashlib.sha256(LOGO.read_bytes()).hexdigest() == json.loads(
    (LOGO.parent / "sora_logo_manifest.json").read_text())["source_sha256"]
for entries in TEX["sets"].values():
    for entry in entries:
        assert hashlib.sha256((OUT / entry["file"]).read_bytes()).hexdigest() == entry["sha256"]

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1
art = bpy.data.collections.new("Nyaagyu_AbumiTazuna_Editable")
scene.collection.children.link(art)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def material(name: str, texture_key: str):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex_nodes = {}
    for channel, suffix in (("color", "Albedo"), ("orm", "ORM"), ("normal", "NormalDX")):
        node = nodes.new("ShaderNodeTexImage")
        node.label = f"Original {texture_key} {suffix}"
        node.image = bpy.data.images.load(str(OUT / f"T_Nyaagyu_{texture_key}_{suffix}.png"))
        node.image.pack()
        if channel != "color":
            node.image.colorspace_settings.name = "Non-Color"
        tex_nodes[channel] = node
    links.new(tex_nodes["color"].outputs["Color"], bsdf.inputs["Base Color"])
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(tex_nodes["orm"].outputs["Color"], sep.inputs["Color"])
    links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.space = "TANGENT"
    links.new(tex_nodes["normal"].outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


BLACK = material("M_Abumi_BlackUrushi_2K", "black_urushi")
RED = material("M_Abumi_InnerRedUrushi_2K", "red_urushi")
IRON = material("M_Abumi_ForgedIron_2K", "forged_iron")
LEATHER = material("M_Tazuna_OiledLeather_2K", "oiled_leather")
SILK = material("M_Tazuna_BraidedSilk_2K", "braided_silk")


def move(obj, name: str, mat=None):
    obj.name = name
    for coll in tuple(obj.users_collection):
        coll.objects.unlink(obj)
    art.objects.link(obj)
    if mat is not None:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    obj["source_art"] = "Original Nyaagyu abumi/tazuna v1"
    return obj


def mesh(name: str, verts, faces, mats, material_ids=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    art.objects.link(obj)
    for mat in mats:
        data.materials.append(mat)
    if material_ids:
        for polygon, material_id in zip(data.polygons, material_ids):
            polygon.material_index = material_id
    for polygon in data.polygons:
        polygon.use_smooth = True
    obj["source_art"] = "Original Nyaagyu abumi/tazuna v1"
    return obj


def tube(name: str, points, radius: float, mat, res=3):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.bevel_depth = radius
    curve.bevel_resolution = res
    spline = curve.splines.new("POLY")
    spline.points.add(len(points)-1)
    for bp, point in zip(spline.points, points):
        bp.co = (*point, 1)
    obj = bpy.data.objects.new(name, curve)
    art.objects.link(obj)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    result = bpy.context.object
    result["source_art"] = "Original Nyaagyu abumi/tazuna v1"
    return result


def torus(name: str, position, major, minor, mat, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=48, minor_segments=12,
                                     location=position, rotation=rotation)
    return move(bpy.context.object, name, mat)


def sphere(name, position, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=position)
    obj = move(bpy.context.object, name, mat)
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def ribbon(name: str, points, width: float, thickness: float, mat):
    """Closed strap cross-section with a stable lateral axis along its path."""
    path = [Vector(p) for p in points]
    verts = []
    for i, point in enumerate(path):
        tangent = (path[min(i+1, len(path)-1)] - path[max(i-1, 0)]).normalized()
        across = tangent.cross(Vector((0, 0, 1)))
        if across.length < .01:
            across = tangent.cross(Vector((1, 0, 0)))
        across.normalize()
        normal = tangent.cross(across).normalized()
        for a,b in ((-1,-1),(1,-1),(1,1),(-1,1)):
            verts.append(tuple(point + across*a*width/2 + normal*b*thickness/2))
    faces = []
    for i in range(len(path)-1):
        for j in range(4):
            k=(j+1)%4
            faces.append((4*i+j,4*i+k,4*(i+1)+k,4*(i+1)+j))
    faces.extend([(3,2,1,0), tuple(4*(len(path)-1)+j for j in range(4))])
    obj=mesh(name,verts,faces,[mat])
    bevel=obj.modifiers.new("Soft hand-cut leather edges", "BEVEL")
    bevel.width=min(thickness*.38,.001)
    bevel.segments=2
    obj.modifiers.new("Weighted face normals", "WEIGHTED_NORMAL")
    return obj


def stirrup(side: int):
    """Broad boat-like abumi; heel opens toward -X, shell closes the toe."""
    y0=side*.432
    z0=.855
    # The first-party source geometry is close to Met 2016.205 dimensions,
    # rather than a traced/museum-certified replica: L .29 W .13 H .25 m.
    stations=[(-.150,.049,.025),(-.119,.057,.048),(-.085,.062,.092),
              (-.045,.065,.153),(0,.065,.207),(.042,.062,.245),
              (.083,.056,.220),(.116,.046,.160),(.140,.030,.094)]
    n=9
    verts=[]
    # Each longitudinal section is an inner U and an outer U. The subtle
    # floor camber avoids a visibly planar CG block while keeping useful tread.
    for x,width,height in stations:
        for outside in (False,True):
            w=width+(.004 if outside else 0)
            for j in range(n):
                t=-1+2*j/(n-1)
                y=y0+t*w
                floor=z0+.006*abs(t)**1.8+.006*((x+.08)/.22)**2
                # Side rises progressively; center remains the open footbed.
                rise=height*(abs(t)**5.7)
                zz=floor+rise-(.006 if outside else 0)
                verts.append((x,y,zz))
    faces=[];ids=[]
    for s in range(len(stations)-1):
        for surface in (0,1):
            for j in range(n-1):
                a=s*2*n+surface*n+j
                b=(s+1)*2*n+surface*n+j
                face=(a,b,b+1,a+1)
                if surface: face=tuple(reversed(face))
                faces.append(face)
                ids.append(1 if surface==0 and 1<=j<=n-3 else 0)
        # Seal outer rim and underside edges with the same black urushi.
        for j in (0,n-1):
            a=s*2*n+j;b=(s+1)*2*n+j
            faces.append((a,a+n,b+n,b));ids.append(0)
    # Close toe; heel remains open by deliberate construction.
    end=(len(stations)-1)*2*n
    for j in range(n-1):
        faces.append((end+j,end+j+1,end+n+j+1,end+n+j));ids.append(0)
    mesh(f"Abumi_{side}_forged_lacquer_bowl",verts,faces,[BLACK,RED],ids)
    # Toe dome rises from the front of the footbed to the pigeon-breast crest.
    dome=[]
    layers=9;cross=13
    for layer in range(layers):
        t=layer/(layers-1)
        x=.139-.090*t+.013*math.sin(math.pi*t)
        z=z0+.063+.186*t
        width=.037+.024*math.sin(math.pi*t)
        for j in range(cross):
            q=-1+2*j/(cross-1)
            dome.append((x-.010*(1-q*q),y0+q*width,z-.045*(abs(q)**2.2)*t))
    dome_faces=[(i*cross+j,(i+1)*cross+j,(i+1)*cross+j+1,i*cross+j+1)
                for i in range(layers-1) for j in range(cross-1)]
    mesh(f"Abumi_{side}_hato_mune_toe_dome",dome,dome_faces,[BLACK])
    # Thin exposed iron roll on both high lips, a load-bearing suspension eye,
    # and a restrained red lacquer interior distinguished from outer black.
    for edge in (-1,1):
        edge_points=[]
        for x,w,h in stations[:-1]:
            edge_points.append((x,y0+edge*(w+.002),z0+.006+h))
        tube(f"Abumi_{side}_rim_{edge}",edge_points,.0024,IRON)
    torus(f"Abumi_{side}_suspension_eye",(.034,y0,z0+.250),.021,.0038,
          IRON,(math.pi/2,0,0))
    # A leather load path passes through the eye and rises toward the kura.
    strap_points=[(.025,side*.430,1.126),(.020,side*.408,1.174),
                  (.009,side*.361,1.247),(-.025,side*.298,1.325),
                  (-.045,side*.262,1.354)]
    ribbon(f"Abumi_{side}_oiled_leather_suspension",strap_points,.024,.0032,LEATHER)
    # Folded return and a small iron adjuster make attachment legible.
    ribbon(f"Abumi_{side}_folded_return",
           [(.027,side*.432,1.147),(.015,side*.410,1.197),
            (.004,side*.387,1.231)],.023,.0028,LEATHER)
    torus(f"Abumi_{side}_strap_adjuster",(.006,side*.380,1.241),.013,.0025,
          IRON,(math.pi/2,0,0))
    for k in range(4):
        x=.013-k*.003
        z=1.206+k*.009
        tube(f"Abumi_{side}_hand_stitch_{k}",
             [(x,side*.396,z),(x-.003,side*.391,z+.002)],.00065,SILK,1)


for side in (-1,1):
    stirrup(side)


def rein(side: int):
    """Bit connection, supple leather route and braided rider-grip segment."""
    sy=side
    bit=Vector((1.104,sy*.154,1.328))
    torus(f"Kutsuwa_{side}_iron_bit_ring",bit,.022,.0033,IRON,(math.pi/2,0,0))
    # Pairing to a bit/bar is represented, but this isolated prop does not
    # assert a historically proven rein knot, bit type or hand grip.
    ribbon(f"Tazuna_{side}_folded_bit_tab",
           [(1.102,sy*.176,1.331),(1.079,sy*.191,1.313),
            (1.058,sy*.205,1.291),(1.018,sy*.223,1.271)],.014,.0025,LEATHER)
    sphere(f"Tazuna_{side}_tab_rivet",(1.065,sy*.203,1.292),
           (.004,.0015,.004),IRON)
    leather_points=[(1.018,sy*.223,1.271),(.954,sy*.247,1.220),
                    (.816,sy*.275,1.177),(.672,sy*.287,1.176),
                    (.537,sy*.263,1.212),(.453,sy*.239,1.246)]
    ribbon(f"Tazuna_{side}_supple_leather",leather_points,.014,.0027,LEATHER)
    # A separate fibre grip provides a recognizable contact zone for a
    # future Nyaakoto paw rig. Three physical helices survive silhouette.
    start=Vector((.453,sy*.239,1.246));finish=Vector((.182,sy*.125,1.352))
    direction=(finish-start).normalized()
    u=direction.cross(Vector((0,0,1))).normalized()
    v=direction.cross(u).normalized()
    tube(f"Tazuna_{side}_braid_core",[start,finish],.004,SILK,2)
    for strand in range(3):
        samples=[]
        for j in range(129):
            t=j/128
            theta=math.tau*(13*t+strand/3)
            p=start.lerp(finish,t)+.0034*(math.cos(theta)*u+math.sin(theta)*v)
            samples.append(tuple(p))
        tube(f"Tazuna_{side}_physical_silk_strand_{strand}",samples,.00165,SILK,2)
    for label,p in (("start",start),("hand",finish)):
        torus(f"Tazuna_{side}_{label}_iron_ferrule",p,.0062,.0014,IRON,
              (0,math.pi/2,0))
    # A small neutral-pose attachment marker lives in the source, not FBX.
    bpy.ops.object.empty_add(type="SPHERE", location=finish)
    empty=bpy.context.object
    empty.name=f"Rider_{'Left' if side<0 else 'Right'}_TazunaGrip_Anchor"
    empty.empty_display_size=.018


for side in (-1,1):
    rein(side)
tube("Kutsuwa_iron_mouth_bar",[(1.104,-.154,1.328),(1.104,.154,1.328)],.0045,IRON)


def add_exact_sora_mon(side: int):
    """Use exact first-party SVG paths as a fictional resistance insignia."""
    before=set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(LOGO))
    objects=[o for o in set(bpy.data.objects)-before if o.type=="CURVE"]
    assert len(objects)==2
    bpy.context.view_layer.update()
    bounds=[o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    cx=(min(p.x for p in bounds)+max(p.x for p in bounds))/2
    cy=(min(p.y for p in bounds)+max(p.y for p in bounds))/2
    scale=.048/max(max(p.x for p in bounds)-min(p.x for p in bounds),
                   max(p.y for p in bounds)-min(p.y for p in bounds))
    for index,obj in enumerate(objects):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.convert(target="MESH")
        obj=bpy.context.object
        matrix=obj.matrix_world.copy()
        for vert in obj.data.vertices:
            p=matrix @ vert.co
            vert.co=(.151,(side*.432)+(p.x-cx)*scale,
                     .966+(p.y-cy)*scale)
        obj.matrix_world.identity()
        move(obj,f"SORA_kamon_exact_svg_abumi_{side}_{index}",RED)
        obj["source_svg_sha256"]=sha(LOGO)
        solid=obj.modifiers.new("Low raised lacquer inlay", "SOLIDIFY")
        solid.thickness=.0007


for side in (-1,1):
    add_exact_sora_mon(side)


# Every export mesh receives UV0; original texture imagery is available as
# separate named maps, and the editable source retains packed images.
bpy.ops.object.select_all(action="DESELECT")
export_objects=[o for o in art.objects if o.type=="MESH"]
for obj in export_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active=export_objects[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(island_margin=.008)
bpy.ops.object.mode_set(mode="OBJECT")
assert all(o.data.uv_layers.active is not None for o in export_objects)

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
bpy.ops.object.select_all(action="DESELECT")
for obj in export_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active=export_objects[0]
bpy.ops.export_scene.fbx(filepath=str(FBX), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         bake_space_transform=False, axis_forward="-Y", axis_up="Z",
                         path_mode="RELATIVE", embed_textures=False,
                         add_leaf_bones=False)


def area(name, location, power, color, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    lamp=bpy.context.object
    lamp.name=name
    lamp.data.energy=power
    lamp.data.color=color
    lamp.data.shape="DISK"
    lamp.data.size=size
    lamp.rotation_euler=(Vector((0,-.26,1.04))-lamp.location).to_track_quat("-Z","Y").to_euler()


world=bpy.data.worlds.new("Neutral studio")
scene.world=world
world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.24,.28,.33,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.42
area("Broad softbox",(.5,-1.05,1.85),650,(1,.89,.73),.72)
area("Cold strip",(-.52,.35,1.8),420,(.65,.80,1),.45)
area("Front fill",(.92,.4,1.34),240,(1,.94,.86),.45)
scene.render.engine="CYCLES"
scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=1120
scene.render.resolution_y=920
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
scene.render.film_transparent=False


def render(name, position, target, focal):
    bpy.ops.object.camera_add(location=position)
    cam=bpy.context.object
    cam.name=f"Camera_{name}"
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO"
    cam.data.ortho_scale=focal
    scene.camera=cam
    scene.render.filepath=str(OUT / name)
    bpy.ops.render.render(write_still=True)
    return OUT/name


render_a=render("Nyaagyu_Abumi_CloseReview.png",(.44,-1.18,1.31),
                (.005,-.424,1.06),.54)
render_b=render("Nyaagyu_Tazuna_ContactReview.png",(.80,-.80,1.67),
                (.64,-.25,1.285),.88)

verts=sum(len(o.data.vertices) for o in export_objects)
tris=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in export_objects)
manifest={
    "schema_version":1,
    "generator":"scripts/art/create_nyaagyu_abumi_tazuna_study.py",
    "source_blend":BLEND.name,"source_blend_sha256":sha(BLEND),
    "fbx":FBX.name,"fbx_sha256":sha(FBX),
    "texture_manifest_sha256":sha(OUT/"textures_manifest.json"),
    "logo_svg_sha256":sha(LOGO),
    "render_files":[{"file":p.name,"sha256":sha(p)} for p in (render_a,render_b)],
    "editable_mesh_parts":len(export_objects),"vertices":verts,"triangles":tris,
    "nominal_stirrup_dimensions_m":{"length":.290,"width":.138,"height":.250},
    "horse_anchor_compatibility":{"Abumi_LeftFoot":[-.035,-.432,.867],
                                  "Abumi_RightFoot":[-.035,.432,.867],
                                  "Tazuna_LeftGrip":[.183,-.125,1.352],
                                  "Tazuna_RightGrip":[.183,.125,1.352]},
    "materials":list(TEX["sets"].keys()),
    "license":"Original project-owned geometry and procedural maps; exact user-supplied SORA SVG used as fictional mon. No museum image or third-party source mesh copied.",
    "qualification":"Source-only isolated study. Not measured photoreal material, rider/horse fit, historically authenticated construction, animated rig, UE import or performance-tested asset.",
}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps({"mesh_parts":len(export_objects),"vertices":verts,"triangles":tris,
                  "output":str(OUT)},indent=2))
