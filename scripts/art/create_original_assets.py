"""Create original cat/weapon source assets. Run with Blender 5.2+ in background.

No downloads, stock meshes, or purchased artwork. Outputs are editable source art;
Unreal import is a separate explicit editor operation. These are prototype meshes,
not a claim of finished photorealistic characters, grooming, or motion capture.
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[2] / "Content/SourceArt")
parser.add_argument("--render", action="store_true")
options = parser.parse_args(args)
OUT = options.output.resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]
SORA_SVG = ROOT / "Content/SourceArt/UI/sora_logo_NOtext2.svg"
SORA_SVG_SHA256 = "d66413a71b70e25dcb8b2f118dcfe846a6446ed1db3de53ce88fc70c16ac0910"
assert hashlib.sha256(SORA_SVG.read_bytes()).hexdigest() == SORA_SVG_SHA256
assert json.loads((SORA_SVG.parent / "sora_logo_manifest.json").read_text())["source_sha256"] == SORA_SVG_SHA256
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, metal=0.0, rough=.6, grain=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    if grain:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = grain
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .15
        bump.inputs["Distance"].default_value = .015
        mat.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


FUR = material("M_CatFur_Ginger", (.42, .19, .075), rough=.91, grain=115)
CREAM = material("M_CatFur_Cream", (.73, .64, .48), rough=.94, grain=125)
NAVY = material("M_Indigo_Haori", (.022, .075, .10), rough=.83, grain=180)
BURGUNDY = material("M_Alien_Mulberry", (.105, .019, .085), rough=.57, grain=100)
ALIEN = material("M_Alien_SlateFur", (.14, .20, .26), rough=.88, grain=115)
STEEL = material("M_ForgedSteel", (.32, .40, .45), metal=.85, rough=.24)
GOLD = material("M_AgedBrass", (.34, .20, .063), metal=.72, rough=.42)
WOOD = material("M_LacquerWood", (.047, .020, .012), rough=.42, grain=9)
BLACK = material("M_Cat_Obsidian", (.008, .012, .014), rough=.3)
EYE = material("M_Cat_Amber", (.95, .43, .035), rough=.15)
CYAN = material("M_CoilJade", (.018, .47, .43), metal=.35, rough=.22)
PINK = material("M_Ear_Inner", (.32, .105, .095), rough=.9)


def assign(obj, mat):
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def sphere(name, pos, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=pos)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return assign(obj, mat)


def box(name, pos, size, mat, bevel=.018):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    if bevel:
        mod = obj.modifiers.new("Crafted_edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def tube(name, a, b, radius, mat):
    a, b = Vector(a), Vector(b)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=radius, depth=direction.length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    return assign(obj, mat)


def ear(name, x, y, z, mat, height=.26):
    vertices = [(x-.07,y-.075,z),(x-.07,y+.075,z),(x+.035,y+.065,z),(x+.035,y-.065,z),(x-.018,y*1.10,z+height)]
    faces = [(0,1,2,3),(0,4,1),(1,4,2),(2,4,3),(3,4,0)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    return assign(obj,mat)


def cloth_loft(name, sections, mat, pleats=0):
    """Tailored ellipsoidal panels with real folded cross-sections."""
    vertices=[]; faces=[]; count=48
    for z,rx,ry in sections:
        for i in range(count):
            a=i*2*math.pi/count
            fold=1+pleats*math.cos(a*12)
            vertices.append((math.cos(a)*rx*fold,math.sin(a)*ry*fold,z))
    for ring in range(len(sections)-1):
        for i in range(count):
            j=(i+1)%count
            faces.append((ring*count+i,ring*count+j,(ring+1)*count+j,(ring+1)*count+i))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);return assign(obj,mat)


def fur_shell(name, center, radii, mat, density=1400, length=.012, seed=0):
    """Original short geometric guard-hair cards; no groom or stock texture."""
    rng=random.Random(seed);verts=[];faces=[]
    center=Vector(center);radii=Vector(radii)
    for i in range(density):
        z=rng.uniform(-1,1);phi=rng.uniform(0,math.tau);r=math.sqrt(max(0,1-z*z))
        n=Vector((r*math.cos(phi),r*math.sin(phi),z))
        # Keep the forward facial features unobscured.
        if n.x>.62 and abs(n.y)<.72: continue
        p=center+Vector((n.x*radii.x,n.y*radii.y,n.z*radii.z))
        tangent=n.cross(Vector((0,0,1)))
        if tangent.length<.01: tangent=Vector((0,1,0))
        tangent.normalize()
        width=rng.uniform(.0006,.0016)
        direction=(n*.4+Vector((-.22,0,-.45))).normalized()
        tip=p+direction*length*rng.uniform(.6,1.4)
        base=len(verts);verts.extend([p-tangent*width,p+tangent*width,tip+tangent*width*.12,tip-tangent*width*.12]);faces.append(tuple(range(base,base+4)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);return assign(obj,mat)


def lapel(name, a, b, width, mat):
    a,b=Vector(a),Vector(b);direction=(b-a).normalized();side=direction.cross(Vector((1,0,0))).normalized()*width/2
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([a-side,a+side,b+side,b-side],[],[(0,1,2,3)]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    assign(obj,mat)
    mod=obj.modifiers.new('Fabric_thickness','SOLIDIFY');mod.thickness=.006
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def sora_kamon(name, center, diameter, mat):
    """Place both unmodified paths of the user-supplied mark on a +X-facing plane."""
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(SORA_SVG))
    curves = [obj for obj in set(bpy.data.objects) - before if obj.type == "CURVE"]
    assert len(curves) == 2, [obj.name for obj in curves]
    corners = [obj.matrix_world @ Vector(corner) for obj in curves for corner in obj.bound_box]
    origin_y = (min(p.x for p in corners) + max(p.x for p in corners)) / 2
    origin_z = (min(p.y for p in corners) + max(p.y for p in corners)) / 2
    size = max(max(p.x for p in corners) - min(p.x for p in corners),
               max(p.y for p in corners) - min(p.y for p in corners))
    assert size > 0
    for index, obj in enumerate(curves):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target="MESH")
        obj = bpy.context.object
        for vert in obj.data.vertices:
            p = obj.matrix_world @ vert.co
            vert.co = (center[0], center[1] + (p.x - origin_y) * diameter / size,
                       center[2] + (p.y - origin_z) * diameter / size)
        obj.matrix_world.identity()
        obj.name = f"UserSupplied_SORAKamon_{name}_Path_{index}"
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        obj["source_svg_sha256"] = SORA_SVG_SHA256
        obj["kamon_placement"] = name
        obj["kamon_path_index"] = index


def export_joined(name, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    bpy.context.scene.cursor.location = (0,0,0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    bpy.ops.export_scene.fbx(filepath=str(OUT / (name+".fbx")),use_selection=True,object_types={"MESH"},
        apply_unit_scale=True,global_scale=1.0,axis_forward="-Y",axis_up="Z",add_leaf_bones=False,bake_anim=False)
    return obj


def cat(name, alien=False):
    start = set(bpy.data.objects)
    fur, cloth = (ALIEN,BURGUNDY) if alien else (FUR,NAVY)
    cloth_loft("Tailored_haori",[(.80,.16,.22),(.95,.20,.27),(1.14,.205,.29),(1.28,.16,.23),(1.34,.105,.14)],cloth,.025)
    cloth_loft("Pleated_hakama",[(.40,.22,.27),(.54,.21,.28),(.72,.18,.25),(.84,.17,.23)],cloth,.07)
    for sign in (-1,1):
        sphere("Thigh",(-.01,sign*.14,.51),(.115,.13,.24),cloth)
        sphere("Shin",(.00,sign*.15,.25),(.095,.10,.20),cloth)
        sphere("Tabi_paw",(.065,sign*.15,.065),(.16,.12,.065),CREAM)
        for i in range(3):
            sphere("Toe",(.195,sign*.15+(i-1)*.056,.065),(.047,.032,.04),fur)
        sleeve = sphere("Haori_sleeve",(.025,sign*.32,1.05),(.15,.16,.25),cloth)
        sleeve.rotation_euler[0] = sign*.25
        sphere("Wrist_paw",(.085,sign*.38,.81),(.093,.095,.13),fur)
        for row in range(5):
            box("Laced_lamellar",(.204,sign*.10,.94+row*.064),(.025,.19,.055),WOOD,.007)
            for col in range(3):
                sphere("Lacing",(.220,sign*(.04+col*.055),.952+row*.064),(.003,.008,.006),GOLD)
        fur_shell("Wrist_fur",(.085,sign*.38,.81),(.093,.095,.13),fur,300,.009,sign+3)
    sphere("Neck",(0,0,1.36),(.13,.15,.14),fur)
    sphere("Head",(.005,0,1.54),(.183,.202,.195),fur)
    fur_shell("Head_guard_hairs",(.005,0,1.54),(.184,.203,.196),fur,2400,.015,9 if alien else 7)
    for sign in (-1,1):
        ear("Outer_ear",-.005,sign*.139,1.666,fur,.235 if alien else .20)
        ear("Inner_ear",.024,sign*.139,1.68,PINK,.16 if alien else .14)
        sphere("Muzzle",(.172,sign*.046,1.474),(.063,.058,.043),CREAM)
        sphere("Eye_socket",(.151,sign*.096,1.592),(.029,.052,.039),BLACK)
        sphere("Iris",(.176,sign*.096,1.592),(.008,.038,.029),CYAN if alien else EYE)
        sphere("Pupil",(.183,sign*.096,1.592),(.003,.007,.026),BLACK)
        sphere("Eye_glint",(.187,sign*.086,1.606),(.003,.006,.007),CREAM)
        for j in range(6):
            y=sign*(.05+j*.018);z=1.611+math.sin(j/5*math.pi)*.016
            sphere("Orbital_lid",(.161,y,z),(.015,.017,.010),fur)
        for j in range(3):
            tube("Whisker",(.219,sign*.057,1.47+j*.009),(.18,sign*.31,1.47+(j-1)*.025),.0008,CREAM)
    sphere("Chin",(.172,0,1.438),(.047,.064,.029),CREAM)
    sphere("Nose",(.232,0,1.488),(.019,.024,.014),PINK)
    tube("Mouth",(.239,0,1.477),(.228,0,1.449),.0015,BLACK)
    for i in range(9):
        sphere("Tail",(-.15-i*.049,0,.69+i*.041),(.065,.065,.079),fur)
    box("Obi",(.02,0,.81),(.39,.53,.09),cloth,.012)
    box("Obi_knot",(-.24,0,.82),(.10,.19,.16),WOOD,.02)
    lapel("Layered_collar_a",(.185,-.16,1.32),(.235,.12,.94),.045,CREAM)
    lapel("Layered_collar_b",(.188,.16,1.32),(.230,-.08,1.04),.045,CREAM)
    if alien:
        for sign in (-1,1):
            box("Alien_collar",(.03,sign*.28,1.34),(.27,.075,.13),STEEL)
            sphere("Induction_node",(.19,sign*.28,1.34),(.033,.05,.05),CYAN)
        box("Ledger_device",(.24,0,1.04),(.07,.16,.21),STEEL)
        box("Ledger_screen",(.279,0,1.06),(.008,.12,.13),CYAN,.003)
    else:
        sphere("Topknot",(-.08,0,1.727),(.05,.06,.07),BLACK)
        box("Headband",(.095,0,1.71),(.024,.32,.036),NAVY,.006)
        sora_kamon("headband",(.111,0,1.71),.032,GOLD)
        # The larger chest placement remains legible beyond first-person range.
        sphere("SORA_Kamon_Backing",(.236,0,1.085),(.010,.051,.051),WOOD)
        sora_kamon("chest",(.249,0,1.085),.074,GOLD)
        tube("Scabbard",(-.09,-.33,.92),(-.49,-.32,.30),.028,WOOD)
    joined = export_joined(name,list(set(bpy.data.objects)-start))
    if not alien:
        joined["sora_kamon_svg_sha256"] = SORA_SVG_SHA256
        joined["sora_kamon_placements"] = "headband,chest"
    return joined


hero = cat("SM_NyaagyuSamurai")
hero.hide_set(True)
enemy = cat("SM_AlienBanker", True)
enemy.hide_set(True)

catalog_path = Path(__file__).resolve().parents[2] / "Content/Data/catalog.json"
catalog = json.loads(catalog_path.read_text())
for weapon in catalog["weapons"]:
    start = set(bpy.data.objects)
    special = weapon["special"]
    if weapon["kind"] == "melee":
        wid = weapon["id"]
        tube("Wrapped_grip",(-.25,0,0),(0,0,0),.028,WOOD)
        if wid in (0,4,10):
            length = {0:.78,4:.46,10:.25}[wid]
            box("Tsuba",(.015,0,0),(.028,.13,.15),GOLD,.006)
            blade = box("Polished_blade",(.05+length/2,0,0),(length,.018,.055),STEEL,.004)
            blade.rotation_euler[1] = -.03
        elif wid == 2:
            tube("Sickle_handle",(-.2,0,0),(.35,0,0),.028,WOOD)
            box("Sickle_blade",(.32,0,.12),(.045,.018,.26),STEEL,.004)
            for n in range(16):
                bpy.ops.mesh.primitive_torus_add(major_radius=.029,minor_radius=.006,major_segments=12,minor_segments=6,location=(-.27-n*.042,0,-.04-n*n*.001))
                ring=bpy.context.object; ring.name="Kusari_link"; ring.rotation_euler[0]=(n%2)*math.pi/2; assign(ring,STEEL)
            sphere("Chain_weight",(-.93,0,-.29),(.065,.065,.065),STEEL)
        elif wid == 6:
            tube("Kanabo_shaft",(-.2,0,0),(.68,0,0),.056,WOOD)
            tube("Kanabo_head",(.24,0,0),(.86,0,0),.095,STEEL)
            for n in range(6):
                for angle in range(4):
                    a=angle*math.pi/2
                    sphere("Iron_stud",(.29+n*.10,math.sin(a)*.09,math.cos(a)*.09),(.027,.035,.035),GOLD)
        elif wid == 8:
            tube("Hammer_handle",(-.2,0,0),(.54,0,0),.035,WOOD)
            box("Forge_hammer_head",(.55,0,0),(.15,.15,.34),STEEL,.018)
        elif wid == 12:
            tube("Naginata_staff",(-.50,0,0),(.95,0,0),.026,WOOD)
            box("Monofilament_blade",(1.12,0,.025),(.42,.014,.055),CYAN,.004)
            for n in range(3):
                tube("Blade_binding",(.82+n*.045,-.038,0),(.82+n*.045,.038,0),.015,GOLD)
        for n in range(7):
            tube("Grip_binding",(-.23+n*.035,-.025,0),(-.21+n*.035,.025,0),.0035,BLACK)
    else:
        box("Receiver",(.08,0,0),(.35,.085,.13),STEEL)
        box("Wooden_stock",(-.27,0,-.015),(.34,.067,.12),WOOD)
        tube("Barrel",(.23,0,.019),(.71,0,.019),.022 if weapon["kind"] != "explosive" else .05,STEEL)
        box("Grip",(-.04,0,-.105),(.08,.06,.16),WOOD)
        box("Magazine",(.16,0,-.105),(.09,.065,.18),STEEL)
        tube("Sight_front",(.58,0,.042),(.58,0,.092),.008,GOLD)
        for n in range(4):
            box("Coil",(.25+n*.06,0,.035),(.014,.083,.085),CYAN if special else GOLD,.004)
        if special:
            sphere("Inductor",(.06,0,.087),(.10,.042,.042),CYAN)
    obj = export_joined(f"SM_Weapon_{weapon['id']:02d}", list(set(bpy.data.objects)-start))
    obj.hide_set(True)

hero.hide_set(False)
enemy.hide_set(False)
hero.location=(0,-.6,0)
enemy.location=(0,.7,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "SoraArena_OriginalAssets.blend"))
previous_manifest = json.loads((OUT / "manifest.json").read_text()) if (OUT / "manifest.json").exists() else {}
manifest = {
    "provenance":"Original procedural meshes authored for SORA Arena; kamon uses the user-supplied SORA SVG. No purchased assets.",
    "units":"meters in Blender; FBX unit metadata converts to Unreal centimeters",
    "characters":["SM_NyaagyuSamurai","SM_AlienBanker"],
    "weapons":[f"SM_Weapon_{i:02d}" for i in range(18)],
    "sora_kamon_svg_sha256":SORA_SVG_SHA256,
    "sora_kamon_placements":["headband","chest"],
    "limitations":["Static prototype meshes, no production rig or groom", "Procedural Blender materials require Unreal material authoring", "No photorealism or performance qualification"]
}
# The rig and hero-katana generators own these addenda to the shared manifest.
for key in ("skeletal_characters", "walk_animations", "rig_status", "hero_katana"):
    if key in previous_manifest:
        manifest[key] = previous_manifest[key]
(OUT / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")

if options.render:
    for obj in bpy.data.objects:
        obj.hide_render = obj.hide_get()
    ground=material("M_PreviewFloor",(.032,.046,.050),rough=.72)
    box("Preview_floor",(0,0,-.055),(200,200,.1),ground)
    bpy.ops.object.camera_add(location=(3.6,-3.4,2.2))
    camera=bpy.context.object
    camera.rotation_euler=(Vector((0,0,1.0))-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.lens=48
    bpy.context.scene.camera=camera
    for name,loc,energy,size,col in [("Warm_key",(3,-4,5),1200,4,(1,.79,.56)),("Cool_rim",(-3,2,4),1500,3,(.2,.65,1)),("Soft_fill",(1,4,3),700,3,(.65,.82,1))]:
        bpy.ops.object.light_add(type="AREA",location=loc)
        lamp=bpy.context.object; lamp.name=name; lamp.data.energy=energy; lamp.data.shape="DISK"; lamp.data.size=size; lamp.data.color=col
        lamp.rotation_euler=(Vector((0,0,1))-lamp.location).to_track_quat("-Z","Y").to_euler()
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280; scene.render.resolution_y=900; scene.render.resolution_percentage=100
    scene.world.color=(.035,.035,.035)
    scene.render.filepath=str(OUT / "OriginalCats_Preview.png")
    bpy.ops.render.render(write_still=True)

print(f"SORA_ASSETS_COMPLETE {OUT}")
